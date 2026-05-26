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
    def hash(values: Any, short: bool = False) -> int | str:
        hasher = sha256()

        if not isinstance(values, (list, tuple)):
            values = [values]

        for value in values:
            hasher.update(str(value).encode())
            hasher.update(b"|")

        digest = hasher.hexdigest()

        if short:
            return digest[:8]

        return int(digest, 16) >> 44
