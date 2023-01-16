import asyncio
import json
import logging
import pickle
from functools import partial
from typing import Callable, Dict, List

from aio_pika import Message
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustChannel,
    AbstractRobustExchange,
    ConsumerTag,
)

from .constant import CANCEL_QUEUE_NAME
from .serializers import BaseSerializer

log = logging.getLogger(__name__)


class Server:
    cancel_queue: AbstractQueue = None
    cancel_queue_consumer: ConsumerTag = None

    def __init__(
        self,
        channel: AbstractRobustChannel,
        exchange: AbstractRobustExchange,
        *,
        prefix: str = "",
    ) -> None:
        self.loop = asyncio.get_event_loop()
        self.channel = channel
        self.exchange = exchange
        self.prefix = prefix
        self.functions: Dict[str, Callable] = {}
        self.consumers: Dict[str, ConsumerTag] = {}
        self.queues: Dict[str, AbstractQueue] = {}
        self.serializers: List[BaseSerializer] = []
        self.tasks: Dict[str, asyncio.Task] = {}

    @classmethod
    async def create(
        cls, channel: AbstractRobustChannel, exchange: AbstractRobustExchange
    ):
        instance = cls(channel, exchange)
        instance.cancel_queue = await channel.declare_queue(
            CANCEL_QUEUE_NAME, durable=True
        )
        await instance.cancel_queue.bind(exchange)
        instance.cancel_queue_consumer = await instance.cancel_queue.consume(
            instance.task_cancel_handler, no_ack=True
        )
        return instance

    async def task_cancel_handler(self, msg: AbstractIncomingMessage):
        cid = msg.correlation_id
        if not cid:
            log.warn("Get messages without a correlation ID")
            return

        task = self.tasks.get(cid)
        if task:
            if task.done():
                log.warn(f"Unable to cancel task: {cid!r} (Task completed)")
            else:
                task.cancel()
                log.info(f"Canceling the task succeeded: {cid!r}")
        else:
            log.error(f"Unable to cancel task: {cid!r} (Task not found)")

    def _remove_task(self, cid: str, t: asyncio.Task):
        self.tasks.pop(cid, None)
        log.debug(f"Task removed: {cid!r}")

    def add_serializer(self, serializer: BaseSerializer):
        self.serializers.append(serializer)

    async def add_route(self, routing_key: str, func: Callable, **queue_kwargs):
        if routing_key in self.functions:
            raise RuntimeError(f"function already registered: {func}")

        if not asyncio.iscoroutinefunction(func):
            raise RuntimeError(f"function should be coroutine: {func}")

        queue_kwargs["auto_delete"] = True
        queue_name = self.prefix + routing_key
        queue = await self.channel.declare_queue(queue_name, **queue_kwargs)
        await queue.bind(self.exchange, routing_key)
        self.queues[routing_key] = queue
        self.functions[routing_key] = func
        self.consumers[routing_key] = await queue.consume(
            partial(self.on_message_received, routing_key), no_ack=True
        )
        log.info(f"Added: {routing_key!r}")

    async def on_message_received(self, routing_key: str, msg: AbstractIncomingMessage):
        func = self.functions.get(routing_key)
        if not func:
            log.warn(f"function for route {routing_key!r} not found")
            return

        if msg.reply_to is None:
            log.warn("Cannot find the reply-to attribute on the message.")
            return

        log.debug("Parse parameters...")
        func_params = await self.parse_params(msg)
        if not isinstance(func_params, tuple):
            return

        args, kwargs = func_params

        async def _func_executor():
            log.debug(f"Call function: {func.__name__!r}")
            success = False
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                log.exception(f"Error occurred when calling {func.__name__!r} function")
                result = e
            else:
                message_data = None
                try:
                    for serializer in self.serializers:
                        if msg.content_type in serializer.content_type:
                            message_data = await serializer.serialize(result)
                            break

                    if message_data is None:
                        raise TypeError(
                            f"Result from {func!r} are not supported. Serializer is not available for {msg.content_type!r}"
                        )

                    success = True
                    result = message_data
                except Exception as e:
                    result = e

            payload = pickle.dumps((success, result), protocol=pickle.HIGHEST_PROTOCOL)
            message = Message(payload)
            for msg_attr, msg_attr_value in msg.info().items():
                setattr(message, msg_attr, msg_attr_value)

            await self.exchange.publish(message, routing_key=msg.reply_to)
            log.info(f"Result have been forwarded to: {msg.reply_to!r}")

        task = asyncio.create_task(_func_executor())
        task.add_done_callback(partial(self._remove_task, msg.correlation_id))
        self.tasks[msg.correlation_id] = task

    async def parse_params(self, msg: AbstractIncomingMessage):
        try:
            params: dict = json.loads(msg.body)
            if not isinstance(params, dict):
                log.error(
                    f"The function parameter should be of type dict, not {type(params)}."
                )
                return
        except json.JSONDecodeError:
            log.exception(f"Unable to parse function parameters: {msg.body}")
            return

        args_param = params.get("args", [])
        kwds_param = params.get("kwargs", {})
        return args_param, kwds_param

    async def close(self):
        for routing_key, consumer_tag in self.consumers.items():
            queue = self.queues[routing_key]
            await queue.cancel(consumer_tag)
            await queue.delete(if_unused=False, if_empty=False)

        self.consumers.clear()
        self.queues.clear()
        if self.cancel_queue and self.cancel_queue_consumer:
            await self.cancel_queue.cancel(self.cancel_queue_consumer)
            await self.cancel_queue.delete(if_unused=False, if_empty=False)

        self.cancel_queue = None
        self.cancel_queue_consumer = None
        for task in self.tasks.values():
            if not task.done():
                task.cancel()

        self.tasks.clear()
        log.debug("Cleaned!")
