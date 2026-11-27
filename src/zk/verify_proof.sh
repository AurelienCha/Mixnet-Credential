#!/usr/bin/env bash
set -euo pipefail

ZK_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ZK_DIR"
export PATH="$ZK_DIR/node_modules/.bin:$PATH"

VERIFICATION_KEY="$1"
PUBLIC="$2"
PROOF="$3"

######################
## PROOF GENERATION ##
######################

snarkjs groth16 verify ${VERIFICATION_KEY} ${PUBLIC} ${PROOF}