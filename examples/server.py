import asyncio
import logging
import os

from aio_pika import connect_robust
from dotenv import load_dotenv
from functions import add, json_add

from rmq_rpc import Server
from rmq_rpc.serializers import JSONSerializer, RawSerializer
from rmq_rpc.server import log

load_dotenv()


log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
log.addHandler(ch)


async def main():
    url = f"amqp://{os.getenv('RABBITMQ_DEFAULT_USER')}:{os.getenv('RABBITMQ_DEFAULT_PASS')}@localhost:5672/%2F"
    connection = await connect_robust(url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("rmq_rpc", durable=True)
        server = Server(channel, exchange)
        server.add_serializer(JSONSerializer())
        server.add_serializer(RawSerializer())
        await server.add_route("add", add)
        await server.add_route("json_add", json_add)
        try:
            log.info("Start listening...")
            await asyncio.Future()
        finally:
            await server.close()


if __name__ == "__main__":
    asyncio.run(main())
