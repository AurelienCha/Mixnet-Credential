from __future__ import annotations
from typing import Any, Callable
import asyncio, json

from codec import encode_message, decode_message

PORT = 5000

class Network(asyncio.DatagramProtocol):
    
    def __init__(self, ip: str, handle_message: Callable, log: LoggerWrapper):
        self.ip = ip
        self.log = log
        self.handle_message = handle_message
        self.semaphore = asyncio.Semaphore(100)  # Prevent flooding attack by limiting how many packet-processing coroutines execute simultaneously (but packets are still received)

    # =========================
    # START
    # =========================

    async def start(self) -> None:
        loop = asyncio.get_running_loop()

        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self,
            local_addr=(self.ip, PORT),
        )

    # =========================
    # RECEIVE
    # =========================

    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        ip, _ = addr
        message_type, message = decode_message(data)

        self.log(data=message, sender=ip, comment=message_type)
        asyncio.create_task(self._safe_handle_message(ip, message_type, message))

    async def _safe_handle_message(self, ip: str, message_type: Stage, message: Any) -> None:
        async with self.semaphore:  # Prevent flooding attack
            await self.handle_message(ip, message_type, message)

    # =========================
    # SEND
    # =========================

    async def send(self, ip: str, message_type: Stage, message: Any) -> None:
        self.log(data=message, recipient=ip, comment=message_type)

        self.transport.sendto(
            encode_message(message_type, message),
            (ip, PORT),
        )