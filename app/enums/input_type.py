from enum import Enum


class InputType(str, Enum):
    IMAGE = "IMAGE"
    TEXT = "TEXT"
    VOICE = "VOICE"