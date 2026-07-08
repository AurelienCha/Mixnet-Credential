from common.ECC import *


################################
## ECC Lagrange Interpolation ##
################################

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

###########################
## POLYNOMIAL EVALUATION ##
###########################

class Polynomial:
    def __init__(self, coeffs):
        self.coeffs = coeffs  # [a0, a1, ...]

    def __call__(self, x):
        # Horner's method (fast polynomial evaluation)
        acc = self.coeffs[-1]
        for c in reversed(self.coeffs[:-1]):
            acc = acc * x + c
        return acc
