from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from random import sample
import asyncio

from log import create_logger
from network import Network
from crypto import Crypto
from header import Header

################################################################
# To remove when adding metrics.py 
from mclbn256 import Fr, G1, G2
from hashlib import sha256
def from_G1(self, other=None):
    return Fr(int(sha256(self.serialize()).hexdigest(), 16) >> 3)
G1.__rshift__ = from_G1
def from_G2(self, other=None):
    return Fr(int(sha256(self.serialize()).hexdigest(), 16) >> 3)
G2.__rshift__ = from_G2
def from_Fr(self, other):
    return other.mapfrom(self)
Fr.__rshift__ = from_Fr

# 253 bits (not 256, because BN uses a prime of 254 bits)
def encode_ip(ip: str) -> G1: 
    a, b, c, d = map(int, ip.split('.'))
    ip = (a << 24) | (b << 16) | (c << 8) | d
    return G1().mapfrom(Fr((ip << (221))))# + secrets.randbits(221))) # padding: 221 = (256 - 3) - 32 # TODO
#################################################################

class Stage(StrEnum):
    SIGN_CLIENT = "SIGN-CLIENT"
    HEADER = "HEADER"

class Client:

    def __init__(self, node_id: int, config: PublicConfig):
        self.log = create_logger("CLIENT", node_id)
        self.path_length = config.path_length

        self.network = Network(f"127.0.100.{node_id}", self.handle_message, self.log)

        self.mixnodes = config.mixnodes

        self.threshold = config.threshold
        self.authorities = config.authorities      
        self.authority_public_key = config.authority_pk

        self.generators = config.generators
        self.signed_generators = config.signed_generators

        self.signature_queue: asyncio.Queue = asyncio.Queue()
        self.credentials: dict[str, G1] = {}
    
    # ========================================================
    # NETWORK
    # ========================================================

    async def start(self) -> None:
        await self.network.start()

    async def send(self, ip: str, message_type: Stage, message) -> None:
        await self.network.send(ip, message_type, message)

    async def handle_message(self, ip: str, message_type: Stage, message) -> None:
        match message_type:
            case Stage.SIGN_CLIENT:
                await self.signature_queue.put((Fr(Crypto.hash(ip)), message))
            case Stage.HEADER:
                pass 
    

    # ========================================================
    # CREDENTIALS
    # ========================================================

    async def get_credential(self, destination: G1) -> G1:  # TODO hide value with salt
        self.log(comment="Requesting credential")

        for authority in sample(self.authorities, k=self.threshold):
            await self.send(authority, Stage.SIGN_CLIENT, destination)

        points = [await self.signature_queue.get() for _ in range(self.threshold)]
        credential = Crypto.lagrange_interpolation(points)
        
        self.log(comment="Credential completed")
        return credential

    # ========================================================
    # PATH SELECTION
    # ========================================================

    def select_mixnodes(self):
        path = sample(list(self.mixnodes.keys()), k=self.path_length)
        mixnodes = [self.mixnodes[ip] for ip in path]
        public_keys = [node.public_key for node in mixnodes]
        signed_public_keys = [node.signed_public_key for node in mixnodes]
        return (path[0], public_keys, signed_public_keys)

    # ========================================================
    # SHARED SECRETS
    # ========================================================

    def derive_shared_secrets(self, nonce: Fr, public_keys: list[G1]) -> list[Fr]:
        shared_secrets = []

        for public_key in public_keys:
            s = (public_key * nonce) >> Fr()
            shared_secrets.append(s)
            nonce *= s

        return shared_secrets
    
    # ========================================================
    # CREDENTIAL UPDATE
    # ========================================================

    def update_credential(self, credential: G1, shared_secrets: list[Fr], signed_public_keys: list[G1]) -> G1:
        return (
            credential
            + sum([signed_public_keys[i] for i in range(-1, -self.path_length, -1)], start=G1().clear())
            + sum([self.signed_generators[i] * sum(shared_secrets[:self.path_length-i], start=Fr(0)) for i in range(self.path_length)], start=G1().clear())
        )

    # ========================================================
    # SEND PACKET
    # ========================================================

    async def send_packet(self, destination_ip: str) -> None:
        # Path
        destination = encode_ip(destination_ip)
        (first_hop, public_keys, signed_public_keys) = self.select_mixnodes()

        # Shared secret
        nonce = Fr().randomize()
        shared_secrets = self.derive_shared_secrets(nonce, public_keys)
        alpha = G1().base_point() * nonce

        # Credential
        credential = self.credentials[destination_ip]
        updated_credential = self.update_credential(credential, shared_secrets, signed_public_keys)

        header = Header.build(
            destination=destination,
            mixes=public_keys,
            shared_secrets=shared_secrets,
            credential=updated_credential,
            alpha=alpha,
            generators=self.generators,
            PATH_SIZE=self.path_length
        )

        await self.send(first_hop, Stage.HEADER, header)