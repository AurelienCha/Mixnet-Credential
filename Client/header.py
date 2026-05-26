from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from mclbn256 import Fr, G1

@dataclass
class Header:
    alpha: G1
    beta: list[G1]
    gamma: G1
    credential: G1
    next_hop: G1 | None = None

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @classmethod
    def from_encoded(cls, message: list[Any]) -> "Header":
        alpha, *beta, gamma, credential = [G1().deserialize(value) for value in message]
        return cls(alpha=alpha, beta=beta, gamma=gamma, credential=credential)

    def encode(self) -> list[bytes]:
        return [self.alpha.serialize(), *(value.serialize() for value in self.beta), self.gamma.serialize(), self.credential.serialize()]
        

    # ========================================================
    # BUILD
    # ========================================================

    @classmethod
    def build(cls, destination: G1, mixes: list[G1], shared_secrets: list[Fr], credential: G1, alpha: G1, generators: list[G1], PATH_SIZE) -> "Header":
        beta, gamma = compute_layers(destination=destination, mixes=mixes, shared_secrets=shared_secrets, generators=generators, PATH_SIZE=PATH_SIZE)
        return cls(alpha=alpha, beta=beta, gamma=gamma, credential=credential)


# ============================================================
# LAYER COMPUTATION
# ============================================================

def compute_gamma(beta: list[G1], shared_secret: Fr) -> G1: # TODO modify integrity
    return sum(beta, start=G1().base_point() * shared_secret)


def initial_layer(destination: G1, shared_secrets: list[Fr], generators: list[G1], PATH_SIZE, BETA_SIZE):
    beta = [destination + generators[0] * shared_secrets[-1]] + [-sum([generators[BETA_SIZE + j - 2*i] * shared_secrets[i] for i in range(j//2, PATH_SIZE-1)], start=G1().clear()) for j in range(BETA_SIZE-1)]
    gamma = compute_gamma(beta,  shared_secrets[-1])
    return beta, gamma


def add_layer(next_hop: G1, beta: list[G1], gamma: G1, shared_secret: Fr, generators: list[G1], BETA_SIZE):

    next_beta = [next_hop, gamma, *beta[:BETA_SIZE]]
    next_beta = [next_beta[i] +  generators[i] * shared_secret for i in range(BETA_SIZE)]

    next_gamma = compute_gamma(next_beta, shared_secret)
    return next_beta, next_gamma


def compute_layers(destination: G1, mixes: list[G1], shared_secrets: list[Fr], generators: list[G1], PATH_SIZE):

    BETA_SIZE = 2 * PATH_SIZE - 1
    beta, gamma = initial_layer(destination, shared_secrets, generators, PATH_SIZE, BETA_SIZE)

    for i in range(-2, -PATH_SIZE-1, -1): # 1, 0
        beta, gamma = add_layer(mixes[i+1], beta, gamma, shared_secrets[i], generators, BETA_SIZE)

    return beta, gamma
