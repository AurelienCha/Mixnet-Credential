from __future__ import annotations

# ============================================================
# SCRIPT VARIABLES
# ============================================================

from os import getenv
CREDENTIALS = True if getenv("CREDENTIALS") == "1" else False

# ============================================================
# CONFIG LOADER
# ============================================================

from dataclasses import dataclass
from typing import Any
import json, fcntl
from time import sleep 

from ECC import *
from config import CREDENTIALS 

if CREDENTIALS:
    @dataclass(slots=True)
    class PublicConfig:
        path_length: int
        authority_pk: G2
        generators: list[G1]
        signed_generator_sum: G1
        authorities: list[str]
        threshold: int
        nbr_mixnodes: int
        mixnodes: dict[str, Any]

    def load_public_config() -> PublicConfig:
        with open(".public.json", "r", encoding="utf-8") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            raw = json.load(file)
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)

            return PublicConfig(
                path_length=raw["path_length"],
                authority_pk=G2().fromstr(raw["authority_PK"].encode()),
                generators=[G1().fromstr(value.encode()) for value in raw["generators"]],
                signed_generator_sum=G1().fromstr(raw["signed_generator_sums"][-1].encode()),
                authorities=raw["authorities"],
                threshold=raw["threshold"],
                nbr_mixnodes=raw["nbr_mixnodes"],
                mixnodes=raw["mixnodes"],
            )

else:
    @dataclass(slots=True)
    class PublicConfig:
        path_length: int
        generators: list[G1]
        nbr_mixnodes: int
        mixnodes: dict[str, Any]

    def load_public_config() -> PublicConfig:
        with open(".public.json", encoding="utf-8") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            raw = json.load(file)
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)

            return PublicConfig(
                path_length=raw["path_length"],
                generators=[G1().fromstr(value.encode()) for value in raw["generators"]],
                nbr_mixnodes=raw["nbr_mixnodes"],
                mixnodes=raw["mixnodes"],
            )


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

config = load_public_config()

GENERATORS = config.generators
NBR_MIXNODES = config.nbr_mixnodes
MIXNODES = config.mixnodes

PATH_LENGTH = config.path_length
BETA_SIZE = 2 * PATH_LENGTH - 1

if CREDENTIALS:
    THRESHOLD = config.threshold
    AUTHORITIES = config.authorities
    AUTHORITY_PK = config.authority_pk
    SIGNED_GENERATOR_SUM = config.signed_generator_sum
else:
    THRESHOLD = None
    AUTHORITIES = None
    AUTHORITY_PK = None
    SIGNED_GENERATOR_SUM = None