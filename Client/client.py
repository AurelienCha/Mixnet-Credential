from __future__ import annotations
from enum import StrEnum
from random import sample
import asyncio
from hashlib import sha256
import hmac

from common.log import timing
from common.header import Header
from common.network import Network
from common.crypto import lagrange_interpolation
from common.ECC import *

from Client.config import CREDENTIALS, GENERATORS, MIXNODES, PATH_LENGTH, BETA_SIZE, THRESHOLD, AUTHORITIES, AUTHORITY_PK, SIGNED_GENERATOR_SUMS


class Stage(StrEnum):
    SIGN_CLIENT = "SIGN-CLIENT"
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
    # CREDENTIALS
    # ========================================================

    @timing
    async def get_credential(self, destination: str) -> G1:  # TODO hide value with salt
        destination = encode_ip(destination)

        for authority in sample(AUTHORITIES, k=THRESHOLD):
            await self.send(authority, Stage.SIGN_CLIENT, destination)
        
        points = [await self.signature_queue.get() for _ in range(THRESHOLD)]
        return lagrange_interpolation(points)

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
            + sum([SIGNED_GENERATOR_SUMS[i] * shared_secrets[-i-1] for i in range(PATH_LENGTH)])
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

        beta, gamma = self.compute_layers(delta, public_keys, shared_secrets)

        header = Header(alpha=alpha, beta=beta, gamma=gamma, credential=credential)

        return (first_hop, header)

    # ============================================================
    # LAYER COMPUTATION
    # ============================================================

    @timing
    def compute_gamma(self, betas: list[G1], shared_secret: Fr) -> G1:
        concatenate_encoding = b"".join(beta.serialize() for beta in betas) 
        return G1().hash(hmac.new(shared_secret.serialize(), concatenate_encoding, sha256).digest())

    @timing
    def initial_layer(self, destination: G1, shared_secrets: list[Fr]):
        beta = [destination + GENERATORS[0] * shared_secrets[-1]] + [-sum([GENERATORS[BETA_SIZE + j - 2*i] * shared_secrets[i] for i in range(j//2, PATH_LENGTH-1)]) for j in range(BETA_SIZE-1)]
        gamma = self.compute_gamma(beta,  shared_secrets[-1])
        return beta, gamma

    @timing
    def add_layer(self, next_hop: G1, beta: list[G1], gamma: G1, shared_secret: Fr):

        next_beta = [next_hop, gamma, *beta[:BETA_SIZE]]
        next_beta = [next_beta[i] +  GENERATORS[i] * shared_secret for i in range(BETA_SIZE)]

        next_gamma = self.compute_gamma(next_beta, shared_secret)
        return next_beta, next_gamma

    @timing
    def compute_layers(self, destination: G1, mixes: list[G1], shared_secrets: list[Fr]):
        beta, gamma = self.initial_layer(destination, shared_secrets)

        for i in range(-2, -PATH_LENGTH-1, -1): # 1, 0
            beta, gamma = self.add_layer(mixes[i+1], beta, gamma, shared_secrets[i])

        return beta, gamma
