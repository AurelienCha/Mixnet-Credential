import argparse, json
from random import randint,seed

from mclbn256 import G1, G2, GT, Fr

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--threshold", type=int, required=True)
parser.add_argument("-a", "--authorities", type=int, required=True)
args = parser.parse_args()

data = {
    "threshold": args.threshold,
    "authorities": [f"127.0.1.{i}" for i in range(1,args.authorities+1)],
    "mixnodes": {},
    "generators": [str(G1().randomize()) for _ in range(7)],
}

with open("config.json", "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4)