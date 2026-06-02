from __future__ import annotations
from typing import Any
from enum import StrEnum
from random import sample
import asyncio

from log import timing
from network import Network
from crypto import Crypto
from header import Header
from ECC import *

from config import CREDENTIALS, GENERATORS, THRESHOLD, AUTHORITIES, AUTHORITY_PK, SIGNED_GENERATORS

class Stage(StrEnum):
    SIGN_MIX = "SIGN-MIX"
    HEADER = "HEADER"


class Mixnode:
    def __init__(self, node_id: int):
        # Other
        self.mixnodes, self.pk_to_ip, self.sign_pk_lookup  = None, None, None

        # Network
        self.ip = f"127.0.10.{node_id}"
        self.network = Network(self.ip, self.handle_message)
        self.signature_queue: asyncio.Queue = asyncio.Queue() # TODO... instead of buffer

        # Crypto
        self.signed_generator_sum = sum(SIGNED_GENERATORS) if CREDENTIALS else None

        self.secret_key = Fr().randomize()
        self.public_key = G1().base_point() * self.secret_key


    async def start(self) -> None:
        await self.network.start()


    async def send(self, ip: str, message_type: str, message: Any) -> None:
        await self.network.send(ip, message_type, message)

    async def handle_message(self, ip: str, message_type: str, message: Any) -> None:
        match message_type:
            case Stage.SIGN_MIX:
                await self.signature_queue.put((Fr(Crypto.hash(ip)), message))

            case Stage.HEADER:
                header: Header = message
                next_ip, processed_header = header.process_header(
                    secret_key=self.secret_key,
                    signed_generator_sum=self.signed_generator_sum,
                    sign_pk_lookup=self.sign_pk_lookup,
                    pk_to_ip=self.pk_to_ip,
                )

                await self.send(next_ip, Stage.HEADER, processed_header) 

    @timing
    async def sign_public_key(self) -> G1:
        for authority in sample(AUTHORITIES, k=THRESHOLD):
            await self.send(authority, Stage.SIGN_MIX, self.public_key)

        points = [await self.signature_queue.get() for _ in range(THRESHOLD)]
        return Crypto.lagrange_interpolation(points)
