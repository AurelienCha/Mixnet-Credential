from __future__ import annotations

import json
import fcntl
from dataclasses import dataclass
from pathlib import Path
from os import getenv
from typing import Any

from common.ECC import G1, G2


# ============================================================
# SETTINGS
# ============================================================

CREDENTIALS = getenv("CREDENTIALS") == "1"
CONFIG_PATH = Path(".config.json")


# ============================================================
# DATA MODELS
# ============================================================

@dataclass(slots=True)
class MixnodeInfo:
    ip: str
    signed_public_key: G1 | None = None  # Optional credential fields

    @classmethod
    def from_json(cls, data: dict[str, str]) -> MixnodeInfo:
        return cls(
            ip=data["IP"],
            signed_public_key=(G1().fromstr(data["sign_PK"].encode()) if CREDENTIALS else None),
        )


@dataclass(slots=True)
class PublicConfig:
    path_length: int
    generators: list[G1]
    nbr_mixnodes: int
    mixnodes: dict[str, Any]

    # Optional credential fields
    authority_pk: G2 | None = None
    signed_generator_sums: list[G1] | None = None
    authorities: list[str] | None = None
    threshold: int | None = None


# ============================================================
# FILE LOCKING HELPERS
# ============================================================

class LockedFile:
    """Small helper for safe file locking."""

    def __init__(self, path: Path, mode: str):
        self.path = path
        self.mode = mode
        self.file = None

    def __enter__(self):
        self.file = self.path.open(self.mode, encoding="utf-8")
        fcntl.flock(self.file.fileno(), fcntl.LOCK_EX)
        return self.file

    def __exit__(self, *_):
        fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        self.file.close()


# ============================================================
# CONFIG MANAGEMENT
# ============================================================

def load_config() -> PublicConfig:
    with LockedFile(CONFIG_PATH, "r") as file:
        raw = json.load(file)

    config = PublicConfig(
        path_length=raw["path_length"],
        generators=[G1().fromstr(value.encode()) for value in raw["generators"]],
        nbr_mixnodes=raw["nbr_mixnodes"],
        mixnodes={G1().fromstr(PK.encode()): MixnodeInfo.from_json(node) for PK, node in raw["mixnodes"].items()},
    )

    if CREDENTIALS:
        config.authorities = raw["authorities"]
        config.threshold = raw["threshold"]
        try:
            config.authority_pk = G2().fromstr(raw["authority_PK"].encode())
            config.signed_generator_sums = [G1().fromstr(value.encode()) for value in raw["signed_generator_sums"]]
        except:
            pass

    return config


async def publish_mixnode(node: Mixnode, signed_public_key: G1 | None = None) -> None:

    with LockedFile(CONFIG_PATH, "r+") as file:
        config = json.load(file)

        entry = {"IP": str(node.ip)}

        if CREDENTIALS:
            entry["sign_PK"] = str(signed_public_key)

        config["mixnodes"][str(node.public_key)] = entry

        file.seek(0)
        json.dump(config, file, indent=4)
        file.truncate()


# ============================================================
# GLOBAL CONFIGURATION
# ============================================================

CONFIG = load_config()

GENERATORS = CONFIG.generators
NBR_MIXNODES = CONFIG.nbr_mixnodes
MIXNODES = CONFIG.mixnodes  # {PK: {IP, PK_sign}}

PATH_LENGTH = CONFIG.path_length
BETA_SIZE = 2 * PATH_LENGTH - 1

# Optional credential fields
THRESHOLD = CONFIG.threshold
AUTHORITIES = CONFIG.authorities
AUTHORITY_PK = CONFIG.authority_pk
SIGNED_GENERATOR_SUMS = CONFIG.signed_generator_sums