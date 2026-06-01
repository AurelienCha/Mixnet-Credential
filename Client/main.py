import argparse, asyncio

from client import Client
from log import create_logger
from config import CREDENTIALS

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
    await client.send_packet(own_ip) # TODO: send to self just for testing, change to real destination later

    #print(OP_COUNT) 
    # path=5: {'RND': {'Fr': 1, 'G1': 0, 'G2': 0}, 'ADD': {'Fr': 10, 'G1': 65, 'G2': 0, 'GT': 0}, 'MUL': {'Fr': 96, 'G1': 76, 'G2': 0, 'GT': 0}, 'FROM': {'G1': 5, 'G2': 0}, 'TO': {'G1': 0, 'G2': 0}, 'PAIR': 0, 'MAP': 2, 'UNMAP': 0}


    await asyncio.Event().wait()  # <- keeps program alive


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True, help="Client identifier")
    arguments = parser.parse_args()

    asyncio.run(main(arguments.id))
