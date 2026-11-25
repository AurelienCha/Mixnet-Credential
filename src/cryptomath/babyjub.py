from dataclasses import dataclass
from ipaddress import IPv4Address

from zk.generate_json_input import P, A, D, add, sqrt_mod

IP_PADDING_BITS = 253 - 32
IP_COUNTER_LIMIT = 64


@dataclass(frozen=True)
class BabyPoint:
    x: int
    y: int

    def __mul__(self, scalar: int):
        if not isinstance(scalar, int):
            return NotImplemented
        if scalar < 0:
            raise ValueError("Scalar must be nonnegative")

        result, point = (0, 1), (self.x, self.y)
        while scalar:
            if scalar & 1:
                result = add(result, point)
            point = add(point, point)
            scalar >>= 1
        return BabyPoint(*result)

    __rmul__ = __mul__


def Babyjub_encode_ip(ip: str) -> BabyPoint:
    padded = int(IPv4Address(ip)) << IP_PADDING_BITS

    for counter in range(IP_COUNTER_LIMIT):
        x = padded + counter
        x2 = x * x % P
        rhs = (1 - A * x2) * pow((1 - D * x2) % P, -1, P) % P
        y = sqrt_mod(rhs)

        if y is not None:
            return BabyPoint(x, y if y % 2 == 0 else P - y)

    raise ValueError(f"No valid point within {IP_COUNTER_LIMIT} candidates")
