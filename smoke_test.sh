#!/bin/bash

run_test() {

    local name="$1"
    shift

    echo -n "$name ... "

    output=$("$@" 2>&1)
    status=$?

    if [ $status -ne 0 ]; then
        echo -e "\033[91m✗\033[0m"
        echo "$output" | tail -n 1
        return 1
    fi

    RATE=$(./scripts/measure_lost_traffic.sh --value)
    RATE=$(printf "%.0f" "$RATE") # cast to int
    
    if [ "$RATE" -lt 80 ]; then
        echo -e "\033[91m[✗]\033[0m (${RATE} %)"
    else
        echo -e "\033[92m[✓]\033[0m (${RATE} %)"
    fi
}

start=$(date +%s)

run_test "Testing without credential" \
    ./scripts/run.sh -p 3 -m 3 -c 2 -t 3 -a 3 -z 0 -v 0

run_test "Testing with credential" \
    ./scripts/run.sh -p 3 -m 3 -c 2 -t 3 -a 3 -z 1 -v 0

end=$(date +%s)
echo "Checks finished in $((end - start)) sec"

