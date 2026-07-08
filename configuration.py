import argparse, json
from random import randint,seed

from mclbn256 import G1, G2, GT, Fr

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path_length", type=int, required=True)
parser.add_argument("-t", "--threshold", type=int, required=True)
parser.add_argument("-a", "--authorities", type=int, required=True)
parser.add_argument("-m", "--mixnodes", type=int, required=True)
args = parser.parse_args()

data = {
    "path_length": args.path_length,
    "threshold": args.threshold,
    "nbr_authorities": args.authorities,
    "nbr_mixnodes": args.mixnodes,
    "authorities": [f"127.0.1.{i}" for i in range(1,args.authorities+1)],
    "mixnodes": {},
    "generators": [str(G1().randomize()) for _ in range(2 * args.path_length + 1)],
}

with open(".config.json", "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4)
