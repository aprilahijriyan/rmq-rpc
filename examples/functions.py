async def add(x: int, y: int):
    return x + y

async def json_add(x: int, y: int):
    return {"xy": await add(x, y)}
