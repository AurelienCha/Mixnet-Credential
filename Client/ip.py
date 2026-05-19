import secrets
from mclbn256 import Fr, G1

class IPv4(str):

    def __new__(cls, ip):
        if isinstance(ip, str):
            return super().__new__(cls, ip)

        elif isinstance(ip, G1):
            s = cls.decode(ip)
            return super().__new__(cls, s)

        raise TypeError("Expected str or G1")

    # 253 bits (not 256, because BN uses a prime of 254 bits)
    def encode(self): 
        a, b, c, d = map(int, self.split('.'))
        ip = (a << 24) | (b << 16) | (c << 8) | d
        return G1().mapfrom(Fr((ip << (221)) + secrets.randbits(221))) # padding: 221 = (256 - 3) - 32
 
    @staticmethod
    def decode(G): # IP-Point to IPv6
        n = int(G.tostr().split()[1].decode(), 16) >> 221 # unpadding
        return f"{(n>>24)&255}.{(n>>16)&255}.{(n>>8)&255}.{n&255}"