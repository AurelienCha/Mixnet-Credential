#!/bin/bash

# Becnhamark with for each run
# - 10 clients sending themselves 10 packets
# - 20 mixnodes
# - 50 authorities

src="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$src"
export PYTHONPATH="$src:$PYTHONPATH"
start=$(date +%s)
clear

make -C zk clean
./zk/circuit_gen.sh

##########################################################
###################### THRESHOLD #########################
##########################################################
# Compare the three protocols under varying parameters:  #
# - Setup (DKG + ZK)                                     #
# - Credential Issuance (with ZK)                        #
##########################################################

rm -rf benchmark/data/logs/

# Use your existing t, or accept it as the first script argument.
t=1
cpu_csv="benchmark/data/zk_cpu_times.csv"
rm -f "$cpu_csv"

# Write the header only for a new or empty file.
if [[ ! -s "$cpu_csv" ]]; then
    printf 'function,t,cpu_time_s\n' > "$cpu_csv"
fi

time_step() {
    local stage="$1"
    local param="$3"
    shift
    local TIMEFORMAT="$stage, $param, %3R"
    { time "$@" >/dev/null 2>&1; } 2>>"$cpu_csv"
}

THRESHOLD=(5 10 15 20 25 30 35 40 45 50) 
for t in "${THRESHOLD[@]}"; do  # THRESHOLD
    echo "Run -- THRESHOLD: $t"
    time_step tau ./zk/tau_ceremony.sh $t
    time_step crs ./zk/common_reference_string.sh $t
    cd "$src"
    ./scripts/run.sh -p 5 -m 20 -c 10 -t $t -a 50 -z 1 -v 0
    dir=benchmark/data/logs/t${t}_p5_z1
    mkdir -p $dir
    mv logs/* -t $dir
done

echo "Gathering CSV files..."
python benchmark/gather_timing_data.py threshold.csv


##########################################################
##################### PATH LENGTH ########################
##########################################################
# Compare the three protocols under varying parameters:  #
# - Sphinx from Danezis(baseline)                        #
# - DSphinx (vanilla)                                    #
# - DSphinx with basic Credentials                       #
##########################################################

cd "$src"
rm -rf benchmark/data/logs/
python3 benchmark/run_original_sphinx.py

# First compute the number of runs

PATH_LENGTH=(3 4 5 6 7)

# Run all tests
for p in "${PATH_LENGTH[@]}"; do  # PATH_LENGTH
    echo "Run -- PATH LENGTH: $p"
    # NO CREDENTIALS
    ./scripts/run.sh -p $p -m 10 -c 5 -t 5 -a 5 -z 0 -v 0
    dir=benchmark/data/logs/t5_p${p}_z0 
    mkdir -p $dir
    mv logs/* -t $dir

    # WITH CREDENTIALS
    ./scripts/run.sh -p $p -m 10 -c 5 -t 5 -a 5 -z 1 -v 0
    dir=benchmark/data/logs/t5_p${p}_z1 
    mkdir -p $dir
    mv logs/* -t $dir
done

echo "Gathering all CSV files..."
python benchmark/gather_timing_data.py pathLength.csv

###########
## PROOF ##
###########
echo "Simulate ZK proof..."
cd "zk"
./benchmark_proof.sh
cd "$src"

##############
## PLOTTING ##
##############

echo "Plotting the graphs..."
python benchmark/plot_setup.py
python benchmark/plot_issuance.py
python benchmark/plot_packet.py

######################
## END OF BENCHMARK ##
######################

make -C ./zk clean
end=$(date +%s)
echo "Benchmark finished in $((end - start)) sec"
echo "Raw data (csv file) saved in benchmark/data"
echo "Results (png file) saved in benchmark/results"
