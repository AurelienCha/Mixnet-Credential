#!/bin/bash

src="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$src"
export PYTHONPATH="$src:$PYTHONPATH"

start=$(date +%s)
clear
rm -rf .benchmark/.data/.logs/

# First compute the number of runs

# Parameters values
THRESHOLD=(5 10 15 20 25 30 35 40 45 50) 

# Compute the number of runs
THRESHOLD_SIZE=${#THRESHOLD[@]}
total_runs=$((THRESHOLD_SIZE))

i=0
# Run all tests
for t in "${THRESHOLD[@]}"; do  # THRESHOLD
    # WITH CREDENTIALS
    i=$((i + 1))
    echo "Run: $i / $total_runs"
    ./scripts/run.sh -p 5 -m 50 -c 50 -t $t -a 50 -z 1 -v 0
    dir=.benchmark/.data/.logs/p5_m50_c50_t${t}_a50_z1
    mkdir -p $dir
    mv .logs/* -t $dir
done


echo "Gathering all CSV files..."
python .benchmark/gather_timing_data.py

end=$(date +%s)
echo "Benchmark finished in $((end - start)) sec"

