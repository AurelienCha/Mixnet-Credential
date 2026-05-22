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
    def build(cls, destination: G1, mixes: list[G1], shared_secrets: list[Fr], credential: G1, alpha: G1, generators: list[G1]) -> "Header":
        beta, gamma = compute_layers(destination=destination, mixes=mixes, shared_secrets=shared_secrets, generators=generators)
        return cls(alpha=alpha, beta=beta, gamma=gamma, credential=credential)


# ============================================================
# LAYER COMPUTATION
# ============================================================

def compute_gamma(beta: list[G1], shared_secret: Fr) -> G1: # TODO modify integrity
    return sum(beta, start=G1().base_point() * shared_secret)


def initial_layer(destination: G1, shared_secrets: list[Fr], generators: list[G1]):

    beta = [
        destination + generators[0] * shared_secrets[2],
        -(generators[-4] * shared_secrets[1] + generators[-2] * shared_secrets[0]),
        -(generators[-3] * shared_secrets[1] + generators[-1] * shared_secrets[0]),
        -(generators[-2] * shared_secrets[1]),
        -(generators[-1] * shared_secrets[1]),
    ]

    gamma = compute_gamma(beta,  shared_secrets[2])
    return beta, gamma


def add_layer(next_hop: G1, beta: list[G1], gamma: G1, shared_secret: Fr, generators: list[G1]):

    next_beta = [
        next_hop + generators[0] * shared_secret,
        gamma + generators[1] * shared_secret,
        beta[0] + generators[2] * shared_secret,
        beta[1] + generators[3] * shared_secret,
        beta[2] + generators[4] * shared_secret,
    ]

    next_gamma = compute_gamma(next_beta, shared_secret)
    return next_beta, next_gamma


def compute_layers(destination: G1, mixes: list[G1], shared_secrets: list[Fr], generators: list[G1]):

    beta, gamma = initial_layer(destination, shared_secrets, generators)

    beta, gamma = add_layer(mixes[2], beta, gamma, shared_secrets[1], generators)
    beta, gamma = add_layer(mixes[1], beta, gamma, shared_secrets[0], generators)

    return beta, gamma
