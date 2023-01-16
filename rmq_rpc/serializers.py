import json
from abc import ABC, abstractmethod
from typing import List, Union

from .enums import ContentType


class BaseSerializer(ABC):
    content_type: List[Union[ContentType, None]] = None

    @abstractmethod
    async def serialize(self, data: bytes):
        raise NotImplementedError

    @abstractmethod
    async def deserialize(self, data: bytes):
        raise NotImplementedError


class RawSerializer(BaseSerializer):
    content_type = [ContentType.TEXT, None]

    async def serialize(self, data: Union[str, bytes]):
        return data

    async def deserialize(self, data: bytes):
        return data


class JSONSerializer(BaseSerializer):
    content_type = [ContentType.JSON]

    async def serialize(self, data: Union[dict, list, int, float, str]) -> bytes:
        return json.dumps(data).encode()

    async def deserialize(self, data: bytes):
        return json.loads(data)
