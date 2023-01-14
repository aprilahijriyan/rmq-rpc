import asyncio
import json
import logging
from functools import partial
from typing import Callable, Dict, List

from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustChannel,
    AbstractRobustExchange,
    ConsumerTag,
)

from .serializers import BaseSerializer

log = logging.getLogger(__name__)


class Server:
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
        args, kwargs = await self.parse_params(msg)
        result = await func(*args, **kwargs)
        message = None
        for serializer in self.serializers:
            if msg.content_type in serializer.content_type:
                message = await serializer.serialize(result)
                break

        if message is None:
            raise TypeError(
                f"Message from {func!r} are not supported. Serializer is not available for {msg.content_type!r}"
            )

        for msg_attr, msg_attr_value in msg.info().items():
            setattr(message, msg_attr, msg_attr_value)

        await self.exchange.publish(message, routing_key=msg.reply_to)
        log.info(f"Result have been forwarded to: {msg.reply_to!r}")

    async def parse_params(self, msg: AbstractIncomingMessage):
        params: dict = json.loads(msg.body)
        if not isinstance(params, dict):
            log.error(
                f"The function parameter should be of type dict, not {type(params)}."
            )
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
        log.debug("Cleaned!")
