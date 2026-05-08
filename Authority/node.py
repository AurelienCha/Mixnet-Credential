import asyncio, argparse, json
from mclbn256 import G1, G2, Fr
from itertools import islice
from enum import StrEnum

from log import create_logger
from network import Network
from crypto import Crypto

class Stage(StrEnum):
    SETUP_SHARES = "SHARES"
    SIGN_PARAM = "SIGN"
    VERIF_SETUP = "VERIF"

class BufferEvent:
    # # TODO: Currently working fine but may be more robust to use a different buffer per steps
    # self.share_buffer = BufferEvent()
    # self.signature_buffer = BufferEvent()
    # self.verification_buffer = BufferEvent()
    # async def handle_message(self, peer_ip, msg):
    #     match msg["type"]:
    #         case "SETUP":
    #             self.share_buffer.add(msg["payload"])
    #         case "SIGN":
    #             self.signature_buffer.add(msg["payload"])
    #         case "VERIF":
    #             self.verification_buffer.add(msg["payload"])
    def __init__(self):
        self.threshold = None
        self.items = []
        self.event = asyncio.Event()

    def add(self, item):
        self.items.append(item)
        if (self.threshold is not None) and (len(self.items) >= self.threshold):
            self.event.set()

    async def wait(self, nbr_item):
        if self.threshold is None:
            self.threshold = nbr_item
        if len(self.items) >= self.threshold:
            self.event.set()
        await self.event.wait()
        return self.flush()

    def flush(self):
        tmp = self.items.copy()
        self.items.clear()
        self.event.clear()
        self.threshold = None
        return tmp

class Authority:
    def __init__(self, id, ip, peers, threshold, generators):
        # Network
        self.network = Network(ip, peers, port=6114)
        self.network.on_message = self.handle_message  # connect layers (i.e. using authority.py fct)

        # Crypto
        self.crypto = Crypto(ip, threshold, generators)

        # Other
        self.logs = create_logger("AUTH", id+1)
        self.buffer = BufferEvent()
    
    def log(self, msg, *, extra_param=None):
        if extra_param is not None:
            if isinstance(msg, list):
                data = ' '.join([str(type(m))[8:-2].split('.')[-1] for m in msg])
                self.logs.info(data, extra=extra_param)
            else:
                data = str(type(msg))[8:-2].split('.')[-1]
                self.logs.info(data, extra=extra_param)
        else:
            self.logs.info(msg)

    async def send(self, peer_ip, message):
        await self.network.send(peer_ip, message, self.stage)

    async def handle_message(self, peer_ip, msg, stage):
        self.buffer.add(msg)
        self.log(msg, extra_param={"sender": peer_ip, "stage": stage})
    
    async def setup(self):

        async def send_shares():
            self.stage = Stage.SETUP_SHARES
            self.buffer.add(self.crypto.polynomial(self.network.ip))
            for peer_ip in self.network.peers:
                await self.send(peer_ip, self.crypto.polynomial(peer_ip))  

        async def aggregate_shares(): 
            # Before aggregation needs to wait all shares
            y_shares = await self.buffer.wait(nbr_item=len(self.network.peers)+1)
            self.crypto.aggregate_secret_key(y_shares)   
                   
        async def sign_params():
            self.stage = Stage.SIGN_PARAM
            msg = self.crypto.sign_params()
            self.buffer.add(msg)
            
            selected_peers = islice(self.network.peers, self.crypto.threshold - 1)
            for peer_ip in selected_peers:
                await self.send(peer_ip, msg.copy())  
            
            partial_signed_params = await self.buffer.wait(nbr_item=self.crypto.threshold)
            x, *y_values = zip(*partial_signed_params)

            points_list = [list(zip(x, vals)) for vals in y_values]
            return [Crypto.lagrange_interpolation(points) for points in points_list]
        
        async def verif_sign(signed_params):
            self.stage = Stage.VERIF_SETUP

            # Send signed params hashed to a peer
            msg = Crypto.hash(signed_params)
            next_peer = next(iter(self.network.peers))
            await self.send(next_peer, msg) 

            # Verify with received hash
            answer = await self.buffer.wait(nbr_item=1)
            assert msg == answer[0]
            self.log("Setup finished succesfully")

        await send_shares()
        await aggregate_shares()
        signed_params = await sign_params()
        await verif_sign(signed_params)
        return signed_params

    async def start(self):
        await self.network.start()
        self.log(f"Listening on ({self.network.ip}, {self.network.port})")
        await self.network.connect()
        self.log(f"CONNECTED TO PEERS: {sum([0 if p is None else 1 for p in self.network.peers.values()])}/{len(self.network.peers)}")

# ===================== MAIN =====================
async def main(ID):
    with open("config.json") as f:
        config = json.load(f)

    node = Authority(
        id = ID,
        ip = config["authorities"][ID],
        peers = config["authorities"][ID+1:] + config["authorities"][:ID],
        threshold = config['threshold'],
        generators = config['generators']
    )

    # == START ==
    await node.start()

    # == SETUP Authority ==
    sign_generators = await node.setup()

    if ID == 0:  # One of the authority make signature public
        config.update({"signed_generators": [str(sign_G) for sign_G in sign_generators]})
        with open("config2.json", "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

# ===================== CLI =====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True)
    args = parser.parse_args()

    asyncio.run(main(args.id))
