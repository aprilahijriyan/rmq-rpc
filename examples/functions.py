import asyncio


async def add(x: int, y: int):
    return x + y


async def json_add(x: int, y: int):
    return {"xy": await add(x, y)}


async def long_task(seconds: int):
    print(f"asleep for {seconds} seconds...")
    await asyncio.sleep(seconds)
