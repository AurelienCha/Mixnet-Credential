from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from random import sample
import asyncio

from log import create_logger
from network import Network
from crypto import Crypto
from header import Header
from ECC import *

from config import  GENERATORS, MIXNODES, PATH_LENGTH, THRESHOLD, AUTHORITIES, AUTHORITY_PK, SIGNED_GENERATORS

class Stage(StrEnum):
    SIGN_CLIENT = "SIGN-CLIENT"
    HEADER = "HEADER"

class Client:

    def __init__(self, node_id: int):
        self.log = create_logger("CLIENT", node_id)

        self.network = Network(f"127.0.100.{node_id}", self.handle_message, self.log)

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
                print(OP_COUNT)
                pass 
    

    # ========================================================
    # CREDENTIALS
    # ========================================================

    async def get_credential(self, destination: str) -> G1:  # TODO hide value with salt
        destination = encode_ip(destination)
        self.log(comment="Requesting credential")

        for authority in sample(AUTHORITIES, k=THRESHOLD):
            await self.send(authority, Stage.SIGN_CLIENT, destination)

        points = [await self.signature_queue.get() for _ in range(THRESHOLD)]
        credential = Crypto.lagrange_interpolation(points)
        
        self.log(comment="Credential completed")
        return credential

    # ========================================================
    # PATH SELECTION
    # ========================================================

    def select_mixnodes(self):
        path = sample(list(MIXNODES.keys()), k=PATH_LENGTH)
        mixnodes = [MIXNODES[ip] for ip in path]
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
            + sum([signed_public_keys[i] for i in range(-1, -PATH_LENGTH, -1)])
            + sum([SIGNED_GENERATORS[i] * sum(shared_secrets[:PATH_LENGTH-i]) for i in range(PATH_LENGTH)])
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
        )

        await self.send(first_hop, Stage.HEADER, header)