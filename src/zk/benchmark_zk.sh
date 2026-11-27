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

for x in 4 8 12 16 20 24 28 32 36 40; do
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

# x      Compile(s)       Tau(s)       CRS(s)   Proof_gen(s)    Verify(s)
# 4           0.370       59.396       18.298          1.814        0.446
# 8           0.372       71.447       22.262          1.813        0.449
# 12          0.370       84.013       26.298          1.824        0.452
# 16          0.369       96.504       30.188          1.844        0.448
# 20          0.368      108.759       34.182          1.828        0.451
# 24          0.367      121.383       38.266          1.836        0.452
# 28          0.382      144.528       45.413          1.907        0.478
# 32          0.392      155.058       50.157          1.885        0.462
# 36          0.382      164.419       52.538          1.915        0.464
# 40          0.386      178.190       56.668          1.895        0.466