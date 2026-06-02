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
import json

from ECC import *
from config import CREDENTIALS 

if CREDENTIALS:
    @dataclass(slots=True)
    class PublicConfig:
        path_length: int
        authority_pk: G2
        generators: list[G1]
        signed_generators: list[G1]
        authorities: list[str]
        threshold: int
        nbr_mixnodes: int
        mixnodes: dict[str, Any]

    def load_public_config() -> PublicConfig:
        with open(".public.json", encoding="utf-8") as file:
            raw = json.load(file)

        return PublicConfig(
            path_length=raw["path_length"],
            authority_pk=G2().fromstr(raw["authority_PK"].encode()),
            generators=[G1().fromstr(value.encode()) for value in raw["generators"]],
            signed_generators=[G1().fromstr(value.encode()) for value in raw["signed_generators"]],
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
            raw = json.load(file)

        return PublicConfig(
            path_length=raw["path_length"],
            generators=[G1().fromstr(value.encode()) for value in raw["generators"]],
            nbr_mixnodes=raw["nbr_mixnodes"],
            mixnodes=raw["mixnodes"],
        )

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
    SIGNED_GENERATORS = config.signed_generators
else:
    THRESHOLD = None
    AUTHORITIES = None
    AUTHORITY_PK = None
    SIGNED_GENERATORS = None