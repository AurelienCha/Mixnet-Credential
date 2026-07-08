from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from common.ECC import *
PATH_LENGTH=5 # TODO to put in common

@dataclass(slots=True)
class Header:
    alpha: G1
    beta: list[G1]
    gamma: G1
    credential: G1 | None
    next_hop: G1 | None = None

    def __init__(self, alpha: G1, beta: list[G1], gamma: G1, credential: G1 | None, next_hop: G1 | None = None):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.credential = credential
        self.next_hop = next_hop

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @classmethod
    def from_encoded(cls, message: list[Any]) -> "DefaultHeader":
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

