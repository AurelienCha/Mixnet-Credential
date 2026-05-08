import json 
from random import randint

from mclbn256 import G1, G2, GT, Fr

NBR_AUTHORITIES = 5

data = {
    "threshold": 3,
    "authorities": [f"127.0.1.{i}" for i in range(1,NBR_AUTHORITIES+1)],
    "generators": [str(G1().randomize()) for _ in range(7)],
}

with open("config.json", "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4)