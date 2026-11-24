from __future__ import annotations

import json
import fcntl
from dataclasses import dataclass
from pathlib import Path
from os import getenv
from typing import Any

from cryptomath.ecc import G1, G2


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
    PK: G1 

    @classmethod
    def from_json(cls, data: dict[str, str]) -> MixnodeInfo:
        return cls(
            ip=data["IP"],
            PK=G1().fromstr(data["PK"].encode())
        )


@dataclass(slots=True)
class PublicConfig:
    path_length: int
    nbr_mixnodes: int
    mixnodes: dict[str, Any]

    # Optional credential fields
    authority_pk_g1: G1 | None = None
    authority_pk: G2 | None = None
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
        nbr_mixnodes=raw["nbr_mixnodes"],
        mixnodes={G1().fromstr(N.encode()): MixnodeInfo.from_json(node) for N, node in raw["mixnodes"].items()},
    )

    if CREDENTIALS:
        config.authorities = raw["authorities"]
        config.threshold = raw["threshold"]
        try:
            config.authority_pk = G2().fromstr(raw["authority_PK"].encode())
            config.authority_pk_g1 = G1().fromstr(raw["authority_PK_G1"].encode())
        except:
            pass

    return config


def publish_authority_setup(authority_pk: G2, authority_pk_g1: G1) -> None:
    with LockedFile(CONFIG_PATH, "r+") as file:
        config = json.load(file)

        config["authority_PK"] = str(authority_pk)
        config["authority_PK_G1"] = str(authority_pk_g1)

        file.seek(0)
        json.dump(config, file, indent=4)
        file.truncate()


async def publish_mixnode(node: Mixnode) -> None:

    with LockedFile(CONFIG_PATH, "r+") as file:
        config = json.load(file)

        config["mixnodes"][str(node.N)] = {"IP": node.ip, "PK":str(node.public_key)}

        file.seek(0)
        json.dump(config, file, indent=4)
        file.truncate()


# ============================================================
# GLOBAL CONFIGURATION
# ============================================================

CONFIG = load_config()

NBR_MIXNODES = CONFIG.nbr_mixnodes
MIXNODES = CONFIG.mixnodes  # {G1(N): {"IP": str(ip), "PK": G1(PK)}}

PATH_LENGTH = CONFIG.path_length
BETA_SIZE = 2 * PATH_LENGTH - 1

# Optional credential fields
THRESHOLD = CONFIG.threshold
AUTHORITIES = CONFIG.authorities
AUTHORITY_PK = CONFIG.authority_pk
AUTHORITY_PK_G1 = CONFIG.authority_pk_g1