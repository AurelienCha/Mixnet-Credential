import asyncio, argparse, json
from itertools import islice

from Authority.authority import Authority
from common.log import create_logger
from common.ECC import *


async def main(ID):
    with open(".config.json") as f:
        config = json.load(f)


    create_logger("AUTH", ID)
    node = Authority(
        id = ID,
        ip = config["authorities"][ID-1],
        peers = config["authorities"][ID:] + config["authorities"][:ID-1],
        threshold = config['threshold'],
        generators = config['generators']
    )

    # == START ==
    await node.start()
    await asyncio.sleep(1)

    # == SETUP Authority ==
    authority_PK, *signed_generators = await node.setup()

    if ID == 1:  # One of the authority make signature public
        config.update({"signed_generator_sums": [str(sum(signed_generators[:i])) for i in range(1, len(signed_generators)+1)]}) # [str(sign_G) for sign_G in signed_generators]})
        config.update({"authority_PK": str(authority_PK)})
        with open(".config.json", "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

    await asyncio.Event().wait()  # <- keeps program alive

# ===================== CLI =====================
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, required=True)
    args = parser.parse_args()

    try:
        asyncio.run(main(args.id))

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
