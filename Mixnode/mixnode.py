from __future__ import annotations
from typing import Any
from enum import StrEnum
from random import sample
import asyncio

from network import Network
from crypto import Crypto
from header import Header
from log import create_logger
from ECC import *

from config import GENERATORS, THRESHOLD, AUTHORITIES, AUTHORITY_PK, SIGNED_GENERATORS, load_public_config

class Stage(StrEnum):
    SIGN_MIX = "SIGN-MIX"
    HEADER = "HEADER"


class Mixnode:
    def __init__(self, node_id: int):
        # Other
        self.log = create_logger("MIX", node_id)
        self.mixnodes = None # self.pk_to_ip = None # self.sign_pk_lookup = None

        # Network
        self.ip = f"127.0.10.{node_id}"
        self.network = Network(self.ip, self.handle_message, self.log)
        self.signature_queue: asyncio.Queue = asyncio.Queue() # TODO... instead of buffer

        # Crypto
        self.signed_generator_sum = sum(SIGNED_GENERATORS, start=G1().clear()) # TODO instad of self.signed_generator_sum = sum([G1().fromstr(g.encode()) for g in signed_generators[1:]], start=G1().fromstr(signed_generators[0].encode()))

        self.secret_key = Fr().randomize()
        self.public_key = G1().base_point() * self.secret_key


    async def start(self) -> None:
        await self.network.start()


    async def send(
        self, ip: str, message_type: str, message: Any) -> None:
        await self.network.send(ip, message_type, message)


    async def handle_message(self, ip: str, message_type: str, message: Any) -> None:
        match message_type:
            case Stage.SIGN_MIX:
                await self.signature_queue.put((Fr(Crypto.hash(ip)), message))

            # case Stage.HEADER if isinstance(message, Header):
            #     header = message
            case Stage.HEADER:
                if not self.mixnodes:
                    self.mixnodes = load_public_config().mixnodes

                    self.pk_to_ip = {
                        node["PK"]: ip
                        for ip, node in self.mixnodes.items()
                    }

                    self.sign_pk_lookup = {
                        node["PK"]: G1().fromstr(node["sign_PK"].encode())
                        for node in self.mixnodes.values()
                    }

                header: Header = message

                processed_header = header.process(
                    secret_key=self.secret_key,
                    signed_generator_sum=self.signed_generator_sum,
                    sign_pk_lookup=self.sign_pk_lookup,
                )

                next_ip = self.pk_to_ip.get(str(processed_header.next_hop))

                if next_ip is None:
                    next_ip = decode_ip(processed_header.next_hop)

                await self.send(next_ip, Stage.HEADER, processed_header) 
    

    async def sign_public_key(self) -> G1:
        for authority in sample(AUTHORITIES, k=THRESHOLD):
            await self.send(authority, Stage.SIGN_MIX, self.public_key)

        points = [await self.signature_queue.get() for _ in range(THRESHOLD)]
        return Crypto.lagrange_interpolation(points)
