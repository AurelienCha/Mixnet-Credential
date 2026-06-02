start=$(date +%s)
clear
rm -rf .benchmark/.data/.logs/

# First compute the number of runs
total_runs=0
for ((p=3; p<=11; p+=2)); do # PATH LENGTH 
    for ((m=p; m<=50; m+=20)); do # NBR MIXNODES
        for ((c=1; c<=50; c+=20)); do # NBR CLIENT

            # NO CREDENTIALS
            total_runs=$((total_runs + 1))

            # WITH CREDENTIALS
            for ((t=3; t<=20; t+=5)); do # THRESHOLD
                for ((a=t; a<=50; a+=20)); do # NBR AUTHORITIES
                    total_runs=$((total_runs + 1))
                done
            done
        done
    done
done

# Run all the configs
i=0
for ((p=3; p<=11; p+=2)); do # PATH LENGTH 
    for ((m=p; m<=50; m+=20)); do # NBR MIXNODES
        for ((c=1; c<=50; c+=20)); do # NBR CLIENT

            # NO CREDENTIALS
            i=$((i + 1))
            echo "Run: $i / $total_runs"
            ./script.sh -p $p -m $m -c $c -z 0 -v 0
            dir=.benchmark/.data/.logs/p${p}_m${m}_c${c}_t0_a0_z0 #$(date +'%Y-%m-%d_%H:%M:%S')
            mkdir -p $dir
            mv .logs/* -t $dir

            for ((t=3; t<=20; t+=5)); do # THRESHOLD
                for ((a=t; a<=50; a+=20)); do # NBR AUTHORITIES

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
