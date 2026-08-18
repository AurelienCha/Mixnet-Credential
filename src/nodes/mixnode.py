from __future__ import annotations
import asyncio, argparse, sys, hmac
from typing import Any
from enum import StrEnum
from random import sample
from hashlib import sha256

from utils.logging import timing, create_logger
from protocol.header import Header
from protocol.network import Network
from cryptography.lagrange import lagrange_interpolation
from cryptography.ecc import Fr, G1, G2, hash_to_Fr, decode_ip

from config.config import load_config, publish_mixnode, CREDENTIALS, GENERATORS, THRESHOLD, AUTHORITIES, AUTHORITY_PK, SIGNED_GENERATOR_SUMS

class Stage(StrEnum):
    SIGN_MIX = "SIGN-MIX"
    HEADER = "HEADER"


class Mixnode:
    def __init__(self, node_id: int):
        # Other
        self.mixnodes = None

        # Network
        self.ip = f"127.0.10.{node_id}"
        self.network = Network(self.ip, self.handle_message)
        self.signature_queue: asyncio.Queue = asyncio.Queue() # TODO... instead of buffer

        # Crypto
        self.signed_generator_sum = SIGNED_GENERATOR_SUMS[-1] if CREDENTIALS else None

        self.secret_key = Fr().randomize()
        self.public_key = G1().base_point() * self.secret_key


    async def start(self) -> None:
        await self.network.start()

    async def send(self, ip: str, message_type: str, message: Any) -> None:
        await self.network.send(ip, message_type, message)

    async def handle_message(self, ip: str, message_type: str, message: Any) -> None:
        match message_type:
            case Stage.SIGN_MIX:
                await self.signature_queue.put((hash_to_Fr(ip.encode()), message))

            case Stage.HEADER:
                if not self.mixnodes:
                    self.mixnodes = load_config().mixnodes
                header: Header = message
                next_ip, processed_header = self.process(header)

                await self.send(next_ip, Stage.HEADER, processed_header) 

    # ========================================================
    # SETUP & PROCESS
    # ========================================================
    
    @timing
    async def sign_public_key(self) -> G1:
        for authority in sample(AUTHORITIES, k=THRESHOLD):
            await self.send(authority, Stage.SIGN_MIX, self.public_key)

        points = [await self.signature_queue.get() for _ in range(THRESHOLD)]
        return lagrange_interpolation(points)


    @timing
    def process(self, header: Header) -> tuple[str, Header]:
        if header.credential:
            self.verify_credential(header)

        shared_secret = self.compute_shared_secret(header.alpha)

        self.verify_integrity(header, shared_secret)
        self.decrypt_beta(header, shared_secret)
        self.update_alpha(header, shared_secret)

        if header.credential:
            self.update_credential(header, shared_secret)

        return (self.get_next_hop(header), header)
    
    # ========================================================
    # HEADER PROCESSING FUNCTIONS
    # ========================================================

    # @timing
    def verify_credential(self, header: Header) -> None:
        if (sum(header.beta[::2]) @ AUTHORITY_PK) != (header.credential @ G2().base_point()):
            raise Exception("Credential verification failed")

    # @timing
    def compute_shared_secret(self, alpha: G1) -> Fr:
        return (alpha * self.secret_key) >> Fr()    
    
    # @timing
    def verify_integrity(self, header: Header, shared_secret: Fr) -> None:
        concatenate_encoding = b"".join(beta.serialize() for beta in header.beta) 
        expected_gamma = G1().hash(hmac.new(shared_secret.serialize(), concatenate_encoding, sha256).digest())

        if header.gamma != expected_gamma:
            raise Exception("Header integrity verification failed")

    # @timing
    def decrypt_beta(self, header: Header, shared_secret: Fr) -> None:
        chunks = [*header.beta, G1().clear(), G1().clear()]

        for index, value in enumerate(chunks):
            chunks[index] = value - GENERATORS[index] * shared_secret

        header.next_hop, header.gamma, *header.beta = chunks

    # @timing
    def update_alpha(self, header: Header, shared_secret: Fr) -> None:
        header.alpha *= shared_secret

    # @timing
    def update_credential(self, header: Header, shared_secret: Fr) -> None:
        next_hop = self.mixnodes.get(header.next_hop)
        next_hop_signed_PK = next_hop.signed_public_key if next_hop else G1().randomize() # If not found, means final destination just randomize credential
        header.credential -= (self.signed_generator_sum * shared_secret + next_hop_signed_PK)

    # @timing
    def get_next_hop(self, header: Header) -> str:
        next_hop = self.mixnodes.get(header.next_hop)
        return next_hop.ip if next_hop else decode_ip(header.next_hop)



# ============================================================
# MAIN
# ============================================================ 

async def main(node_id: int) -> None:

    create_logger("MIX", node_id)
    node = Mixnode(node_id=node_id)

    # == START ==
    await node.start()

    # == Publish Mixnode PK (and PK signed if CREDENTIALS) ==
    await publish_mixnode(node, await node.sign_public_key() if CREDENTIALS else None)
    
    # == WAIT TO PROCESS PACKET ==
    await asyncio.Event().wait()  # <- keeps alive

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True, help="Mixnode identifier")
    arguments = parser.parse_args()

    asyncio.run(main(arguments.id))
    # try:
    #     asyncio.run(main(arguments.id))

    # except Exception as e:
    #     print(f"ERROR: {type(e).__name__}: {e}")
    #     sys.exit(1)
   