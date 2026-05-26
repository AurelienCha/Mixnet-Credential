from typing import Any

from header import Header
from ECC import *

# ============================================================
# SERIALIZER 
# ============================================================

SERIALIZERS = {
    Header: ("Header", lambda value: value.encode()),
    G1: ("G1", lambda value: value.serialize()),
    G2: ("G2", lambda value: value.serialize()),
    Fr: ("Fr", lambda value: value.serialize()),
    str: ("str", lambda value: value),
    int: ("int", lambda value: value),
}


DESERIALIZERS = {
    "Header": lambda value: Header.from_encoded(value),
    "G1": lambda value: G1().deserialize(value),
    "G2": lambda value: G2().deserialize(value),
    "Fr": lambda value: Fr().deserialize(value),
    "str": lambda value: value,
    "int": lambda value: int(value),
}

# ============================================================
# ENCODE / DECODE OBJECT
# ============================================================

def encode_object(obj: Any) -> tuple[str, Any]:
    if isinstance(obj, (list, tuple)):
        return (
            type(obj)(SERIALIZERS[type(item)][0] for item in obj),
            type(obj)(SERIALIZERS[type(item)][1](item) for item in obj)
        )

    object_type, encoder = SERIALIZERS[type(obj)]
    return (object_type, encoder(obj))

def decode_object(packet: tuple[str, Any]) -> Any:
    types, data = packet

    if isinstance(types, list):
        return [
            DESERIALIZERS[obj_type](value)
            for obj_type, value in zip(types, data)
        ]

    return DESERIALIZERS[types](data)

# ============================================================
# NETWORK ENCODE / DECODE
# ============================================================

def encode_message(message_type: str, message: Any) -> bytes:
    m = [message_type.value, *encode_object(message)]
    return str(m).encode()

def decode_message(data: bytes) -> tuple[str, Any]:
    message_type, *message = eval(data.decode())
    return (message_type, decode_object(message))

