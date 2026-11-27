
#!/usr/bin/env bash
set -euo pipefail # prevent silent errors

# Resolve paths relative to setup.sh, regardless of where it was called.
ZK_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ZK_DIR"
export PATH="$ZK_DIR/node_modules/.bin:$PATH"

# Source: https://github.com/iden3/snarkjs

#########################
## Circuit Compilation ##
#########################

circom --r1cs --wasm -l node_modules circuit.circom