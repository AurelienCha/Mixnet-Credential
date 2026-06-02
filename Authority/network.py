import asyncio

from codec import encode_message, decode_message
import log

PORT = 5000

class Network(asyncio.DatagramProtocol):
    
    def __init__(self, ip, handle_message):
        self.ip = ip
        self.handle_message = handle_message  # callback  # connect layers (i.e. using authority.py fct)

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
        msg_type, msg = decode_message(data)
        log.LOGGING(data=msg, sender=ip, comment=msg_type)
        
        if self.handle_message:
            asyncio.create_task(self.handle_message(ip, msg_type, msg))

    # =========================
    # SEND
    # =========================

    async def send(self, ip, msg_type, msg):
        log.LOGGING(data=msg, recipient=ip, comment=msg_type)
        self.transport.sendto(encode_message(msg_type, msg), (ip, PORT))