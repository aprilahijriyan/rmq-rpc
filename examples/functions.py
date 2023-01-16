import asyncio


class Value:
    def __init__(self, value) -> None:
        self.value = value

    def __int__(self):
        return int(self.value)


async def add(x: int, y: int):
    return Value(x + y)


async def json_add(x: int, y: int):
    return {"xy": int(await add(x, y))}


async def long_task(seconds: int):
    print(f"asleep for {seconds} seconds...")
    await asyncio.sleep(seconds)


async def error_task():
    0 / 0
