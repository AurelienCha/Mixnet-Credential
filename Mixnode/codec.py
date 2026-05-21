import pickle

from mclbn256 import G1, G2, Fr
from header import Header

# ============================================================
# SERIALIZER REGISTRY
# ============================================================

SERIALIZERS = {
    Header: {
        "type": "Header",
        "encode": lambda x: x.encode(),
        "decode": lambda x: Header(x)
    },
    G1: {
        "type": "G1",
        "encode": lambda x: x.serialize(),
        "decode": lambda x: G1().deserialize(x)
    },

    G2: {
        "type": "G2",
        "encode": lambda x: x.serialize(),
        "decode": lambda x: G2().deserialize(x)
    },

    Fr: {
        "type": "Fr",
        "encode": lambda x: x.serialize(),
        "decode": lambda x: Fr().deserialize(x)
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
# ENCODE/DECODE OBJECT
# ============================================================

def encode_obj(obj):
    if isinstance(obj, (list, tuple)):
        s_list = type(obj)(SERIALIZERS[type(o)] for o in obj)
        return (type(obj)(s["type"] for s in s_list), type(obj)(s["encode"](o) for (s, o) in zip(s_list, obj)))

    s = SERIALIZERS[type(obj)]
    return (s["type"], s["encode"](obj))

def decode_obj(packet):
    types, data = packet

    if isinstance(types, (list, tuple)):
        return type(types)(DESERIALIZERS[t](d) for (t, d) in zip(types, data))

    return DESERIALIZERS[types](data)


# ============================================================
# NETWORK ENCODE / DECODE
# ============================================================

def encode_msg(msg_type, msg):
    packet = (msg_type, encode_obj(msg))
    return pickle.dumps(packet)

def decode_msg(data):
    msg_type, msg = pickle.loads(data)
    return (msg_type, decode_obj(msg))