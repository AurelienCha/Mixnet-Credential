from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from enum import StrEnum
from random import sample
import asyncio, json

from network import Network
from crypto import Crypto
from header import Header
from log import create_logger

################################################################
# To remove when adding metrics.py
from mclbn256 import Fr, G1, G2 
def decode_ip(point: G1) -> str: # IP-Point to IPv4
    """Decode an IP address embedded inside a G1 point."""

    value = int(point.tostr().split()[1].decode(), 16) >> 221

    return (
        f"{(value >> 24) & 255}."
        f"{(value >> 16) & 255}."
        f"{(value >> 8) & 255}."
        f"{value & 255}"
    )
################################################################


class Stage(StrEnum):
    SIGN_MIX = "SIGN-MIX"
    HEADER = "HEADER"


class Mixnode:
    def __init__(self, node_id: int, config: PublicConfig):
        # Other
        self.log = create_logger("MIX", node_id)
        self.mixnodes = None#, self.pk_to_ip, self.sign_pk_lookup = None, None, None

        # Network
        self.ip = f"127.0.10.{node_id}"
        self.network = Network(self.ip, self.handle_message, self.log)
        self.signature_queue: asyncio.Queue = asyncio.Queue() # TODO... instead of buffer

        # Crypto
        self.authority_pk = config.authority_pk
        self.generators = config.generators

        self.signed_generator_sum = sum(config.signed_generators, start=G1().clear()) # TODO instad of self.signed_generator_sum = sum([G1().fromstr(g.encode()) for g in signed_generators[1:]], start=G1().fromstr(signed_generators[0].encode()))

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
                        if "sign_PK" in node
                    }

                header: Header = message

                processed_header = header.process(
                    secret_key=self.secret_key,
                    authority_pk=self.authority_pk,
                    generators=self.generators,
                    signed_generator_sum=self.signed_generator_sum,
                    sign_pk_lookup=self.sign_pk_lookup,
                )

                next_ip = self.pk_to_ip.get(str(processed_header.next_hop))

                if next_ip is None:
                    next_ip = decode_ip(processed_header.next_hop)

                await self.send(next_ip, Stage.HEADER, processed_header) 
    

    async def sign_public_key(self, authorities: list[str], threshold: int) -> G1:
        for authority in sample(authorities, k=threshold):
            await self.send(authority, Stage.SIGN_MIX, self.public_key)

        points = [await self.signature_queue.get() for _ in range(threshold)]
        return Crypto.lagrange_interpolation(points)


# ============================================================
# CONFIG LOADER
# ============================================================

@dataclass
class PublicConfig:
    authority_pk: G2
    generators: list[G1]
    signed_generators: list[G1]
    authorities: list[str]
    threshold: int
    mixnodes: dict[str, Any]

def load_public_config() -> PublicConfig:
    with open("public.json", encoding="utf-8") as file:
        raw = json.load(file)

    return PublicConfig(
        authority_pk=G2().fromstr(raw["authority_PK"].encode()),
        generators=[G1().fromstr(value.encode()) for value in raw["generators"]],
        signed_generators=[G1().fromstr(value.encode()) for value in raw["signed_generators"]],
        authorities=raw["authorities"],
        threshold=raw["threshold"],
        mixnodes=raw["mixnodes"],
    )