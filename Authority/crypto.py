import hashlib
from mclbn256 import G1, G2, Fr

class Crypto:
    def __init__(self, ip, threshold, generators):
        self.threshold = threshold
        self.generators = [G2().base_point()] + [G1().fromstr(g.encode()) for g in generators]

        self.x = Fr(Crypto.hash(ip))
        self.coefficients = [Fr().randomize() for _ in range(threshold)]
        self.secret_share = None

    def polynomial(self, x): # Horner polynomial evaluation -> efficient 
        x = Fr(Crypto.hash(x))

        result = Fr(0)
        for coef in reversed(self.coefficients):
            result = result * x + coef

        return result

    def aggregate_secret_key(self, y_shares):
        self.secret_share = sum(y_shares, Fr(0))

    def sign(self, P):
        return P * self.secret_share
    
    def sign_params(self):
        return [self.x, self.sign(self.generators[0])] + [self.sign(G) for G in self.generators[1::2]]
    
    @staticmethod
    def lagrange_interpolation(points):

        result = points[0][1] * Fr(0) # init to zero point

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
