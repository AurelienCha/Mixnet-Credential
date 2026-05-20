import asyncio, argparse, json
from network import Network
from crypto import Crypto
from header import Header
from mclbn256 import Fr, G1, G2
from log import create_logger

from enum import StrEnum
from random import sample
import fcntl # for concurrency call

################################################################
def decode_ip(G): # IP-Point to IPv6
    n = int(G.tostr().split()[1].decode(), 16) >> 221 # unpadding
    return f"{(n>>24)&255}.{(n>>16)&255}.{(n>>8)&255}.{n&255}"
#################################################################

class Stage(StrEnum):
    SIGN_MIX = "SIGN-MIX"
    HEADER = "HEADER"

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

class Mixnode:
    def __init__(self, id, authority_PK, generators, signed_generators):
        self.ip = f"127.0.10.{id}"
        self.buffer = Buffer()
        self.log = create_logger("MIX", id)
        # Network
        self.network = Network(self.ip, self.handle_message)
        self.mixnodes = None
        # Crypto
        self.authority_PK = G2().fromstr(authority_PK.encode())
        self.generators = [G1().fromstr(g.encode()) for g in generators]
        self.signed_generator_sum = sum([G1().fromstr(g.encode()) for g in signed_generators[1:]], start=G1().fromstr(signed_generators[0].encode()))

        self.sk = Fr().randomize()
        self.PK = G1().base_point() * self.sk

    async def send(self, ip, msg_type, message):
        await self.network.send(ip, msg_type, message)

    async def handle_message(self, ip, msg_type, message):
        match msg_type:
            case Stage.SIGN_MIX:  # Authority
                await self.buffer.add((Fr(Crypto.hash(ip)), message))
                self.log(message, extra_param={"sender": ip, "stage": msg_type})
            case Stage.HEADER:  # Header to process
                if self.mixnodes is None: # if first time, fetch mixnodes signatures from public file
                    with open("public.json") as f:
                        self.mixnodes =  json.load(f)["mixnodes"]
                header = Header(self.generators, message)
                self.log(f"Received", extra_param={"sender": ip, "stage": msg_type})
                msg = await self.process_packet(header)
                next_ip = next((ip for ip, node in self.mixnodes.items() if node["PK"] == str(header.next_hop)), None) # Header
                if next_ip is None:
                    next_ip = decode_ip(header.next_hop)
                await self.send(next_ip, Stage.HEADER, msg)
                self.log(f"Send", extra_param={"recipient": next_ip, "stage": msg_type})

    async def start(self):
        await self.network.start()
    
    async def sign_public_key(self, authorities, threshold):
        for authority in sample(authorities, k=threshold):
            await self.send(authority, Stage.SIGN_MIX, self.PK)
        points = await self.buffer.wait(threshold)
        return Crypto.lagrange_interpolation(points)

    async def process_packet(self, header):
        header.verify_credential(self.authority_PK)
        shared_secret = header.compute_shared_secret(self.sk)
        
        header.verify_integrity(shared_secret)
        header.decrypt_beta(shared_secret)
        header.update_alpha(shared_secret)
        header.update_credential(shared_secret, self.signed_generator_sum, self.mixnodes)
        return header.encode()
    
# ===================== MAIN =====================
async def main(ID):
    with open("public.json") as f:
        config = json.load(f)

    node = Mixnode(
        id = ID,
        authority_PK = config['authority_PK'],
        generators = config['generators'],
        signed_generators = config['signed_generators'],
    )

    # == START ==
    await node.start()

    # == SIGN PK ==
    node.log("Signing public key", extra_param={"stage": Stage.SIGN_MIX})
    sign_PK = await node.sign_public_key(config['authorities'], config['threshold'])
    node.log("Public key is signed", extra_param={"stage": Stage.SIGN_MIX})
    # Update config file with mutex to prevent concurrent overwrite
    with open("public.json", "r+", encoding="utf-8") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        config = json.load(file)
        config['mixnodes'].update({node.ip: {'PK': str(node.PK), 'sign_PK': str(sign_PK)}})
        file.seek(0)
        json.dump(config, file, indent=4)
        file.truncate()
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
    node.log("Public Key and its signature are published (.json)", extra_param={"stage": Stage.SIGN_MIX})
    
    # == WAIT TO PROCESS PACKET ==
    await asyncio.Event().wait()  # <- keeps alive

# ===================== CLI =====================
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True)
    args = parser.parse_args()

    asyncio.run(main(args.id))