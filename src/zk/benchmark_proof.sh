#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

repeats=1000
cpu_csv="../benchmark/data/zk_cpu_times.csv"

# Record elapsed time while hiding command output.
time_step() {
    local stage="$1"
    shift
    local TIMEFORMAT="$stage, 0, %3R"
    { time "$@" >/dev/null 2>&1; } 2>>"$cpu_csv"
}

# Measure these four commands as one step.
generate_proof() {
    python generate_json_input.py
    snarkjs wtns calculate circuit_js/circuit.wasm input.json witness.wtns
    snarkjs wtns check circuit.r1cs witness.wtns
    snarkjs groth16 prove circuit_final.zkey witness.wtns proof.json public.json
}

for ((repeat=1; repeat<=repeats; repeat++)); do
    time_step proof generate_proof

    time_step verify snarkjs groth16 verify verification_key.json public.json proof.json
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