import json
import base64

from mclbn256 import G1, G2, Fr

# ============================================================
# SERIALIZER REGISTRY
# ============================================================

SERIALIZERS = {
    G1: {
        "type": "G1",
        "encode": lambda x: base64.b64encode(x.serialize()).decode(),
        "decode": lambda x: G1().deserialize(base64.b64decode(x))
    },

    G2: {
        "type": "G2",
        "encode": lambda x: base64.b64encode(x.serialize()).decode(),
        "decode": lambda x: G2().deserialize(base64.b64decode(x))
    },

    Fr: {
        "type": "Fr",
        "encode": lambda x: base64.b64encode(x.serialize()).decode(),
        "decode": lambda x: Fr().deserialize(base64.b64decode(x))
    },

    str: {
        "type": "str",
        "encode": lambda x: x,
        "decode": lambda x: x
    },

    int: {
        "type": "int",
        "encode": lambda x: x,
        "decode": lambda x: int(x)
    }
}

# reverse lookup
DESERIALIZERS = {
    v["type"]: v["decode"]
    for v in SERIALIZERS.values()
}

# ============================================================
# ENCODE OBJECT
# ============================================================

def encode_obj(obj):
    if isinstance(obj, list):
        s_list = [SERIALIZERS[type(o)] for o in obj]
        return {
            "__type__": [s["type"] for s in s_list],
            "data": [s["encode"](o) for (s, o) in zip(s_list, obj)]
        }

    s = SERIALIZERS[type(obj)]
    return {
        "__type__": s["type"],
        "data": s["encode"](obj)
    }

# ============================================================
# DECODE OBJECT
# ============================================================

def decode_obj(packet):
    types = packet["__type__"]

    if isinstance(types, list):
        return [DESERIALIZERS[t](data) for (t, data) in zip(types, packet["data"])]

    return DESERIALIZERS[types](packet["data"])

# ============================================================
# NETWORK ENCODE / DECODE
# ============================================================

def encode_msg(msg):
    return (json.dumps(encode_obj(msg)) + "\n").encode()

async def recv_msg(reader):
    data = await reader.readline()

    if not data:
        return None

    msg = decode_obj(json.loads(data.decode()))
    return msg