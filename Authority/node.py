import asyncio, argparse, json
from mclbn256 import G1, G2, Fr
from itertools import islice
from enum import StrEnum

from log import create_logger
from network import Network
from crypto import Crypto

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
        self.log = create_logger("AUTH", id)
        self.buffer = {
            Stage.SETUP_SHARES: Buffer(), 
            Stage.SIGN_PARAM: Buffer(), 
            Stage.VERIF_SETUP: Buffer(), 
        }
        self.stage = None

        # Network
        self.peers = peers
        self.network = Network(ip, self.handle_message, self.log)

        # Crypto
        self.crypto = Crypto(ip, threshold, generators)
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
                await self.send(ip, Stage.SIGN_MIX, self.crypto.sign(message))  # message = PK -> sign PK
            case Stage.SIGN_CLIENT:
                await self.send(ip, Stage.SIGN_CLIENT, self.crypto.sign(message)) 
        self.log({"data": message, "sender": ip, "stage": msg_type})
        self.log({"data": self.stage, "sender": ip, "stage": msg_type})
    
    async def setup(self):

        async def send_and_aggregate_shares():
            self.stage = Stage.SETUP_SHARES

            # Send shares to each authorities
            await self.buffer[self.stage].add(self.crypto.polynomial(self.network.ip))
            for peer_ip in self.peers:
                await self.send(peer_ip, self.stage, self.crypto.polynomial(peer_ip))  

            # Before aggregation needs to wait all shares
            y_shares = await self.buffer[self.stage].wait(len(self.peers)+1)
            self.crypto.aggregate_secret_key(y_shares)
            self.log({"data": self.crypto.secret_share, "stage": self.stage})
                   
        async def sign_params():
            self.stage = Stage.SIGN_PARAM

            # Own partial sign
            sign = self.crypto.sign_params()
            await self.buffer[self.stage].add(sign)

            # Send its partial sign to peers (circular send)
            selected_peers = islice(self.peers, self.crypto.threshold - 1)
            for peer_ip in selected_peers:
                await self.send(peer_ip, self.stage, sign.copy())  
            
            # Wait enough partial signatures (and transform into list of points)
            partial_signed_params = await self.buffer[self.stage].wait(self.crypto.threshold)
            x, *y_values = zip(*partial_signed_params)
            points_list = [list(zip(x, vals)) for vals in y_values]

            # Lagrange interpolation
            return [Crypto.lagrange_interpolation(points) for points in points_list]
        
        async def verif_sign(signed_params):
            self.stage = Stage.VERIF_SETUP

            # Send signed params hashed to a peer (next one)
            msg = Crypto.hash(signed_params)
            next_peer = next(iter(self.peers))
            await self.send(next_peer, self.stage, msg) 

            # Verify with received hash
            answer = await self.buffer[self.stage].wait(1)
            assert msg == answer[0]
            #self.log("Setup finished succesfully")

        await send_and_aggregate_shares()
        signed_params = await sign_params()
        await verif_sign(signed_params)
        return signed_params
  
    async def start(self):
        await self.network.start()
        self.log({"data": f"Starting: {self.network.ip}"})

# ===================== MAIN =====================
async def main(ID):
    with open("config.json") as f:
        config = json.load(f)

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
    print(node.network.ip, "FINISH")

    if ID == 1:  # One of the authority make signature public
        config.update({"signed_generators": [str(sign_G) for sign_G in signed_generators]})
        config.update({"authority_PK": str(authority_PK)})
        with open("public.json", "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

    await asyncio.Event().wait()  # <- keeps program alive

# ===================== CLI =====================
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True)
    args = parser.parse_args()

    asyncio.run(main(args.id))
