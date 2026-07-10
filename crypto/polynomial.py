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