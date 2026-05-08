import asyncio
import json

from codec import encode_msg, recv_msg

class Network:
    
    def __init__(self, ip, peers, port):
        self.ip = ip
        self.port = port

        self.peers = {p: None for p in peers}
        self.on_message = None  # callback

    async def start(self):
        async def handle_conn(reader, writer):

            peer_ip, _ = writer.get_extra_info("peername")
            self.peers[peer_ip] = (reader, writer)
            asyncio.create_task(self.listen(peer_ip, reader, writer))  
        
        self.server = await asyncio.start_server(handle_conn, self.ip, self.port)
        await asyncio.sleep(0.1)

    async def listen(self, peer_ip, reader, writer):
        try:
            while True:
                msg = await recv_msg(reader)
                if not msg:
                    break

                if self.on_message:
                    await self.on_message(peer_ip, msg)

        except Exception as e:
            print(f"[Network] error with {peer_ip}: {e}")
        finally:
            self.peers[peer_ip] = None
            writer.close()
            await writer.wait_closed()

    async def connect(self):
        for peer_ip in self.peers:
            if self.ip < peer_ip: # Do not duplicate connections
                reader, writer = await asyncio.open_connection(peer_ip, self.port, local_addr=(self.ip, 0))
                self.peers[peer_ip] = (reader, writer)
                asyncio.create_task(self.listen(peer_ip, reader, writer))
        
        while any(v is None for v in self.peers.values()):
            await asyncio.sleep(0.01)
        assert sum([0 if p is None else 1 for p in self.peers.values()]) == len(self.peers)

    async def send(self, ip, msg):
        conn = self.peers.get(ip)
        if not conn:
            return
        _, writer = conn
        writer.write(encode_msg(msg))
        await writer.drain()