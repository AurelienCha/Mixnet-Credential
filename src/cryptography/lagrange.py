from cryptography.ecc import Fr, G1

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


