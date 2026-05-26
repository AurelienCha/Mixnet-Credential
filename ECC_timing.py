from mclbn256 import G1, G2, GT, Fr
from hashlib import sha256

### Fr ###
def from_Fr(self, other):
    return other.mapfrom(self)
Fr.__rshift__ = from_Fr

### G1 ###
def from_G1(self, other=None):
    return Fr(int(sha256(self.serialize()).hexdigest(), 16) >> 3)
G1.__rshift__ = from_G1

### G2 ###
def from_G2(self, other=None):
    return Fr(int(sha256(self.serialize()).hexdigest(), 16) >> 3)
G2.__rshift__ = from_G2

def measure(it=100):
    OP_TIME = {
        "OBJ":{
            "Fr":0,
            "G1":0,
            "G2":0,
            "GT":0,
        },
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

    # OBJ
    print("Timing Object Instanciation...")
    OP_TIME["OBJ"]["Fr"] = f"{timeit('a = Fr()', setup='from mclbn256 import Fr;',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["OBJ"]["G1"] = f"{timeit('a = G1()', setup='from mclbn256 import G1;',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["OBJ"]["G2"] = f"{timeit('a = G2()', setup='from mclbn256 import G2;',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["OBJ"]["GT"] = f"{timeit('a = GT()', setup='from mclbn256 import GT;',number=it)/it * pow(10,6):.3f} ns"
    # RND
    print("Timing Object Ramdomization...")
    OP_TIME["RND"]["Fr"] = f"{timeit('a.randomize()', setup='from mclbn256 import Fr; a = Fr();',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["RND"]["G1"] = f"{timeit('a.randomize()', setup='from mclbn256 import G1; a = G1();',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["RND"]["G2"] = f"{timeit('a.randomize()', setup='from mclbn256 import G2; a = G2();',number=it)/it * pow(10,6):.3f} ns"
    # ADD
    print("Timing Object Addition...")
    OP_TIME["ADD"]["Fr"] = f"{timeit('a + b', setup='from mclbn256 import Fr;    a = Fr().randomize(); b = Fr().randomize()',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["ADD"]["G1"] = f"{timeit('a + b', setup='from mclbn256 import G1;    a = G1().randomize(); b = G1().randomize()',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["ADD"]["G2"] = f"{timeit('a + b', setup='from mclbn256 import G2;    a = G2().randomize(); b = G2().randomize()',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["ADD"]["GT"] = f"{timeit('a + b', setup='from mclbn256 import G1,G2; a = G1().randomize() @ G2().randomize(); b = G1().randomize() @ G2().randomize()',number=it)/it * pow(10,6):.3f} ns"
    # MUL
    print("Timing Object Multiplication...")
    OP_TIME["MUL"]["Fr"] = f"{timeit('a * b', setup='from mclbn256 import Fr;        a = Fr().randomize(); b = Fr().randomize()',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["MUL"]["G1"] = f"{timeit('a * b', setup='from mclbn256 import Fr,G1;     a = G1().randomize(); b = Fr().randomize()',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["MUL"]["G2"] = f"{timeit('a * b', setup='from mclbn256 import Fr,G2;     a = G2().randomize(); b = Fr().randomize()',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["MUL"]["GT"] = f"{timeit('a ** b', setup='from mclbn256 import Fr,G1,G2; a = G1().randomize() @ G2().randomize(); b = Fr().randomize()',number=it)/it * pow(10,6):.3f} ns"
    #  FROM
    print("Timing 'From' Conversion...")
    OP_TIME["FROM"]["G1"] = f"{timeit('a >> Fr()', setup='from mclbn256 import Fr,G1; a = G1().randomize();',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["FROM"]["G2"] = f"{timeit('a >> Fr()', setup='from mclbn256 import Fr,G2; a = G2().randomize();',number=it)/it * pow(10,6):.3f} ns"
    # TO
    print("Timing 'To' Conversion...")
    OP_TIME["TO"]["G1"] = f"{timeit('a >> G1()', setup='from mclbn256 import Fr,G1; a = Fr().randomize();',number=it)/it * pow(10,6):.3f} ns"
    OP_TIME["TO"]["G2"] = f"{timeit('a >> G2()', setup='from mclbn256 import Fr,G2; a = Fr().randomize();',number=it)/it * pow(10,6):.3f} ns"
    # PAIR
    print("Timing Object Pairing...")
    OP_TIME["PAIR"] = f"{timeit('a @ b', setup='from mclbn256 import G1,G2; a = G1().randomize(); b = G2().randomize();',number=it)/it * pow(10,6):.3f} ns"
    # MAP
    print("Timing Object Mapping...")
    stmt = """from random import randint; from mclbn256 import Fr,G1; ip = f'{randint(0,255)}.{randint(0,255)}.{randint(0,255)}.{randint(0,255)}';\ndef encode_ip(ip): a, b, c, d = map(int, ip.split('.')); ip = (a << 24) | (b << 16) | (c << 8) | d; return G1().mapfrom(Fr((ip << (221))))"""
    OP_TIME["MAP"] = f"{timeit('encode_ip(ip)', setup=stmt,number=it)/it * pow(10,6):.3f} ns"
    # UNMAP
    print("Timing Object Unmapping...")
    stmt = """import secrets; from mclbn256 import G1; point = G1().randomize()\ndef decode_ip(point): value = int(point.tostr().split()[1].decode(), 16) >> 221; return f'{(value >> 24) & 255}.{(value >> 16) & 255}.{(value >> 8) & 255}.{value & 255}'"""
    OP_TIME["UNMAP"] = f"{timeit('decode_ip(point)', setup=stmt,number=it)/it * pow(10,6):.3f} ns"

    
    with open(f"{dirname(__file__)}/timing average on {it:3_} iterations \n {time.asctime()}.json","w") as f:
        json.dump(OP_TIME,f)

if __name__ == '__main__':
    from timeit import timeit
    import json 
    from os.path import dirname
    import time

    measure(it=pow(10,4))
else:
    raise ImportError("SHOULD NOT BE IMPORTED")
