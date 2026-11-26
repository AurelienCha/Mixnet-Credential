
#!/usr/bin/env bash

N_AUTHORITIES=$1
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
