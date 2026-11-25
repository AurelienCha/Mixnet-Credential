#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 || -z ${3:-} ]]; then
    echo "Usage: bash $0 <ip_integer> <nonce> <output_prefix>" >&2
    exit 1
fi

ZK_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ZK_DIR"
export PATH="$ZK_DIR/node_modules/.bin:$PATH"

IP="$1"
NONCE="$2"
PREFIX="$3"

######################
## PROOF GENERATION ##
######################

# Remove private inputs and witnesses on success or failure.
trap 'rm -f -- "${PREFIX}_input.json" "${PREFIX}_witness.wtns"' EXIT

python3 generate_json_input.py --ip "$IP" --nonce "$NONCE" --output "${PREFIX}_input.json" --quiet

## Warning: Calculate the witness into a input.json file first then:
snarkjs wtns calculate circuit_js/circuit.wasm "${PREFIX}_input.json" "${PREFIX}_witness.wtns"

# Wheck the .wtns file is valid and corresponds to the circuit:
snarkjs wtns check circuit.r1cs "${PREFIX}_witness.wtns"

# Generate the proof and public input:
snarkjs groth16 prove circuit_final.zkey "${PREFIX}_witness.wtns" "${PREFIX}_proof.json" "${PREFIX}_public.json"
