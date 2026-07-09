start=$(date +%s)
clear
rm -rf .benchmark/.data/.logs/

# First compute the number of runs

# Parameters values
PATH_LENGTH=(3 4 5 6 7)
THRESHOLD=(3 6 12) 
BIG_VALUES=(15 30 60) # for NBR_MIXNODES, NBR_CLIENTS & NBR_AUTHORITIES

# Compute the number of runs
PATH_SIZE=${#PATH_LENGTH[@]}
THRESHOLD_SIZE=${#THRESHOLD[@]}
SIZE_BIG=${#BIG_VALUES[@]}
total_runs=$((THRESHOLD_SIZE * PATH_SIZE * SIZE_BIG**3 + PATH_SIZE * SIZE_BIG**2))

i=0
# Run all tests
for p in "${PATH_LENGTH[@]}"; do  # PATH_LENGTH
    for m in "${BIG_VALUES[@]}"; do  # NBR_MIXNODES
        for c in "${BIG_VALUES[@]}"; do  # NBR_CLIENT

            # NO CREDENTIALS
            i=$((i + 1))
            echo "Run: $i / $total_runs"
            ./script.sh -p $p -m $m -c $c -z 0 -v 0
            dir=.benchmark/.data/.logs/p${p}_m${m}_c${c}_t0_a0_z0 #$(date +'%Y-%m-%d_%H:%M:%S')
            mkdir -p $dir
            mv .logs/* -t $dir

            # WITH CREDENTIALS
            for t in "${THRESHOLD[@]}"; do  # THRESHOLD
                for a in "${BIG_VALUES[@]}"; do  # NBR_AUTHORITIES

                    # WITH CREDENTIALS
                    i=$((i + 1))
                    echo "Run: $i / $total_runs"
                    ./script.sh -p $p -m $m -c $c -t $t -a $a -z 1 -v 0
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
