
#!/usr/bin/env bash
set -euo pipefail # prevent silent errors

if [[ $# -ne 1 || ! ${1:-} =~ ^[1-9][0-9]*$ ]]; then
    echo "Usage: bash $0 <number_of_authorities> (positive integer)" >&2
    exit 1
fi
N_AUTHORITIES=$1

# Resolve paths relative to setup.sh, regardless of where it was called.
ZK_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ZK_DIR"
export PATH="$ZK_DIR/node_modules/.bin:$PATH"

# Source: https://github.com/iden3/snarkjs

#########################
## Circuit Compilation ##
#########################

circom --r1cs --wasm -l node_modules circuit.circom

# The circom command takes one input (the circuit to compile, in our case
# circuit.circom) and several options:
#
# - r1cs: generates circuit.r1cs (the R1CS constraint system of the circuit
#   in binary format).
# - wasm: generates circuit.wasm (the WASM code to generate the witness –
#   more on that later).
# - c: generates C++ witness calculator code.
# - sym: generates circuit.sym (a symbols file required for debugging and
#   printing the constraint system in an annotated mode).
# - inspect: does additional checks over the constraints produced.
# - l: folder with circomlib (https://github.com/iden3/circomlib/tree/master)

## print circuit stats: snarkjs r1cs info circuit.r1cs    
## print constraints: snarkjs r1cs print circuit.r1cs circuit.sym
## export to json: snarkjs r1cs export json circuit.r1cs circuit.r1cs.json


#####################
## Ceremony of Tau ## (Setup phase 1, circuit independent)
#####################

## INITIALIZATION ##
snarkjs powersoftau new bn128 13 pot_0000.ptau -v                    
# Here 13, means max 2^13 = 8192 constraints
# Currently we have 5 375 constraints (2^12 < 5 375 < 2^13)

## CONTRIBUTIONS ##
last_tau="pot_0000.ptau"
for ((i = 1; i <= N_AUTHORITIES; i++)); do
    printf -v next_tau 'pot_%04d.ptau' "$i"
    snarkjs powersoftau contribute "$last_tau" "$next_tau" --name="Contribution $i" -v -e="Rnd text for Entropy $i"
    last_tau="$next_tau"
done
# -e: prevent interaction (otherwise ask for random string)

## VERIFICATION ##   (of any contribution)
snarkjs powersoftau verify "$last_tau"

## RANDOM FINAL BEACON ##  (to prevent manipulation)
snarkjs powersoftau beacon "$last_tau" pot_beacon.ptau 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f 10 -n="Final Beacon"
# 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f: some high entropy data publicly available, without prior knowledge
# 10: means hashing 10 times this data

## FINALIZATION and PREPARATION FOR PHASE 2 ##
snarkjs powersoftau prepare phase2 pot_beacon.ptau pot_final.ptau -v
snarkjs powersoftau verify pot_final.ptau

##################################
## CRC: Common Reference String ## (Setup phase 2, Groth16, circuit specific)
##################################

## INITIALIZATION ##
snarkjs groth16 setup circuit.r1cs pot_final.ptau circuit_0000.zkey

## CONTRIBUTIONS ##
last_zkey="circuit_0000.zkey"
for ((i = 1; i <= N_AUTHORITIES; i++)); do
    printf -v next_zkey 'circuit_%04d.zkey' "$i"
    snarkjs zkey contribute "$last_zkey" "$next_zkey" --name="Contribution $i" -v -e="Rnd text for Entropy $i"
    last_zkey="$next_zkey"
done
# -e: prevent interaction (otherwise ask for random string)

# VERIFICATION ##   (of any contribution)
snarkjs zkey verify circuit.r1cs pot_final.ptau "$last_zkey"

## RANDOM FINAL BEACON ##  (to prevent manipulation)
snarkjs zkey beacon "$last_zkey" circuit_final.zkey 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f 10 -n="Final Beacon phase2"

## EXPORT VERIFICATION KEY to JSON ##
snarkjs zkey export verificationkey circuit_final.zkey verification_key.json
