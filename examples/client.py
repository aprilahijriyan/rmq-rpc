import asyncio
import logging
import os
import timeit

from aio_pika import connect_robust
from dotenv import load_dotenv
from functions import add, json_add, long_task

from rmq_rpc import Client
from rmq_rpc.client import log
from rmq_rpc.enums import ContentType
from rmq_rpc.serializers import JSONSerializer, RawSerializer

load_dotenv()

log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
log.addHandler(ch)


async def test_rpc_add():
    url = f"amqp://{os.getenv('RABBITMQ_DEFAULT_USER')}:{os.getenv('RABBITMQ_DEFAULT_PASS')}@localhost:5672/%2F"
    connection = await connect_robust(url)
    async with connection:
        try:
            channel = await connection.channel()
            exchange = await channel.declare_exchange("rmq_rpc", durable=True)
            client = await Client.create(channel, exchange)
            client.add_serializer(JSONSerializer())
            client.add_serializer(RawSerializer())
            start_time = timeit.default_timer()
            try:
                await client.call(long_task, args=(5,), timeout=3.0)
            except asyncio.TimeoutError:
                print("Successfully canceled long task (as expected!)")

            await asyncio.gather(
                *[client.call(add, args=(i, i + i)) for i in range(500)]
            )
            await asyncio.gather(
                *[
                    client.call(
                        json_add, args=(i, i + i), content_type=ContentType.JSON
                    )
                    for i in range(500)
                ]
            )

        finally:
            await client.close()
            end_time = timeit.default_timer()
            elapsed_time = end_time - start_time
            log.info("Elapsed time is %f seconds." % elapsed_time)


if __name__ == "__main__":
    asyncio.run(test_rpc_add())
