#!/bin/bash

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

PATH_LENGTH=5
THRESHOLD=10
AUTHORITIES=20
MIXNODES=20
CLIENTS=3


CREDENTIALS=1
VERBOSE=1

# Override defaults if provided
while getopts "p:t:a:m:c:z:v:" opt; do
  case $opt in
    p) PATH_LENGTH="$OPTARG" ;;
    t) THRESHOLD="$OPTARG" ;;
    a) AUTHORITIES="$OPTARG" ;;
    m) MIXNODES="$OPTARG" ;;
    c) CLIENTS="$OPTARG" ;;
    z) CREDENTIALS="$OPTARG" ;;
    v) VERBOSE="$OPTARG" ;;
    *) echo "Invalid option"; exit 1 ;;
  esac
done

export CREDENTIALS
export VERBOSE

# ==========================================
# CLEAN LOGS and config
# ==========================================

rm -rf .logs

mkdir -p .logs/auth
mkdir -p .logs/mix
mkdir -p .logs/client

rm -f .config.json
rm -f .public.json

# NETWORK LOGS
NETWORK_LOG=".logs/network_capture.log"
touch $NETWORK_LOG
tshark -l -i lo -f "udp port 5000" > $NETWORK_LOG &
TSHARK_PID=$!

# ==========================================
# GENERATE CONFIG
# ==========================================

python3 -m configuration --path_length $PATH_LENGTH --threshold $THRESHOLD --authorities $AUTHORITIES --mixnodes $MIXNODES --clients $CLIENTS || exit 1

# ==========================================
# START AUTHORITIES
# ==========================================

if [ $CREDENTIALS -eq 1 ]; then
    # echo "AUTHORITIES SETUP ..."
    for ((i=1; i<=AUTHORITIES; i++))
    do
        python3 -m Authority.node --id $i &
    done
else
    cp .config.json .public.json
fi

# ==========================================
# WAIT FOR SETUP COMPLETION
# ==========================================

while [ ! -f .public.json ]
do
    sleep 0.1
done

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
    COUNT=$(jq '.mixnodes | length' .public.json)

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
        exit 0
    fi

    sleep 0.1
done