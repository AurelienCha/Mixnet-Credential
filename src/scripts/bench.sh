#!/bin/bash

src="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$src"
export PYTHONPATH="$src:$PYTHONPATH"

start=$(date +%s)
clear
rm -rf .benchmark/.data/.logs/

# First compute the number of runs

# Parameters values
PATH_LENGTH=(3 4 5 6 7 9 11 13)
THRESHOLD=(5 10 20) 
BIG_VALUES=(25 50) # for NBR_MIXNODES & NBR_AUTHORITIES

# Compute the number of runs
PATH_SIZE=${#PATH_LENGTH[@]}
THRESHOLD_SIZE=${#THRESHOLD[@]}
SIZE_BIG=${#BIG_VALUES[@]}
total_runs=$((THRESHOLD_SIZE * PATH_SIZE * SIZE_BIG**2 + PATH_SIZE * SIZE_BIG))

i=0
# Run all tests
for p in "${PATH_LENGTH[@]}"; do  # PATH_LENGTH
    for m in "${BIG_VALUES[@]}"; do  # NBR_MIXNODES
        for c in "${BIG_VALUES[@]}"; do  # NBR_CLIENTS

            # NO CREDENTIALS
            i=$((i + 1))
            echo "Run: $i / $total_runs"
            ./scripts/run.sh -p $p -m $m -c $c -z 0 -v 0
            dir=.benchmark/.data/.logs/p${p}_m${m}_c${c}_t0_a0_z0 #$(date +'%Y-%m-%d_%H:%M:%S')
            mkdir -p $dir
            mv .logs/* -t $dir

            # WITH CREDENTIALS
            for t in "${THRESHOLD[@]}"; do  # THRESHOLD
                for a in "${BIG_VALUES[@]}"; do  # NBR_AUTHORITIES

                    # WITH CREDENTIALS
                    i=$((i + 1))
                    echo "Run: $i / $total_runs"
                    ./scripts/run.sh -p $p -m $m -c $c -t $t -a $a -z 1 -v 0
                    dir=.benchmark/.data/.logs/p${p}_m${m}_c${c}_t${t}_a${a}_z1 #$(date +'%Y-%m-%d_%H:%M:%S')
                    mkdir -p $dir
                    mv .logs/* -t $dir
                done
            done
        done
    done
done


echo "Gathering all CSV files..."
python .benchmark/gather_timing_data.py

end=$(date +%s)
echo "Benchmark finished in $((end - start)) sec"

