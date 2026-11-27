from __future__ import annotations
import argparse, asyncio, sys, hmac
from enum import StrEnum
from random import SystemRandom
from secrets import randbelow
sample = SystemRandom().sample
from hashlib import sha256
from itertools import accumulate
from operator import mul
from utils.logging import timing, create_logger, LOGGING
from protocol.header import Header
from protocol.network import Network
from cryptomath.lagrange import lagrange_interpolation
from cryptomath.ecc import Fr, G1, G2, hash_to_Fr, encode_ip
from cryptomath.babyjub import Babyjub_encode_ip

from config.config import CREDENTIALS, MIXNODES, PATH_LENGTH, BETA_SIZE, THRESHOLD, AUTHORITIES, AUTHORITY_PK, AUTHORITY_PK_G1

class Stage(StrEnum):
    SIGN_CLIENT = "SIGN-CLIENT" # TODO update
    HEADER = "HEADER"


class Client:

    def __init__(self, node_id: int):
        self.network = Network(f"127.0.100.{node_id}", self.handle_message)

        self.credentials: dict[str, G1] = {}
        self.signature_queue: asyncio.Queue = asyncio.Queue()
        self.received_packets = 0
        
    
    
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
                await self.signature_queue.put((hash_to_Fr(ip.encode()), message))
            case Stage.HEADER:
                self.received_packets += 1  

    # ========================================================
    # PATH SELECTION
    # ========================================================

    def select_mixnodes(self):
        # Mixnodes {G1(N): {"IP": str(ip), "PK": G1(PK)}}
        route = sample(list(MIXNODES.keys()), k=PATH_LENGTH) 
        route_ip = [MIXNODES[n].ip for n in route]
        route_PK = [MIXNODES[n].PK for n in route] 
        return route, route_ip, route_PK

    # ========================================================
    # SHARED SECRETS
    # ========================================================

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
    # CREDENTIALS
    # ========================================================

    # @timing
    async def generate_proof(self, destination: str, r: int):
        zk_blinded_point = Babyjub_encode_ip(destination) * r

        a, b, c, d = map(int, destination.split("."))
        ip = (a << 24) | (b << 16) | (c << 8) | d

        prefix = f"{zk_blinded_point.x}"
        
        process = await asyncio.create_subprocess_exec("bash", "./zk/generate_proof.sh", str(ip), str(r), prefix)
        await process.wait()     # Wait for termination

        return prefix

    @timing
    async def get_credential(self, destination: str) -> G1:
        # Same nonzero 253-bit range as your ZK circuit.
        r = randbelow(1 << 253)
        zk_file = await self.generate_proof(destination, r)

        salt = Fr(r)
        blinded_destination = encode_ip(destination) * salt  # Blind signature

        for authority in sample(AUTHORITIES, k=THRESHOLD):
            await self.send(authority, Stage.SIGN_CLIENT, [blinded_destination, zk_file]) # TRICK: Send the encoding in both curve # TODO find compatible curves
        
        points = [await self.signature_queue.get() for _ in range(THRESHOLD)]
        signed_blinded_Delta = lagrange_interpolation(points)
        return signed_blinded_Delta * ~salt  # Unblind signature

    # @timing
    # def link_credential(self, credential: G1, shared_secrets: list[Fr], route_ip: list[str]) -> G1:
    #     # Sign hops
    #     Hops = [AUTHORITY_PK_G1 * hash_to_Fr(ip.encode()) for ip in route_ip] + [credential] 

    #     # Link credential to path
    #     return sum([Hop * ~s_prod for (Hop, s_prod) in zip(Hops, accumulate(shared_secrets, mul, initial=Fr(1)))])

    # @timing
    def link_credential(self, credential: G1, shared_secrets: list[Fr], route_ip: list[str]) -> G1:
        if not route_ip or len(route_ip) != len(shared_secrets):
            raise ValueError("Route and shared-secret lengths must agree")

        # AUTHORITY_PK_G1 = [y] zeta_1; AUTHORITY_PK remains [y] zeta_2.
        sigma = G1().base_point() * Fr(0)
        inverse_prefix = Fr(1)  # w_i^{-1}, initially w_1^{-1} = 1.
        for ip, shared_secret in zip(route_ip, shared_secrets):
            if shared_secret == Fr(0):
                raise ValueError("Shared secrets must be nonzero")
            address_scalar = hash_to_Fr(ip.encode())
            sigma = sigma + AUTHORITY_PK_G1 * (address_scalar * inverse_prefix)
            inverse_prefix = inverse_prefix * ~shared_secret

        return sigma + credential * inverse_prefix 

    # ========================================================
    # SEND PACKET
    # ========================================================

    async def send_packet(self, destination_ip: str) -> None:
        first_hop, header = self.build_packet(destination_ip)
        await self.send(first_hop, Stage.HEADER, header)
    
    def encode_destination(self, ip: str) -> G1:  # TODO:  make a list of destination en their encoding
        return encode_ip(ip)

    @timing
    def build_packet(self, destination_ip: str) -> None:

        delta = self.encode_destination(destination_ip) 

        # Path
        route, route_ip, route_PK = self.select_mixnodes() # TODO get route (list of ip)

        # Shared secret
        alpha, shared_secrets = self.derive_shared_secrets(route_PK)

        # Credential
        if CREDENTIALS: # Credential = [y]*Delta
            credential = self.link_credential(self.credentials[destination_ip], shared_secrets, route_ip)
        else:
            credential = None

        # Compute Encryption Layer
        layer = self.compute_layers(delta, route, shared_secrets) 

        return (MIXNODES[layer[0]].ip, Header(next_hop=layer[0], alpha=alpha, beta=layer[2:], gamma=layer[1], credential=credential)) # NEXT_HOP = layer[0] # TODO continue refactor

    # ============================================================
    # LAYER COMPUTATION
    # ============================================================

    def compute_gamma(self, betas: list[G1], shared_secret: Fr) -> G1:
        concatenate_encoding = b"".join(beta.serialize() for beta in betas) 
        return G1().hash(hmac.new(shared_secret.serialize(), concatenate_encoding, sha256).digest())

    def preprocessing(self, shared_secrets: list[Fr], route: list[G1]): 
        filler_chunks = []
        for i in range(PATH_LENGTH-1):
            # append
            filler_chunks.append(G1().hash(shared_secrets[i]))
            filler_chunks.append(route[i])
            # encrypt
            filler_chunks = [chunk * shared_secrets[i] for chunk in filler_chunks] # * s_i^-1

        return filler_chunks
    

    def initial_layer(self, destination: G1, shared_secrets: list[Fr], route: list[G1]):
        filler_chunks = self.preprocessing(shared_secrets, route)

        beta = [destination * ~shared_secrets[-1]] + filler_chunks 
        gamma = self.compute_gamma(beta, shared_secrets[-1])
        N = route[-1]
        return [N, gamma, *beta]

    def add_layer(self, next_hop: G1, layer: list[G1], shared_secret: Fr):
        beta = [chunk * ~shared_secret for chunk in layer[:-2]] 
        gamma = self.compute_gamma(beta, shared_secret)
        N = next_hop
        return [N, gamma, *beta]

    def compute_layers(self, destination: G1, route: list[G1], shared_secrets: list[Fr]):

        layer = self.initial_layer(destination, shared_secrets, route)

        for i in reversed(range(PATH_LENGTH-1)): 
            layer = self.add_layer(route[i], layer, shared_secrets[i])

        return layer

# ============================================================
# MAIN
# ============================================================

async def main(node_id: int, nbr_packets: int) -> None:

    create_logger("CLIENT", node_id)
    client = Client(node_id=node_id)

    # == START Network ==
    await client.start()
    await asyncio.sleep(1)


    # == SIGN Credentials ==
    own_ip = client.network.ip
    if CREDENTIALS:
        client.credentials[own_ip] = (await client.get_credential(own_ip))

    # == SEND packet == 
    await asyncio.gather(*(
        client.send_packet(own_ip)
        for _ in range(nbr_packets)
    ))

    while client.received_packets < nbr_packets:
        await asyncio.sleep(0.1)

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True, help="Client identifier")
    parser.add_argument("-x", "--packets", type=int, required=False, help="Send x packets", default=10)
    arguments = parser.parse_args()

    asyncio.run(main(arguments.id, arguments.packets))
    # try:
    #     asyncio.run(main(arguments.id, arguments.packets))

    # except Exception as e:
    #     print(f"ERROR: {type(e).__name__}: {e}")
    #     sys.exit(1)
