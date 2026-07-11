import asyncio
import socket

from protocol.codec import encode_message, decode_message
import utils.logging as log

PORT = 5000


class Network(asyncio.DatagramProtocol):

    def __init__(self, ip, handle_message):
        self.ip = ip
        self.handle_message = handle_message # callback
        self.message_queue = asyncio.Queue(maxsize=-1)

    # =========================
    # START
    # =========================

    async def start(self):
        loop = asyncio.get_running_loop()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Kernel UDP buffer
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)

        sock.bind((self.ip, PORT))

        self.transport, _ = await loop.create_datagram_endpoint(lambda: self, sock=sock)

        asyncio.create_task(self.process_messages())

    # =========================
    # RECEIVE
    # =========================

    def datagram_received(self, data, addr):
        ip, _ = addr
        self.message_queue.put_nowait((ip, data))

    # =========================
    # PROCESSING WORKERS
    # =========================

    async def process_messages(self):
        while True:
            ip, data = await self.message_queue.get()

            try:
                msg_type, msg = decode_message(data)
                log.LOGGING(data=msg, sender=ip, comment=msg_type)
                await self.handle_message(ip, msg_type, msg)
                
            except Exception as e:
                print(f"Error processing packet: {e}")

            finally:
                self.message_queue.task_done()

    # =========================
    # SEND
    # =========================

    async def send(self, ip, msg_type, msg):
        log.LOGGING(data=msg, recipient=ip, comment=msg_type)
        self.transport.sendto(encode_message(msg_type, msg), (ip, PORT))