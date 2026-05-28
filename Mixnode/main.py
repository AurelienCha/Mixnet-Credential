
import asyncio, argparse, json, fcntl

from mixnode import Mixnode, load_public_config
from ECC import *


async def publish_mixnode(node: Mixnode, signed_public_key: G1) -> None:
    with open("public.json", "r+", encoding="utf-8") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)

        config = json.load(file)
        config["mixnodes"][node.ip] = {"PK": str(node.public_key), "sign_PK": str(signed_public_key)}

        file.seek(0)
        json.dump(config, file, indent=4)
        file.truncate()

        fcntl.flock(file.fileno(), fcntl.LOCK_UN)

# ============================================================
# MAIN
# ============================================================ 

async def main(node_id: int) -> None:

    node = Mixnode(node_id=node_id)

    # == START ==
    await node.start()

    # == SIGN and PUBLISH PK ==
    signed_public_key = await node.sign_public_key()
    await publish_mixnode(node, signed_public_key)  # UPDATE config file with mutex to prevent concurrent overwrite
    
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