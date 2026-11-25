#!/usr/bin/env python3
"""Generate input for circuit.circom (IPv4, 64 candidates, 253-bit nonce)."""
import argparse
import json
import secrets

P = 21888242871839275222246405745257275088548364400416034343698204186575808495617
A, D, NONRESIDUE = 168700, 168696, 5
NONCE_BITS = 253
CANDIDATES = 64

def sqrt_mod(n):
    """Tonelli-Shanks square root in F_P; return None for a nonsquare."""
    n %= P
    if n == 0:
        return 0
    if pow(n, (P - 1) // 2, P) != 1:
        return None
    q, s = P - 1, 0
    while q % 2 == 0:
        q //= 2
        s += 1
    z = 2
    while pow(z, (P - 1) // 2, P) != P - 1:
        z += 1
    m, c = s, pow(z, q, P)
    t, r = pow(n, q, P), pow(n, (q + 1) // 2, P)
    while t != 1:
        i, t2 = 0, t
        while t2 != 1:
            t2 = t2 * t2 % P
            i += 1
        b = pow(c, 1 << (m - i - 1), P)
        r = r * b % P
        t = t * b * b % P
        c = b * b % P
        m = i
    assert r*r % P == n
    return r

def add(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    t = x1*x2*y1*y2 % P
    dx, dy = (1 + D*t) % P, (1 - D*t) % P
    if dx == 0 or dy == 0:
        raise ValueError('Exceptional Edwards denominator')
    x3 = (x1*y2 + y1*x2) * pow(dx, -1, P) % P
    y3 = (y1*y2 - A*x1*x2) * pow(dy, -1, P) % P
    return x3, y3

def generate(ip, nonce):
    if not 0 <= ip < 2**32:
        raise ValueError('ip must be 32-bit unsigned integer')
    if ip in (1, 2, 3, 4, 5):
        raise ValueError('ip is blacklisted')
    if not 1 <= nonce < 2**NONCE_BITS:
        raise ValueError(f'nonce must satisfy 1 <= nonce < 2^{NONCE_BITS}')
    assert pow(NONRESIDUE, (P-1)//2, P) == P-1
    valids, roots, nonroots = [], [], []
    for i in range(CANDIDATES):
        x = ip * 2**221 + i
        assert x < P
        x2 = x*x % P
        den = (1-D*x2) % P
        if den == 0:
            raise ValueError(f'candidate {i} has zero denominator; circuit rejects it')
        rhs = (1-A*x2) * pow(den, -1, P) % P
        root = sqrt_mod(rhs)
        if root is not None:
            valids.append(1)
            roots.append(root)
            nonroots.append(0)
        else:
            nonroot = sqrt_mod(NONRESIDUE*rhs % P)
            assert nonroot is not None and rhs != 0
            valids.append(0)
            roots.append(0)
            nonroots.append(nonroot)
    selected = next((i for i,v in enumerate(valids) if v), None)
    if selected is None:
        raise ValueError('no valid candidate in first 64 attempts')
    roots[selected] = roots[selected] if roots[selected] % 2 == 0 else P-roots[selected]
    base = (ip*2**221+selected, roots[selected])
    assert (A*base[0]**2 + base[1]**2 - 1 - D*base[0]**2*base[1]**2) % P == 0
    acc, power = (0, 1), base
    # All bits must match BlindWithNonce(253), not just nonce & 15.
    for bit in range(NONCE_BITS):
        summed = add(acc, power)
        if nonce & (1<<bit):
            acc = summed
        if bit < NONCE_BITS - 1:
            power = add(power, power)
    data = {'ip':str(ip),'nonce':str(nonce),
            'valid':list(map(str,valids)), 'root':list(map(str,roots)),
            'nonRoot':list(map(str,nonroots)),
            'blindedX':str(acc[0]),'blindedY':str(acc[1])}
    for i in range(CANDIDATES):
        x = ip*2**221+i
        rhs = (1-A*x*x)*pow((1-D*x*x)%P,-1,P)%P
        assert ((int(data['root'][i])**2-rhs)%P == 0 if valids[i] else (int(data['nonRoot'][i])**2-5*rhs)%P == 0)
    return data, selected

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip',type=str,default=6)
    parser.add_argument('--nonce',type=str,default=None,
                        help='1 <= nonce < 2^253; defaults to fresh OS randomness')
    parser.add_argument('--output',default='input.json')
    parser.add_argument('--quiet',action='store_true')
    args = parser.parse_args()
    nonce = args.nonce if args.nonce is not None else secrets.randbelow(2**NONCE_BITS-1)+1
    try:
        data, selected = generate(int(args.ip), int(nonce))
    except ValueError as exc:
        parser.error(str(exc))
    with open(args.output,'w') as f:
        json.dump(data,f,indent=2)
        f.write('\n')
    if not args.quiet:
        print('Generated',args.output,'first valid index:',selected)
