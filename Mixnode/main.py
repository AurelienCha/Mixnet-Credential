
import asyncio, argparse, json, fcntl

from config import CREDENTIALS, NBR_MIXNODES, load_public_config
from mixnode import Mixnode
from log import create_logger
from ECC import *


async def publish_mixnode(node: Mixnode, signed_public_key: G1) -> None:
    with open(".public.json", "r+", encoding="utf-8") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)

        config = json.load(file)
        if CREDENTIALS:
            config["mixnodes"][node.ip] = {"PK": str(node.public_key), "sign_PK": str(signed_public_key)}
        else:
            config["mixnodes"][node.ip] = {"PK": str(node.public_key)}

        file.seek(0)
        json.dump(config, file, indent=4)
        file.truncate()

        fcntl.flock(file.fileno(), fcntl.LOCK_UN)

# ============================================================
# MAIN
# ============================================================ 

async def main(node_id: int) -> None:

    create_logger("MIX", node_id)
    node = Mixnode(node_id=node_id)

    # == START ==
    await node.start()

    # == SIGN and PUBLISH PK ==
    if CREDENTIALS:
        await publish_mixnode(node, await node.sign_public_key())  # UPDATE config file with mutex to prevent concurrent overwrite
    else:
        await publish_mixnode(node, None)
    
    # == WAIT ALL MIXNODES HAVE PUBLISHED THEIR PUBLIC KEYS ==
    while True:
        node.mixnodes = load_public_config().mixnodes
        if NBR_MIXNODES ==  len(node.mixnodes): 
            node.pk_to_ip = {
                node["PK"]: ip
                for ip, node in node.mixnodes.items()
            }

            node.sign_pk_lookup = {
                node["PK"]: G1().fromstr(node["sign_PK"].encode())
                for node in node.mixnodes.values()
            } if CREDENTIALS else None
            break
        await asyncio.sleep(0.5)
    
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