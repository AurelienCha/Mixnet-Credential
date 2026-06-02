from typing import Any
from hashlib import sha256

from ECC import *

class Crypto:

    @staticmethod
    def lagrange_interpolation(points: list[tuple[Fr, G1]]) -> G1:
        result = points[0][1] * Fr(0)  # init to zero point

        for k, (xk, yk) in enumerate(points):
            numerator = Fr(1)
            denominator = Fr(1)

            for i, (xi, _) in enumerate(points):
                if i != k:
                    numerator *= -xi
                    denominator *= (xk - xi)

            result += yk * (numerator * ~denominator)

        return result


    @staticmethod
    def hash(values: Any) -> int | str:
        h = sha256()
        if not isinstance(values, (list, tuple)):
            values = [values]

        for v in values:
            h.update(str(v).encode())
            h.update(b"|")

        return int(h.hexdigest(), 16) >> 44
