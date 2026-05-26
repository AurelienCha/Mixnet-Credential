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

if __name__ == '__main__':
    from enum import StrEnum
    class Stage(StrEnum):
        SIGN_MIX = "SIGN-MIX"
        HEADER = "HEADER"

    header = Header.from_encoded([b'\xb7\xf8\xb13\xdc\xbe\xc0\xefE\xfe:^_\xfd\x80G\x03\xf3\x88yI\x0f/a\xecb#\xb1B\x8b\r\x8d', b'\x10v\x92\x08\xfa\xb3z6\xea\x82\x14\xb0\xe8\xc0\xb3\x19\xf76\x8a\xcf4\x0c\tV\xdd\xc1y\xc9\x9cT\r\x9d', b'\x85\xf1N\x03\xca\x81\xbd:\xdc\xf3\xb4\xdc\xb4Dl\xdd\xe9U\xa7]\xdbWf\x9b\xb8L\xd7\xa9y\x84n\x90', b'A\x18\x83P\x1eB0p`\x7fj\xc5\x00\xa0\xb6\xee\x03\xe6\xbbs\xa8\x89\xb5J\x85\x92\xb72\x8c\x13E\x1e', b'8TwX\x16(\xeb\xe8\x17\xd9\x8c\x13\xe7-\xc7\x12*\xf8_cGi\xa5\x0c\xa7Z\xb5\x10\x94\xc7\xc9\x13', b'B\xa3|us>\x96\xbcd\xe1\x93Qx\x02\xf9K\x05\xbd\xff\x85T\xb7\xdb\xcc\x94\xd0E%\x1d\nO\x9c', b'\x97\x01\x80\xe5R\xbf\xd94\\F\xe3;\xbe\xe5\x13\x97\xd2\x0f\x1c\xb8\xdeg=\n\xae)\xf6a\xcb\t\x9c\x1c', b'\xf8N\xdd\x01\xcd\xa0\xbbR\xb5\xe6\x11\xd2\xdd\x7f\x0c\xcb\xd6\x8d\xa5a\xee\xe8ZY\xde\xe5U4\xf5\xda\x12\x19'])
    m = encode_message(Stage.HEADER, header)
    t, h = decode_message(m)
    print(h)
    print(header==h)
