#!/bin/bash
cd "$(dirname "$0")"

# ==========================================
# Cleanup PROCESSES
# ==========================================

cleanup() {
    pkill -f Authority.node
    pkill -f Mixnode.main
    pkill -f Client.main
}

trap cleanup EXIT INT TERM

# ==========================================
# Default Parameters
# ==========================================

PATH_LENGTH=3
THRESHOLD=3
AUTHORITIES=3
MIXNODES=3
CLIENTS=2

CREDENTIALS=1
VERBOSE=1

export CREDENTIALS
export VERBOSE

# ==========================================
# CLEAN LOGS and config
# ==========================================

rm -rf .logs

mkdir -p .logs/auth
mkdir -p .logs/mix
mkdir -p .logs/client

# NETWORK LOGS
NETWORK_LOG=".logs/network_capture.log"
touch $NETWORK_LOG
tshark -l -i lo -f "udp port 5000" > $NETWORK_LOG >/dev/null 2>&1 &
TSHARK_PID=$!

# ==========================================
# GENERATE CONFIG
# ==========================================

python3 -m scripts.configuration --path_length $PATH_LENGTH --threshold $THRESHOLD --authorities $AUTHORITIES --mixnodes $MIXNODES --clients $CLIENTS || exit 1

# ==========================================
# START AUTHORITIES
# ==========================================

if [ $CREDENTIALS -eq 1 ]; then
    # echo "AUTHORITIES SETUP ..."
    for ((i=1; i<=AUTHORITIES; i++))
    do
        python3 -m Authority.node --id $i &
    done

    # ==========================================
    # WAIT FOR SETUP COMPLETION
    # ==========================================

    while ! jq -e '.authority_PK' .config.json >/dev/null; do
        sleep 0.1
    done
fi



# ==========================================
# START MIXNODES
# ==========================================

# echo "MIXNODES SETUP ..."
for ((i=1; i<=MIXNODES; i++))
do
    python3 -m Mixnode.main --id $i &
done

# ==========================================
# WAIT ALL MIXNODES UPDATE public.json
# ==========================================

while true
do
    COUNT=$(jq '.mixnodes | length' .config.json)

    if [ "$COUNT" -ge "$MIXNODES" ]; then
        break
    fi
    sleep 0.1
done

# ==========================================
# START Client
# ==========================================

# echo "RUNNING CLIENTS ..."
for ((i=1; i<=CLIENTS; i++))
do
    python3 -m Client.main --id $i &
done

# ==========================================
# Automatically stop the script if no UDP activity is detected
# ==========================================


sleep 2
while true; do
    last=$(stat -c %Y $NETWORK_LOG)
    now=$(date +%s)

    # Exit if no UDP activity for 1 seconds
    if (( now - last >= 1)); then
        kill $TSHARK_PID
        mv .config.json .logs/config.json
        exit 0
    fi

    sleep 0.1
done