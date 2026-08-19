#!/bin/bash

src="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$src"
export PYTHONPATH="$src:$PYTHONPATH"
start=$(date +%s)

################ SMALL BENCHMARK #################
## Varying Threshold on DSphinx with Credential ##
##################################################

clear
rm -rf benchmark/data/logs/

THRESHOLD=(5 10 15 20 25 30 35 40 45 50) 
total_runs=${#THRESHOLD[@]}
i=0
for t in "${THRESHOLD[@]}"; do  # THRESHOLD
    i=$((i + 1))
    echo "Run: $i / $total_runs"
    ./scripts/run.sh -p 5 -m 50 -c 50 -t $t -a 50 -z 1 -v 0
    dir=benchmark/data/logs/p5_m50_c50_t${t}_a50_z1 
    mkdir -p $dir
    mv logs/* -t $dir
done

echo "Gathering CSV files..."
python benchmark/gather_timing_data.py setup_runtime.csv

##########################################################
##################### MAIN BENCHMARK #####################
##########################################################
# Compare the three protocols under varying parameters:  #
# - Sphinx from Danezis(baseline)                        #
# - DSphinx (vanilla)                                    #
# - DSphinx with basic Credentials                       #
##########################################################

clear
rm -rf benchmark/data/logs/
python benchmark/run_original_sphinx.py

# First compute the number of runs

# Parameters values
PATH_LENGTH=(3 4 5 6 7 9 11 13)
THRESHOLD=(5 10 20) 
ENTITIES=(25 50) # for NBR_MIXNODES & NBR_AUTHORITIES

# Compute the number of runs
PATH_SIZE=${#PATH_LENGTH[@]}
THRESHOLD_SIZE=${#THRESHOLD[@]}
SIZE_ENTITIES=${#ENTITIES[@]}
total_runs=$((PATH_SIZE * SIZE_ENTITIES**2 * ( 1 + THRESHOLD * SIZE_ENTITIES ) ))

i=0
# Run all tests
for p in "${PATH_LENGTH[@]}"; do  # PATH_LENGTH
    for m in "${ENTITIES[@]}"; do  # NBR_MIXNODES
        for c in "${ENTITIES[@]}"; do  # NBR_CLIENTS

            # NO CREDENTIALS
            i=$((i + 1))
            echo "Run: $i / $total_runs"
            ./scripts/run.sh -p $p -m $m -c $c -z 0 -v 0
            dir=benchmark/data/logs/p${p}_m${m}_c${c}_t0_a0_z0 #$(date +'%Y-%m-%d_%H:%M:%S')
            mkdir -p $dir
            mv logs/* -t $dir

            # WITH CREDENTIALS
            for t in "${THRESHOLD[@]}"; do  # THRESHOLD
                for a in "${ENTITIES[@]}"; do  # NBR_AUTHORITIES

                    # WITH CREDENTIALS
                    i=$((i + 1))
                    echo "Run: $i / $total_runs"
                    ./scripts/run.sh -p $p -m $m -c $c -t $t -a $a -z 1 -v 0
                    dir=benchmark/data/logs/p${p}_m${m}_c${c}_t${t}_a${a}_z1 #$(date +'%Y-%m-%d_%H:%M:%S')
                    mkdir -p $dir
                    mv logs/* -t $dir
                done
            done
        done
    done
done


echo "Gathering all CSV files..."
python benchmark/gather_timing_data.py timing.csv

##############
## PLOTTING ##
##############

echo "Plotting the graphs..."
python benchmark/computation_time.py
python benchmark/computation_overhead.py
python benchmark/plot_scaling.py
python benchmark/plot_setup.py

######################
## END OF BENCHMARK ##
######################

end=$(date +%s)
echo "Benchmark finished in $((end - start)) sec\n"
echo "Raw data (csv file) saved in benchmark/data"
echo "Results (png file) saved in benchmark/results"

