import asyncio, argparse, json
from enum import StrEnum
from random import sample
import secrets, hashlib

from network import Network
from crypto import Crypto
from header import Header
from mclbn256 import Fr, G1, G2

################################################################
##########
## FROM ##
##########
def from_G1(self, other=None):
    return Fr(int(hashlib.sha256(self.serialize()).hexdigest(), 16) >> 3)
G1.__rshift__ = from_G1
def from_G2(self, other=None):
    return Fr(int(hashlib.sha256(self.serialize()).hexdigest(), 16) >> 3)
G2.__rshift__ = from_G2
def from_Fr(self, other):
    return other.mapfrom(self)
Fr.__rshift__ = from_Fr

# 253 bits (not 256, because BN uses a prime of 254 bits)
def encode_ip(ip): 
    a, b, c, d = map(int, ip.split('.'))
    ip = (a << 24) | (b << 16) | (c << 8) | d
    return G1().mapfrom(Fr((ip << (221))))# + secrets.randbits(221))) # padding: 221 = (256 - 3) - 32 # TODO

def decode_ip(G): # IP-Point to IPv6
    n = int(G.tostr().split()[1].decode(), 16) >> 221 # unpadding
    return f"{(n>>24)&255}.{(n>>16)&255}.{(n>>8)&255}.{n&255}"
#################################################################
class Stage(StrEnum):
    SIGN_CLIENT = "SIGN-CLIENT"
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

class Client:

    def __init__(self, config, id):
        self.network = Network(f"127.0.100.{id}", self.handle_message)
        self.threshold = config['threshold']
        self.authorities = config['authorities']

        self.generators = [G1().fromstr(g.encode()) for g in config['generators']]
        self.signed_generators = [G1().fromstr(g.encode()) for g in config['signed_generators']]
        self.authority_PK = G2().fromstr(config['authority_PK'].encode())

        self.mixnodes = {k: {
            'PK':G1().fromstr(v['PK'].encode()), 
            'sign_PK':G1().fromstr(v['sign_PK'].encode())
        } for (k,v) in config['mixnodes'].items()}

        self.buffer = Buffer()
        self.credentials = None

    async def start(self):
        await self.network.start()
        # send message periodically

    async def send(self, ip, msg_type, message):
        await self.network.send(ip, msg_type, message)

    async def handle_message(self, ip, msg_type, message):
        match msg_type:
            case Stage.SIGN_CLIENT:  # Authority
                await self.buffer.add(message)     
            case Stage.HEADER:
                print("RECEIVED:", message)
                pass
        pass
        # Message received are either:
        #   - from Authority (to get credentials)
        #   - from Mixnode (get a message)
    
    async def get_credential(self, destination): # TODO hide value with salt
        print(f"D = G1().fromstr('{destination}'.encode())")
        for authority in sample(self.authorities, k=self.threshold):
            await self.send(authority, Stage.SIGN_CLIENT, destination)
        points = await self.buffer.wait(self.threshold)

        
        credential = Crypto.lagrange_interpolation(points)
        print(f"C = G1().fromstr('{credential}'.encode())")
        print(destination * Fr(9055672386780370862397236484297163523090219802681336625303531130) == credential)
        return credential

    async def send_packet(self, destination):
        # Credential and nounce x
        credential = self.credentials[destination]
        x = Fr(1412)# Fr().randomize() # TODO

        # Random Path
        def select_mixnodes(path_length=3):
            path = sorted(list(self.mixnodes)) # sample(list(self.mixnodes), k=path_length) # TODO
            PK = [self.mixnodes[m]["PK"] for m in path]
            sign_PK = [self.mixnodes[m]["sign_PK"] for m in path]
            return path[0], PK, sign_PK
        first_hop, PK_mixes, sign_PK = select_mixnodes()

        # Compute Shared secret
        def derive_shared_secrets(x, PK_mixes):
            s1 = (PK_mixes[0] * x) >> Fr()
            x *= s1
            s2 = (PK_mixes[1] * x) >> Fr()
            x *= s2
            s3 = (PK_mixes[2] * x) >> Fr()
            return [s1, s2, s3]
        # def derive_shared_secrets(self, PK_mixes, x): # TODO optimized version
        #     secrets = []

        #     for pk in PK_mixes:
        #         s = (pk * x) >> Fr()
        #         secrets.append(s)
        #         x = x * s

        #     return secrets
        s = derive_shared_secrets(x, PK_mixes)
        print("s =", f"[Fr({s[0]}), Fr({s[1]}), Fr({s[2]})]")
        
        # Update Credential to the path
        def compute_credential(cred, s, signed_PK):
            print('-sG1-', self.signed_generators[0])
            print('-sG3-', self.signed_generators[1])
            print('-sG5-', self.signed_generators[2])
            m = cred \
                    + signed_PK[-1] + signed_PK[-2] \
                    + self.signed_generators[0] * (s[2] + s[1] + s[0]) \
                    + self.signed_generators[1] * (s[1] + s[0]) \
                    + self.signed_generators[2] * s[0] 
            
            print("-m-", m)
            return m
        credential = compute_credential(credential, s, sign_PK) 
        print(f"C0 = G1().fromstr('{str(credential)}'.encode())")

        header = Header(self.generators)
        header.build(encode_ip(destination), PK_mixes, s, credential, G1().base_point() * x)
        await self.send(first_hop, Stage.HEADER, header.encode())


# ===================== MAIN =====================
async def main(ID):
    with open("public.json") as f:
        config = json.load(f)

    node = Client(config, ID)

    # == START ==
    print("y = Crypto.lagrange_interpolation([P1,P2,P3])")
    print("print(y)")
    await node.start()

    node.credentials = {node.network.ip: await node.get_credential(encode_ip(node.network.ip))}

    dest = node.network.ip
    await node.send_packet(dest)

    await asyncio.Event().wait()  # <- keeps program alive

# ===================== CLI =====================
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True)
    args = parser.parse_args()

    asyncio.run(main(args.id))