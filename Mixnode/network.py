import asyncio
import json

from codec import encode_msg, decode_msg

PORT = 5000

class Network(asyncio.DatagramProtocol):
    
    def __init__(self, ip, handle_message, log):
        self.ip = ip
        self.on_message = handle_message  # callback  # connect layers (i.e. using authority.py fct)
        self.log = log

    # =========================
    # START
    # =========================

    async def start(self):
        loop = asyncio.get_running_loop()

        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self,
            local_addr=(self.ip, PORT)
        )

    # =========================
    # RECEIVE
    # =========================

    def datagram_received(self, data, addr):
        ip, _ = addr
        msg_type, msg = decode_msg(data)
        self.log({"data": msg, "sender": ip, "stage": msg_type})
        
        if self.on_message:
            asyncio.create_task(self.on_message(ip, msg_type, msg))

    # =========================
    # SEND
    # =========================

    async def send(self, ip, msg_type, msg):
        self.log({"data": msg, "recipient": ip, "stage": msg_type})
        self.transport.sendto(encode_msg(msg_type, msg), (ip, PORT))