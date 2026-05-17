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
    VERIF_MIX = "VERIF-MIX"


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
        # Network
        self.network = Network(ip, peers, self.handle_message)

        # Crypto
        self.crypto = Crypto(ip, threshold, generators)

        # Other
        self.logs = create_logger("AUTH", id+1)
        self.buffer = {
            Stage.SETUP_SHARES: Buffer(), 
            Stage.SIGN_PARAM: Buffer(), 
            Stage.VERIF_SETUP: Buffer(), 
            Stage.SIGN_MIX: Buffer(), 
            Stage.VERIF_MIX: Buffer(), 
        }
    
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

    async def send(self, peer_ip, msg_type, message):
        await self.network.send(peer_ip, msg_type, message)

    async def handle_message(self, peer_ip, msg_type, message):
        match msg_type:
            case Stage.SETUP_SHARES: 
                await self.buffer[msg_type].add(message)
            case Stage.SIGN_PARAM: 
                await self.buffer[msg_type].add(message)
            case Stage.VERIF_SETUP:
                await self.buffer[msg_type].add(message)
            case Stage.SIGN_MIX:
                await self.buffer[msg_type].add(message)
            case Stage.VERIF_MIX:
                await self.buffer[msg_type].add(message)
        self.log(message, extra_param={"sender": peer_ip, "stage": msg_type})
    
    async def setup(self):

        async def send_and_aggregate_shares():
            self.stage = Stage.SETUP_SHARES

            # Send shares to each authorities
            await self.buffer[self.stage].add(self.crypto.polynomial(self.network.ip))
            for peer_ip in self.network.peers:
                await self.send(peer_ip, self.stage, self.crypto.polynomial(peer_ip))  

            # Before aggregation needs to wait all shares
            y_shares = await self.buffer[self.stage].wait(len(self.network.peers)+1)
            self.crypto.aggregate_secret_key(y_shares)   
                   
        async def sign_params():
            self.stage = Stage.SIGN_PARAM

            # Own partial sign
            sign = self.crypto.sign_params()
            await self.buffer[self.stage].add(sign)

            # Send its partial sign to peers (circular send)
            selected_peers = islice(self.network.peers, self.crypto.threshold - 1)
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
            next_peer = next(iter(self.network.peers))
            await self.send(next_peer, self.stage, msg) 

            # Verify with received hash
            answer = await self.buffer[self.stage].wait(1)
            assert msg == answer[0]
            self.log("Setup finished succesfully")

        await send_and_aggregate_shares()
        signed_params = await sign_params()
        await verif_sign(signed_params)
        return signed_params
    
    async def sign_mixnodes(self, mixnodes):

        async def sign_mixes(mixnodes):
            self.stage = Stage.SIGN_MIX

            # individual sign of all mixnodes PK
            msg = [self.crypto.x] + [self.crypto.sign(G1().fromstr(mix['PK'].encode())) for mix in mixnodes.values()]
            await self.buffer[self.stage].add(msg)
            
            # send it to threshold number of peers
            selected_peers = islice(self.network.peers, self.crypto.threshold - 1)
            for peer_ip in selected_peers:
                await self.send(peer_ip, self.stage, msg.copy())  

            # wait and agggregate
            partial_signs = await self.buffer[self.stage].wait(self.crypto.threshold)
            x, *y_values = zip(*partial_signs)

            # Lagrange interpolation
            points_list = [list(zip(x, vals)) for vals in y_values]
            return [Crypto.lagrange_interpolation(points) for points in points_list]
        
        async def verif_sign(signed_mixnodes):
            self.stage = Stage.VERIF_MIX

            # Send signed params hashed to a peer
            msg = Crypto.hash(signed_mixnodes)
            next_peer = next(iter(self.network.peers))
            await self.send(next_peer, self.stage, msg) 

            # Verify with received hash
            answer = await self.buffer[self.stage].wait(1)
            assert msg == answer[0]
            self.log("Sign mixnodes succesfully")

        signed_mixnodes = await sign_mixes(mixnodes)
        await verif_sign(signed_mixnodes)
        return {k:(v,str(sign_v)) for sign_v, (k, v) in zip(signed_mixnodes, mixnodes.items())}


    async def start(self):
        await self.network.start()
        self.log(f"Starting: {self.network.ip}")

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
    await asyncio.sleep(0.1)

    # == SETUP Authority ==
    signed_generators = await node.setup()
    await asyncio.sleep(0.1)
    signed_mixnodes = await node.sign_mixnodes(config.pop('mixnodes'))

    if ID == 0:  # One of the authority make signature public
        config.update({"signed_generators": [str(sign_G) for sign_G in signed_generators]})
        config['mixnodes'] = signed_mixnodes
        with open("config2.json", "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

# ===================== CLI =====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True)
    args = parser.parse_args()

    asyncio.run(main(args.id))
