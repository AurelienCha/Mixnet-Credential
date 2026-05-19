import hashlib
from mclbn256 import G1, G2, Fr

class Crypto:

    @staticmethod
    def lagrange_interpolation(points):

        result = points[0][1] * Fr(0)  # init to zero point

        for k, (xk, yk) in enumerate(points):

            num = Fr(1)
            den = Fr(1)

            for i, (xi, _) in enumerate(points):

                if i != k:
                    num *= -xi
                    den *= (xk - xi)

            result += yk * (num * ~den)

        return result

    @staticmethod
    def hash(values):
        h = hashlib.sha256()
        if not isinstance(values, (list, tuple)):
            values = [values]

        for v in values:
            h.update(str(v).encode())
            h.update(b"|")

        return int(h.hexdigest(), 16) >> 44
