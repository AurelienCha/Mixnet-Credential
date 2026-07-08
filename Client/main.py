import argparse, asyncio

from Client.client import Client
from common.log import create_logger
from Client.config import CREDENTIALS
from common.ECC import *

# ============================================================
# MAIN
# ============================================================

async def main(node_id: int) -> None:

    create_logger("CLIENT", node_id)
    client = Client(node_id=node_id)

    # == START Network ==
    await client.start()
    await asyncio.sleep(1)


    # == SIGN Credentials ==
    own_ip = client.network.ip
    if CREDENTIALS:
        client.credentials[own_ip] = (await client.get_credential(own_ip))

    # == SEND packet == 
    # while True:
    #     await client.send_packet(own_ip) # TODO: send to self just for testing, change to real destination later
    for _ in range(1):
        await client.send_packet(own_ip)

    while not client.shutdown_event.is_set():
        await asyncio.sleep(0.1)

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True, help="Client identifier")
    arguments = parser.parse_args()

    asyncio.run(main(arguments.id))
