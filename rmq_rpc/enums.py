from enum import Enum


class ContentType(str, Enum):
    TEXT = "text/plain"
    JSON = "application/json"
