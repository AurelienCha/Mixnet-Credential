#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

repeats=5
benchmark_times=$(mktemp)
trap 'rm -f "$benchmark_times"' EXIT

# Record elapsed time while hiding command output.
time_step() {
    local stage="$1"
    shift
    local TIMEFORMAT="$stage %3R"
    { time "$@" >/dev/null 2>&1; } 2>>"$benchmark_times"
}

# Measure these four commands as one step.
generate_proof() {
    python generate_json_input.py
    snarkjs wtns calculate circuit_js/circuit.wasm input.json witness.wtns
    snarkjs wtns check circuit.r1cs witness.wtns
    snarkjs groth16 prove circuit_final.zkey witness.wtns proof.json public.json
}

printf '%-4s %12s %12s %12s %14s %12s\n' \
    'x' 'Compile(s)' 'Tau(s)' 'CRS(s)' 'Proof_gen(s)' 'Verify(s)'

for x in 4 8 12; do # 16 20 24 28 32 36 40; do
    : >"$benchmark_times"

    for ((repeat=1; repeat<=repeats; repeat++)); do
        time_step compile circom --r1cs --wasm -l node_modules circuit.circom
        time_step tau ./tau_ceremony.sh "$x"
        time_step crs ./common_reference_string.sh "$x"

        time_step proof generate_proof

        time_step verify snarkjs groth16 verify \
            verification_key.json public.json proof.json
    done

    awk -v x="$x" -v n="$repeats" '
        { total[$1] += $2 }
        END {
            printf "%-4s %12.3f %12.3f %12.3f %14.3f %12.3f\n", \
                x, total["compile"]/n, total["tau"]/n, total["crs"]/n, \
                total["proof"]/n, total["verify"]/n
        }
    ' "$benchmark_times"
done

# TIMEFORMAT='%3R seconds'

# for x in 4 8 12 16 20 24 28 32 36 40; do
#     # SETUP
#     time circom --r1cs --wasm -l node_modules circuit.circom >/dev/null 2>&1
#     time ./tau_ceremony.sh "$x" >/dev/null 2>&1
#     time ./common_reference_string.sh "$x" >/dev/null 2>&1

#     # Proof generation (sum all that)
#     time python generate_json_input.py >/dev/null 2>&1
#     time snarkjs wtns calculate circuit_js/circuit.wasm input.json witness.wtns >/dev/null 2>&1
#     time snarkjs wtns check circuit.r1cs witness.wtns >/dev/null 2>&1
#     time snarkjs groth16 prove circuit_final.zkey witness.wtns proof.json public.json >/dev/null 2>&1

#     # Proof verification
#     time snarkjs groth16 verify verification_key.json public.json proof.json >/dev/null 2>&1
# done
