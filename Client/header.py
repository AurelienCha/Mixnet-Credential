from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from hashlib import sha256
import hmac

from ECC import *
from log import timing
from config import GENERATORS, PATH_LENGTH, BETA_SIZE

@dataclass(slots=True)
class Header:
    alpha: G1
    beta: list[G1]
    gamma: G1
    credential: G1 | None
    next_hop: G1 | None = None

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @classmethod
    def from_encoded(cls, message: list[Any]) -> "Header":
        values = [G1().deserialize(value) for value in message]
        if len(values) == 2*PATH_LENGTH + 2:
            alpha, *beta, gamma, credential = values
        elif len(values) == 2*PATH_LENGTH + 1:
            alpha, *beta, gamma = values
            credential = None
        else:
            raise ValueError(f"Unexpected message length: {len(values)}")
        return cls(alpha=alpha, beta=beta, gamma=gamma, credential=credential)

    def encode(self) -> list[bytes]:
        if self.credential:
            return [self.alpha.serialize(), *(value.serialize() for value in self.beta), self.gamma.serialize(), self.credential.serialize()]
        return [self.alpha.serialize(), *(value.serialize() for value in self.beta), self.gamma.serialize()]

    # ========================================================
    # BUILD
    # ========================================================
    
    @classmethod
    def build(cls, destination: G1, mixes: list[G1], shared_secrets: list[Fr], alpha: G1, credential: G1 | None) -> "Header":
        beta, gamma = compute_layers(destination=destination, mixes=mixes, shared_secrets=shared_secrets)
        return cls(alpha=alpha, beta=beta, gamma=gamma, credential=credential)


# ============================================================
# LAYER COMPUTATION
# ============================================================

@timing
def compute_gamma(betas: list[G1], shared_secret: Fr) -> G1:
    concatenate_encoding = b"".join(beta.serialize() for beta in betas) 
    return G1().hash(hmac.new(shared_secret.serialize(), concatenate_encoding, sha256).digest())

@timing
def initial_layer(destination: G1, shared_secrets: list[Fr]):
    beta = [destination + GENERATORS[0] * shared_secrets[-1]] + [-sum([GENERATORS[BETA_SIZE + j - 2*i] * shared_secrets[i] for i in range(j//2, PATH_LENGTH-1)]) for j in range(BETA_SIZE-1)]
    gamma = compute_gamma(beta,  shared_secrets[-1])
    return beta, gamma

@timing
def add_layer(next_hop: G1, beta: list[G1], gamma: G1, shared_secret: Fr):

    next_beta = [next_hop, gamma, *beta[:BETA_SIZE]]
    next_beta = [next_beta[i] +  GENERATORS[i] * shared_secret for i in range(BETA_SIZE)]

    next_gamma = compute_gamma(next_beta, shared_secret)
    return next_beta, next_gamma

@timing
def compute_layers(destination: G1, mixes: list[G1], shared_secrets: list[Fr]):
    beta, gamma = initial_layer(destination, shared_secrets)

    for i in range(-2, -PATH_LENGTH-1, -1): # 1, 0
        beta, gamma = add_layer(mixes[i+1], beta, gamma, shared_secrets[i])

    return beta, gamma
