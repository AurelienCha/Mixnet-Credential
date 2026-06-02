from __future__ import annotations
from enum import StrEnum
from random import sample
import asyncio

from log import timing
from network import Network
from crypto import Crypto
from header import Header
from ECC import *

from config import CREDENTIALS, GENERATORS, MIXNODES, PATH_LENGTH, THRESHOLD, AUTHORITIES, AUTHORITY_PK, SIGNED_GENERATORS


class Stage(StrEnum):
    SIGN_CLIENT = "SIGN-CLIENT"
    HEADER = "HEADER"


class Client:

    def __init__(self, node_id: int):
        self.network = Network(f"127.0.100.{node_id}", self.handle_message)

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

    @timing
    async def get_credential(self, destination: str) -> G1:  # TODO hide value with salt
        destination = encode_ip(destination)

        for authority in sample(AUTHORITIES, k=THRESHOLD):
            await self.send(authority, Stage.SIGN_CLIENT, destination)
        
        points = [await self.signature_queue.get() for _ in range(THRESHOLD)]
        return Crypto.lagrange_interpolation(points)

    # ========================================================
    # PATH SELECTION
    # ========================================================

    @timing
    def select_mixnodes(self):
        path = sample(list(MIXNODES.keys()), k=PATH_LENGTH)
        mixnodes = [MIXNODES[ip] for ip in path]
        public_keys = [node.public_key for node in mixnodes]
        signed_public_keys = [node.signed_public_key for node in mixnodes]
        return (path[0], public_keys, signed_public_keys)

    # ========================================================
    # SHARED SECRETS
    # ========================================================

    @timing
    def derive_shared_secrets(self, public_keys: list[G1]) -> list[Fr]:
        nonce = Fr().randomize()
        alpha = G1().base_point() * nonce

        shared_secrets = []
        for public_key in public_keys:
            s = (public_key * nonce) >> Fr()
            shared_secrets.append(s)
            nonce *= s

        return alpha, shared_secrets
    
    # ========================================================
    # CREDENTIAL UPDATE
    # ========================================================

    @timing
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
        first_hop, header = self.build_packet(destination_ip)
        await self.send(first_hop, Stage.HEADER, header)
    
    @timing 
    def encode_destination(self, ip: str) -> G1:  # TODO:  make a list of destination en their encoding
        return encode_ip(ip)

    @timing
    def build_packet(self, destination_ip: str) -> None:

        delta = self.encode_destination(destination_ip) 

        # Path
        (first_hop, public_keys, signed_public_keys) = self.select_mixnodes()

        # Shared secret
        alpha, shared_secrets = self.derive_shared_secrets(public_keys)

        # Credential
        credential = self.update_credential(self.credentials[destination_ip], shared_secrets, signed_public_keys) if CREDENTIALS else None

        header = Header.build(
            destination= delta,
            mixes=public_keys,
            shared_secrets=shared_secrets,
            alpha=alpha,
            credential=credential,
        )

        return (first_hop, header)