from mclbn256 import G1, G2, GT, Fr
from hashlib import sha256

def reset_OP_COUNT(): 
    global OP_COUNT;
    OP_COUNT = {
        "RND":{
            "Fr":0,
            "G1":0,
            "G2":0,
        },
        "ADD":{
            "Fr":0,
            "G1":0,
            "G2":0,
            "GT":0,
        },
        "MUL":{
            "Fr":0,
            "G1":0,
            "G2":0,
            "GT":0,
        },
        "FROM":{
            "G1":0,
            "G2":0,
        },
        "TO":{
            "G1":0,
            "G2":0,
        },
        "PAIR":0,
        "MAP":0,
        "UNMAP":0,
    }

reset_OP_COUNT()

#########
## RND ##
#########

### Fr ###
Fr_randomize = Fr.randomize
def Fr_randomize_hook(self):
    global OP_COUNT;
    OP_COUNT["RND"]["Fr"] += 1
    return Fr_randomize(self)
Fr.randomize = Fr_randomize_hook

### G1 ###
G1_randomize = G1.randomize
def G1_randomize_hook(self):
    global OP_COUNT; 
    OP_COUNT["RND"]["G1"] += 1
    return G1_randomize(self)
G1.randomize = G1_randomize_hook

### G2 ###
G2_randomize = G2.randomize
def G2_randomize_hook(self):
    global OP_COUNT; 
    OP_COUNT["RND"]["G2"] += 1
    return G2_randomize(self)
G2.randomize = G2_randomize_hook


##############
## ADDITION ##
##############

### Fr ###
Fr_add = Fr.__add__
def Fr_add_hook(self, other):
    global OP_COUNT;
    OP_COUNT["ADD"]["Fr"] += 1
    return Fr_add(self, other)
Fr.__add__ = Fr_add_hook

### G1 ###
G1_add = G1.__add__
def G1_add_hook(self, other):
    global OP_COUNT; 
    OP_COUNT["ADD"]["G1"] += 1
    return G1_add(self, other)
G1.__add__ = G1_add_hook

### G2 ###
G2_add = G2.__add__
def G2_add_hook(self, other):
    global OP_COUNT; 
    OP_COUNT["ADD"]["G2"] += 1
    return G2_add(self, other)
G2.__add__ = G2_add_hook

### GT ###
GT_add = GT.__add__
def GT_add_hook(self, other):
    global OP_COUNT; 
    OP_COUNT["ADD"]["GT"] += 1
    return GT_add(self, other)
GT.__add__ = GT_add_hook

###########
## SUM() ##
###########

### Fr ###
def Fr_radd(self, other):
    return self.__add__(other) if other else self
Fr.__radd__ = Fr_radd

### G1 ###
def G1_radd(self, other):
    return self.__add__(other) if other else self
G1.__radd__ = G1_radd

### G2 ###
def G2_radd(self, other):
    return self.__add__(other) if other else self
G2.__radd__ = G2_radd

### GT ###
def GT_radd(self, other):
    return self.__add__(other) if other else self
GT.__radd__ = GT_radd


####################
## MULTIPLICATION ##
####################

### Fr ###
Fr_mul = Fr.__mul__
def Fr_mul_hook(self, other):
    global OP_COUNT;
    OP_COUNT["MUL"]["Fr"] += 1
    return Fr_mul(self, other)
Fr.__mul__ = Fr_mul_hook

### G1 ###
G1_mul = G1.__mul__
def G1_mul_hook(self, other):
    global OP_COUNT; 
    OP_COUNT["MUL"]["G1"] += 1
    return G1_mul(self, other)
G1.__mul__ = G1_mul_hook

### G2 ###
G2_mul = G2.__mul__
def G2_mul_hook(self, other):
    global OP_COUNT; 
    OP_COUNT["MUL"]["G2"] += 1
    return G2_mul(self, other)
G2.__mul__ = G2_mul_hook

### GT ###
GT_mul = GT.__pow__
def GT_mul_hook(self, other):
    global OP_COUNT; 
    OP_COUNT["MUL"]["GT"] += 1
    return GT_mul(self, other)
GT.__pow__ = GT_mul_hook


#############
## PAIRING ##
#############

pairing = G1.__matmul__
def pairing_hook(self, other):
    global OP_COUNT; 
    OP_COUNT["PAIR"] += 1
    return pairing(self, other)
G1.__matmul__ = pairing_hook


###############
## TO / FROM ##
###############

### Fr ###
def from_Fr(self, other):
    global OP_COUNT; 
    if isinstance(other, G1):
        OP_COUNT["TO"]["G1"] += 1
    elif isinstance(other, G2):
        OP_COUNT["TO"]["G2"] += 1
    return other.mapfrom(self)
Fr.__rshift__ = from_Fr

### G1 ###
def from_G1(self, other=None):
    global OP_COUNT; 
    OP_COUNT["FROM"]["G1"] += 1
    return Fr(int(sha256(self.serialize()).hexdigest(), 16) >> 3)
G1.__rshift__ = from_G1

### G2 ###
def from_G2(self, other=None):
    global OP_COUNT; 
    OP_COUNT["FROM"]["G2"] += 1
    return Fr(int(sha256(self.serialize()).hexdigest(), 16) >> 3)
G2.__rshift__ = from_G2


#########
## MAP ##
#########

# 253 bits (not 256, because BN uses a prime of 254 bits)
def encode_ip(ip: str) -> G1: 
    global OP_COUNT; 
    OP_COUNT["MAP"] += 1
    a, b, c, d = map(int, ip.split('.'))
    ip = (a << 24) | (b << 16) | (c << 8) | d
    return G1().mapfrom(Fr((ip << (221))))# + secrets.randbits(221))) # padding: 221 = (256 - 3) - 32 # TODO -> Nop, not possible

def decode_ip(point: G1) -> str: # IP-Point to IPv4
    """Decode an IP address embedded inside a G1 point."""
    global OP_COUNT; 
    OP_COUNT["UNMAP"] += 1
    value = int(point.tostr().split()[1].decode(), 16) >> 221
    return f"{(value >> 24) & 255}.{(value >> 16) & 255}.{(value >> 8) & 255}.{value & 255}"

##########
## HASH ##
##########

# Curve order
R = int("0x2523648240000001BA344D8000000007FF9F800000000010A10000000000000D", 16)
def hash_to_Fr(msg: bytes):
    h = sha256(msg).digest()
    n = int.from_bytes(h, "big")
    n = n % R   # IMPORTANT: manual reduction
    x = Fr()
    x.setInt(n)
    return x

##############
## Hashable ## (for python dict)
##############
def hash_G1(self):
    return int(sha256(self.serialize()).hexdigest(), 16)
G1.__hash__ = hash_G1