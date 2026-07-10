import asyncio
from itertools import islice
from enum import StrEnum

from common.log import timing
from common.network import Network
from common.crypto import lagrange_interpolation, Polynomial

from common.ECC import *

class Stage(StrEnum):
    SETUP_SHARES = "SHARES"
    SIGN_PARAM = "SIGN-PARAM"
    SIGN_MIX = "SIGN-MIX"
    SIGN_CLIENT = "SIGN-CLIENT"

class Authority:
    def __init__(self, id, ip, peers, threshold, generators):
        # Other
        self.setup_queue = asyncio.Queue()
        self.sign_queue = asyncio.Queue()

        # Network
        self.peers = peers
        self.network = Network(ip, self.handle_message)

        # Crypto
        self.id = hash_to_Fr(ip.encode())
        self.threshold = threshold
        self.generators = [G1().fromstr(g.encode()) for g in generators[::2]]
        self.secret_share = None
        self.rnd_polynomial = Polynomial([Fr().randomize() for _ in range(self.threshold)])

    async def send(self, ip, msg_type, message):
        await self.network.send(ip, msg_type, message)

    async def handle_message(self, ip, msg_stage, message):
        match msg_stage:
            case Stage.SETUP_SHARES: 
                await self.setup_queue.put(message)
            case Stage.SIGN_PARAM:
                await self.sign_queue.put(message)
            case Stage.SIGN_MIX:
                await self.send(ip, Stage.SIGN_MIX, self.sign(message))  # message = PK -> sign PK
            case Stage.SIGN_CLIENT:
                await self.send(ip, Stage.SIGN_CLIENT, self.sign(message)) 

    @timing
    def sign(self, P):
        return P * self.secret_share

    def aggregate_secret_key(self, y_shares):
        self.secret_share = sum(y_shares, Fr(0))
    
    def sign_parameters(self):
        return [self.id, self.sign(G2().base_point())] + [self.sign(G) for G in self.generators]

    async def collect(self, queue, n): # non-negligeable time ? (to verify)
        return [await queue.get() for _ in range(n)]
    
    @timing
    async def setup(self):
        
        @timing
        async def send_and_aggregate_shares():

            # Send shares to each authorities
            await self.setup_queue.put(self.rnd_polynomial(self.id))

            await asyncio.gather(*(
                self.send(peer_ip, Stage.SETUP_SHARES, self.rnd_polynomial(hash_to_Fr(peer_ip.encode())))
                for peer_ip in self.peers
            ))

            # Before aggregation needs to wait all shares
            y_shares = await self.collect(self.setup_queue, len(self.peers) + 1)
            self.aggregate_secret_key(y_shares)
                   
        @timing
        async def sign_params():

            # Own partial sign
            sign = self.sign_parameters()
            await self.sign_queue.put(sign)

            # Send its partial sign to peers (circular send)
            selected_peers = islice(self.peers, self.threshold - 1)
            await asyncio.gather(*(    
                self.send(peer_ip, Stage.SIGN_PARAM, sign.copy())
                for peer_ip in selected_peers
            ))  
            
            # Wait enough partial signatures (and transform into list of points)
            partial_signed_params = await self.collect(self.sign_queue, self.threshold)
            x, *y_values = zip(*partial_signed_params)
            points_list = [list(zip(x, vals)) for vals in y_values]

            # Lagrange interpolation
            return [lagrange_interpolation(points) for points in points_list]

        await send_and_aggregate_shares()
        signed_params = await sign_params()
        
        return signed_params
  
    async def start(self):
        await self.network.start()
