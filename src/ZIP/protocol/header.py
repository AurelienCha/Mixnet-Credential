from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from cryptomath.ecc import G1, G2
from config.config import PATH_LENGTH

@dataclass(slots=True)
class Header:
    next_hop: G1
    alpha: G1
    beta: list[G1]
    gamma: G1
    credential: G1 | None
    R2: G2 | None

    def __init__(self, next_hop: G1, alpha: G1, beta: list[G1], gamma: G1, credential: G1 | None, R2: G2 | None):
        self.next_hop = next_hop
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.credential = credential
        self.R2 = R2

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @classmethod
    def from_encoded(cls, message: list[Any]) -> "DefaultHeader":
        if len(message) == 2*PATH_LENGTH + 4:
            next_hop, alpha, *beta, gamma, credential = [G1().deserialize(value) for value in message[:-1]]
            R2 = G2().deserialize(message[-1])
        elif len(message) == 2*PATH_LENGTH + 2:
            next_hop, alpha, *beta, gamma = [G1().deserialize(value) for value in message]
            credential, R2 = None, None
        else:
            raise ValueError(f"Unexpected message length: {len(message)}")
        return cls(next_hop=next_hop, alpha=alpha, beta=beta, gamma=gamma, credential=credential, R2=R2)

    def encode(self) -> list[bytes]:
        if self.credential:
            return [self.next_hop.serialize(), self.alpha.serialize(), *(value.serialize() for value in self.beta), self.gamma.serialize(), self.credential.serialize(), self.R2.serialize()]
        return [self.next_hop.serialize(), self.alpha.serialize(), *(value.serialize() for value in self.beta), self.gamma.serialize()]

