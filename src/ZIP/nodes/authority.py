import asyncio, argparse, json, sys
from itertools import islice
from enum import StrEnum

from utils.logging import timing, create_logger
from protocol.network import Network
from cryptomath.lagrange import lagrange_interpolation
from cryptomath.polynomial import Polynomial
from cryptomath.ecc import Fr, G1, G2, hash_to_Fr
from config.config import publish_authority_setup, AUTHORITIES, THRESHOLD

class Stage(StrEnum):
    SETUP_SHARES = "SHARES"
    SIGN_PARAM = "SIGN-PARAM"
    SIGN_CLIENT = "SIGN-CLIENT"

class Authority:
    def __init__(self, ID):
        # Other
        self.setup_queue = asyncio.Queue()
        self.sign_queue = asyncio.Queue()

        # Network
        self.ip = AUTHORITIES[ID-1]
        self.peers = AUTHORITIES[ID:] + AUTHORITIES[:ID-1]
        self.network = Network(self.ip, self.handle_message)

        # Crypto
        self.id = hash_to_Fr(self.ip.encode())
        self.threshold = THRESHOLD
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
            case Stage.SIGN_CLIENT:
                await self.send_credential(ip, message) 
    
    async def send_credential(self, ip, blinded_destination):
        # TODO add ZK proof verification stuff
        r = Fr().randomize()
        credential = [blinded_destination * (self.secret_share + r), G1().base_point() * (self.secret_share + r), G2().base_point() * r]
        await self.send(ip, Stage.SIGN_CLIENT, credential) # Credential = [Delta * (y+r), G1 * (y+r), G2 * r]
    
        
    def sign(self, P):
        return P * self.secret_share

    def aggregate_secret_key(self, y_shares):
        self.secret_share = sum(y_shares, Fr(0))

    async def collect(self, queue, n): # non-negligeable time ? (to verify)
        return [await queue.get() for _ in range(n)]
    
    @timing
    async def setup(self):
        
        @timing
        async def send_and_aggregate_shares(): # Obtain its secret share

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
        async def sign_params(): # sign parameter -> Public key of the authority

            # Own partial sign
            sign = [self.id, self.sign(G2().base_point())] # (x, y)
            await self.sign_queue.put(sign)

            # Send its partial sign to peers (circular send)
            selected_peers = islice(self.peers, self.threshold - 1)
            await asyncio.gather(*(    
                self.send(peer_ip, Stage.SIGN_PARAM, sign.copy())
                for peer_ip in selected_peers
            ))  
            
            # Wait enough partial signatures (and transform into list of points)
            partial_signed_params = await self.collect(self.sign_queue, self.threshold) 

            # Lagrange interpolation
            return lagrange_interpolation(partial_signed_params) # TODO now the only params is the Public key Y (change name in code for clarity)

        await send_and_aggregate_shares()
        signed_params = await sign_params()
        
        return signed_params # TODO now the only params is the Public key Y (change name in code for clarity)
  
    async def start(self):
        await self.network.start()



# ============================================================
# MAIN
# ============================================================ 

async def main(ID):
    create_logger("AUTH", ID)
    node = Authority(ID = ID)

    # == START ==
    await node.start()
    await asyncio.sleep(1)

    # == SETUP Authority ==
    authority_PK = await node.setup()

    if ID == 1:  # One of the authority make signature public
        publish_authority_setup(authority_pk=authority_PK)

    await asyncio.Event().wait()  # <- keeps program alive

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True)
    args = parser.parse_args()

    asyncio.run(main(args.id))
    # try:
    #     asyncio.run(main(args.id))

    # except Exception as e:
    #     print(f"ERROR: {type(e).__name__}: {e}")
    #     sys.exit(1)

