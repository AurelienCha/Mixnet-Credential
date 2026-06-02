from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from hashlib import sha256
import hmac

from ECC import *
from log import timing
from config import GENERATORS, AUTHORITY_PK, PATH_LENGTH

class ProtocolError(Exception):
    """Base protocol exception."""


class IntegrityError(ProtocolError):
    """Raised when packet integrity verification fails."""


class CredentialError(ProtocolError):
    """Raised when credential verification fails."""

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
    # PROCESSING
    # ========================================================

    @timing
    def process_header(self, secret_key: Fr, signed_generator_sum: G1 | None, sign_pk_lookup: dict[str, G1] | None, pk_to_ip: dict[str, str]| None) -> tuple[str, Header]:
        if self.credential:
            self.verify_credential()

        shared_secret = self.compute_shared_secret(secret_key)

        self.verify_integrity(shared_secret)
        self.decrypt_beta(shared_secret)
        self.update_alpha(shared_secret)

        if self.credential:
            self.update_credential(shared_secret, signed_generator_sum, sign_pk_lookup)

        return (self.get_next_hop(pk_to_ip), self)

    @timing
    def verify_credential(self) -> None:
        x_value = sum(self.beta[::2])

        if (x_value @ AUTHORITY_PK) != (self.credential @ G2().base_point()):
            raise CredentialError("Credential verification failed")

    @timing
    def compute_shared_secret(self, secret_key: Fr) -> Fr:
        return (self.alpha * secret_key) >> Fr()    
    
    @timing
    def verify_integrity(self, shared_secret: Fr) -> None:
        concatenate_encoding = b"".join(beta.serialize() for beta in self.beta) 
        expected_gamma = G1().hash(hmac.new(shared_secret.serialize(), concatenate_encoding, sha256).digest())

        if self.gamma != expected_gamma:
            raise IntegrityError("Header integrity verification failed")

    @timing
    def decrypt_beta(self, shared_secret: Fr) -> None:
        header = [*self.beta, G1().clear(), G1().clear()]

        for index, value in enumerate(header):
            header[index] = value - GENERATORS[index] * shared_secret

        self.next_hop, self.gamma, *self.beta = header

    @timing
    def update_alpha(self, shared_secret: Fr) -> None:
        self.alpha *= shared_secret

    @timing
    def update_credential(self, shared_secret: Fr, signed_generator_sum: G1, sign_pk_lookup: dict[str, G1]) -> None:
        sign_next_hop = sign_pk_lookup.get(str(self.next_hop), G1().randomize()) # If not found, means final destination just randomize credential
        self.credential -= (signed_generator_sum * shared_secret + sign_next_hop)

    @timing
    def get_next_hop(self, pk_to_ip: dict[str, str]) -> str:
        return pk_to_ip.get(str(self.next_hop), decode_ip(self.next_hop))