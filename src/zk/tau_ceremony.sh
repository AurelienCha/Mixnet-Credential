N_AUTHORITIES=$1
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