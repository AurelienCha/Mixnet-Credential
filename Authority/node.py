import asyncio, argparse, json
from itertools import islice
from enum import StrEnum

from common.log import create_logger, timing
from common.network import Network
from common.crypto import lagrange_interpolation, Polynomial

from common.ECC import *

class Stage(StrEnum):
    SETUP_SHARES = "SHARES"
    SIGN_PARAM = "SIGN-PARAM"
    VERIF_SETUP = "VERIF-PARAM"
    SIGN_MIX = "SIGN-MIX"
    SIGN_CLIENT = "SIGN-CLIENT"


class Buffer:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def add(self, item):
        await self.queue.put(item)

    async def wait(self, n): 
        items = []
        for _ in range(n):
            item = await self.queue.get()
            items.append(item)
        return items

class Authority:
    def __init__(self, id, ip, peers, threshold, generators):
        # Other
        self.buffer = {
            Stage.SETUP_SHARES: Buffer(), 
            Stage.SIGN_PARAM: Buffer(), 
            Stage.VERIF_SETUP: Buffer(), 
        }
        self.stage = None

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

    async def handle_message(self, ip, msg_type, message):
        match msg_type:
            case Stage.SETUP_SHARES: 
                await self.buffer[msg_type].add(message)
            case Stage.SIGN_PARAM:
                await self.buffer[msg_type].add(message)
            case Stage.VERIF_SETUP:
                await self.buffer[msg_type].add(message)
            case Stage.SIGN_MIX:
                await self.send(ip, Stage.SIGN_MIX, self.sign_mix(message))  # message = PK -> sign PK
            case Stage.SIGN_CLIENT:
                await self.send(ip, Stage.SIGN_CLIENT, self.sign_client(message)) 
    
    @timing
    def sign_mix(self, P):
        return self.sign(P)

    @timing
    def sign_client(self, P):
        return self.sign(P)

    def sign(self, P):
        return P * self.secret_share

    def aggregate_secret_key(self, y_shares):
        self.secret_share = sum(y_shares, Fr(0))
    
    def sign_parameters(self):
        return [self.id, self.sign(G2().base_point())] + [self.sign(G) for G in self.generators]
    
    
    @timing
    async def setup(self):
        
        @timing
        async def send_and_aggregate_shares():
            self.stage = Stage.SETUP_SHARES

            # Send shares to each authorities
            await self.buffer[self.stage].add(self.rnd_polynomial(self.id))
            for peer_ip in self.peers:
                peer_id = hash_to_Fr(peer_ip.encode())
                await self.send(peer_ip, self.stage, self.rnd_polynomial(peer_id))  

            # Before aggregation needs to wait all shares
            y_shares = await self.buffer[self.stage].wait(len(self.peers)+1)
            self.aggregate_secret_key(y_shares)
                   
        @timing
        async def sign_params():
            self.stage = Stage.SIGN_PARAM

            # Own partial sign
            sign = self.sign_parameters()
            await self.buffer[self.stage].add(sign)

            # Send its partial sign to peers (circular send)
            selected_peers = islice(self.peers, self.threshold - 1)
            for peer_ip in selected_peers:
                await self.send(peer_ip, self.stage, sign.copy())  
            
            # Wait enough partial signatures (and transform into list of points)
            partial_signed_params = await self.buffer[self.stage].wait(self.threshold)
            x, *y_values = zip(*partial_signed_params)
            points_list = [list(zip(x, vals)) for vals in y_values]

            # Lagrange interpolation
            return [lagrange_interpolation(points) for points in points_list]

        await send_and_aggregate_shares()
        signed_params = await sign_params()
        
        return signed_params
  
    async def start(self):
        await self.network.start()

# ===================== MAIN =====================
async def main(ID):
    with open(".config.json") as f:
        config = json.load(f)


    create_logger("AUTH", ID)
    node = Authority(
        id = ID,
        ip = config["authorities"][ID-1],
        peers = config["authorities"][ID:] + config["authorities"][:ID-1],
        threshold = config['threshold'],
        generators = config['generators']
    )

    # == START ==
    await node.start()
    await asyncio.sleep(1)

    # == SETUP Authority ==
    authority_PK, *signed_generators = await node.setup()

    if ID == 1:  # One of the authority make signature public
        config.update({"signed_generator_sums": [str(sum(signed_generators[:i])) for i in range(1, len(signed_generators)+1)]}) # [str(sign_G) for sign_G in signed_generators]})
        config.update({"authority_PK": str(authority_PK)})
        with open(".public.json", "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

    await asyncio.Event().wait()  # <- keeps program alive

# ===================== CLI =====================
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True)
    args = parser.parse_args()

    asyncio.run(main(args.id))
