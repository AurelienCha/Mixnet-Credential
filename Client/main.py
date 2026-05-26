
from dataclasses import dataclass
from typing import Any
import argparse
import asyncio
import json

from client import Client, encode_ip

from mclbn256 import Fr, G1, G2 
# ============================================================
# CONFIG LOADER
# ============================================================

@dataclass
class MixnodeInfo:
    public_key: G1
    signed_public_key: G1

@dataclass
class PublicConfig:
    path_length: int
    authority_pk: G2
    generators: list[G1]
    signed_generators: list[G1]
    authorities: list[str]
    threshold: int
    mixnodes: dict[str, Any]

def load_public_config() -> PublicConfig:
    with open("public.json", encoding="utf-8") as file:
        raw = json.load(file)

    return PublicConfig(
        path_length=raw["path_length"],
        authority_pk=G2().fromstr(raw["authority_PK"].encode()),
        generators=[G1().fromstr(value.encode()) for value in raw["generators"]],
        signed_generators=[G1().fromstr(value.encode()) for value in raw["signed_generators"]],
        authorities=raw["authorities"],
        threshold=raw["threshold"],
        mixnodes={ip: MixnodeInfo(
                public_key=G1().fromstr(node["PK"].encode()),
                signed_public_key=G1().fromstr(node["sign_PK"].encode()))
                for ip, node in raw["mixnodes"].items()},
    )

# ============================================================
# MAIN
# ============================================================

async def main(node_id: int) -> None:
    config = load_public_config()

    client = Client(node_id=node_id, config=config)

    # == START Network ==
    await client.start()
    await asyncio.sleep(1)

    # == SIGN Credentials ==
    own_ip = client.network.ip
    client.credentials[own_ip] = (await client.get_credential(encode_ip(own_ip)))

    # == SEND packet ==
    await client.send_packet(own_ip)

    await asyncio.Event().wait()  # <- keeps program alive


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True, help="Client identifier")
    arguments = parser.parse_args()

    asyncio.run(main(arguments.id))
