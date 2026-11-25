
#!/usr/bin/env bash
set -euo pipefail # prevent silent errors


# Source: https://github.com/iden3/snarkjs

python generate_json_input.py

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
snarkjs powersoftau new bn128 13 pot10_0000.ptau -v                    
# Here 13, means max 2^13 = 8192 constraints
# Currently we have 5 375 constraints (2^12 < 5 375 < 2^13)

## CONTRIBUTIONS ##
snarkjs powersoftau contribute pot10_0000.ptau pot10_0001.ptau --name="Contribution 1" -v -e="Rnd text for Entropy 1"
snarkjs powersoftau contribute pot10_0001.ptau pot10_0002.ptau --name="Contribution 2" -v -e="Rnd text for Entropy 2"
snarkjs powersoftau contribute pot10_0002.ptau pot10_0003.ptau --name="Contribution 3" -v -e="Rnd text for Entropy 3"
snarkjs powersoftau contribute pot10_0003.ptau pot10_0004.ptau --name="Contribution 4" -v -e="Rnd text for Entropy 4"
# -e: prevent interaction (otherwise ask for random string)

## VERIFICATION ##   (of any contribution)
snarkjs powersoftau verify pot10_0004.ptau

## RANDOM FINAL BEACON ##  (to prevent manipulation)
snarkjs powersoftau beacon pot10_0004.ptau pot10_beacon.ptau 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f 10 -n="Final Beacon"
# 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f: some high entropy data publicly available, without prior knowledge
# 10: means hashing 10 times this data

## FINALIZATION and PREPARATION FOR PHASE 2 ##
snarkjs powersoftau prepare phase2 pot10_beacon.ptau pot10_final.ptau -v
snarkjs powersoftau verify pot10_final.ptau

##################################
## CRC: Common Reference String ## (Setup phase 2, Groth16, circuit specific)
##################################

## INITIALIZATION ##
snarkjs groth16 setup circuit.r1cs pot10_final.ptau circuit_0000.zkey

## CONTRIBUTIONS ##
snarkjs zkey contribute circuit_0000.zkey circuit_0001.zkey --name="Contribution 1" -v -e="Rnd text for Entropy 1"
snarkjs zkey contribute circuit_0001.zkey circuit_0002.zkey --name="Contribution 2" -v -e="Rnd text for Entropy 2"
snarkjs zkey contribute circuit_0002.zkey circuit_0003.zkey --name="Contribution 3" -v -e="Rnd text for Entropy 3"
snarkjs zkey contribute circuit_0003.zkey circuit_0004.zkey --name="Contribution 4" -v -e="Rnd text for Entropy 4"
# -e: prevent interaction (otherwise ask for random string)

# VERIFICATION ##   (of any contribution)
snarkjs zkey verify circuit.r1cs pot10_final.ptau circuit_0004.zkey

## RANDOM FINAL BEACON ##  (to prevent manipulation)
snarkjs zkey beacon circuit_0004.zkey circuit_final.zkey 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f 10 -n="Final Beacon phase2"

## EXPORT VERIFICATION KEY to JSON ##
snarkjs zkey export verificationkey circuit_final.zkey verification_key.json

######################
## PROOF GENERATION ##
######################

## Warning: Calculate the witness into a input.json file first then:
snarkjs wtns calculate circuit_js/circuit.wasm input.json witness.wtns
# or equivalently: node circuit_js/generate_witness.js circuit_js/circuit.wasm input.json witness.wtns

# Wheck the .wtns file is valid and corresponds to the circuit:
snarkjs wtns check circuit.r1cs witness.wtns

# Generate the proof and public input:
snarkjs groth16 prove circuit_final.zkey witness.wtns proof.json public.json

# NB: All these 3 commands can be run in a single command line:
# snarkjs groth16 fullprove input.json circuit_js/circuit.wasm circuit_final.zkey proof.json public.json


########################
## PROOF VERIFICATION ##
########################

snarkjs groth16 verify verification_key.json public.json proof.json

snarkjs groth16 verify verification_key.json 16937308711342903569326178973316892831150299428734892750260112584028824662645_public.json 16937308711342903569326178973316892831150299428734892750260112584028824662645_proof.json
