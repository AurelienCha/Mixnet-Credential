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
# ENCODE/DECODE OBJECT
# ============================================================

def encode_obj(obj):
    if isinstance(obj, list):
        s_list = [SERIALIZERS[type(o)] for o in obj]
        return ([s["type"] for s in s_list], [s["encode"](o) for (s, o) in zip(s_list, obj)])

    s = SERIALIZERS[type(obj)]
    return (s["type"], s["encode"](obj))

def decode_obj(packet):
    types, data = packet

    if isinstance(types, list):
        return [DESERIALIZERS[t](d) for (t, d) in zip(types, data)]

    return DESERIALIZERS[types](data)

# ============================================================
# NETWORK ENCODE / DECODE
# ============================================================

def encode_msg(msg_type, msg):
    packet = (msg_type, encode_obj(msg))
    return (json.dumps(packet) + "\n").encode()

def decode_msg(data):
    msg_type, msg = json.loads(data.decode())
    return (msg_type, decode_obj(msg))