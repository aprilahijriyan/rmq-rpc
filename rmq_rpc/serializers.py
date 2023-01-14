import json
from abc import ABC, abstractmethod
from typing import List, Union

from aio_pika import Message

from .enums import ContentType


class BaseSerializer(ABC):
    content_type: List[Union[ContentType, None]] = None

    @abstractmethod
    async def serialize(self, data: bytes) -> Message:
        raise NotImplementedError

    @abstractmethod
    async def deserialize(self, data: bytes):
        raise NotImplementedError


class RawSerializer(BaseSerializer):
    content_type = [ContentType.TEXT, None]

    async def serialize(self, data: Union[str, bytes]) -> Message:
        if isinstance(data, str):
            data = data.encode()
        return Message(data, content_type=self.content_type[0])

    async def deserialize(self, data: bytes):
        return data


class JSONSerializer(BaseSerializer):
    content_type = [ContentType.JSON]

    async def serialize(self, data: Union[dict, list]) -> Message:
        return Message(json.dumps(data).encode(), content_type=self.content_type[0])

    async def deserialize(self, data: bytes):
        return json.loads(data)
