from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from ECC import *

class ProtocolError(Exception):
    """Base protocol exception."""


class IntegrityError(ProtocolError):
    """Raised when packet integrity verification fails."""


class CredentialError(ProtocolError):
    """Raised when credential verification fails."""


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

    def encode(self) -> list[Any]:
        return [self.alpha.serialize(), *[beta.serialize() for beta in self.beta], self.gamma.serialize(), self.credential.serialize()]


    # ========================================================
    # PROCESSING
    # ========================================================


    def process(self, secret_key: Fr, authority_pk: G2, generators: list[G1], signed_generator_sum: G1, sign_pk_lookup: dict[str, G1]) -> Header:
        self.verify_credential(authority_pk)

        shared_secret = self.compute_shared_secret(secret_key)

        self.verify_integrity(shared_secret)
        self.decrypt_beta(shared_secret, generators)
        self.update_alpha(shared_secret)

        self.update_credential(shared_secret, signed_generator_sum, sign_pk_lookup)

        return self


    def verify_credential(self, authority_pk: G2) -> None:
        x_value = sum(self.beta[::2], start=G1().clear())

        if (x_value @ authority_pk) != (self.credential @ G2().base_point()):
            raise CredentialError("Credential verification failed")


    def compute_shared_secret(self, secret_key: Fr) -> Fr:
        return (self.alpha * secret_key) >> Fr()    
    

    def verify_integrity(self, shared_secret: Fr) -> None: # TODO modify integrity
        expected_gamma = sum(self.beta, start=G1().base_point() * shared_secret)

        if self.gamma != expected_gamma:
            raise IntegrityError("Header integrity verification failed")


    def decrypt_beta(self, shared_secret: Fr, generators: list[G1]) -> None:
        header = [*self.beta, G1().clear(), G1().clear()]

        for index, value in enumerate(header):
            header[index] = value - generators[index] * shared_secret

        self.next_hop, self.gamma, *self.beta = header


    def update_alpha(self, shared_secret: Fr) -> None:
        self.alpha *= shared_secret


    def update_credential(self, shared_secret: Fr, signed_generator_sum: G1, sign_pk_lookup: dict[str, G1]) -> None:
        sign_next_hop = sign_pk_lookup.get(str(self.next_hop), G1().randomize()) # If not found, means final destination just randomize credential
        self.credential -= (signed_generator_sum * shared_secret + sign_next_hop)