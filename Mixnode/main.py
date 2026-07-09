import asyncio, argparse

from common.config import CREDENTIALS, NBR_MIXNODES, load_config, publish_mixnode
from Mixnode.mixnode import Mixnode
from common.log import create_logger
from common.ECC import *


# ============================================================
# MAIN
# ============================================================ 

async def main(node_id: int) -> None:

    create_logger("MIX", node_id)
    node = Mixnode(node_id=node_id)

    # == START ==
    await node.start()

    # == Publish Mixnode PK (and PK signed if CREDENTIALS) ==
    await publish_mixnode(node, await node.sign_public_key() if CREDENTIALS else None)
    
    # == WAIT TO PROCESS PACKET ==
    await asyncio.Event().wait()  # <- keeps alive

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True, help="Mixnode identifier")
    arguments = parser.parse_args()

    asyncio.run(main(arguments.id))