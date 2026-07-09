import argparse, asyncio

from Client.client import Client
from common.log import create_logger, LOGGING
from common.config import CREDENTIALS
from common.ECC import *

# ============================================================
# MAIN
# ============================================================

async def main(node_id: int, nbr_packets: int) -> None:

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
    await asyncio.gather(*(
        client.send_packet(own_ip)
        for _ in range(nbr_packets)
    ))

    while True:
        await asyncio.sleep(0.1)

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True, help="Client identifier")
    parser.add_argument("-x", "--packets", type=int, required=False, help="Send x packets", default=100)
    arguments = parser.parse_args()

    asyncio.run(main(arguments.id, arguments.packets))
