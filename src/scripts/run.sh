#!/bin/bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT:$PYTHONPATH"

# ==========================================
# Cleanup PROCESSES
# ==========================================

cleanup() {
    pkill -f nodes.authority
    pkill -f nodes.mixnode
    pkill -f nodes.client
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

mkdir -p logs/auth
mkdir -p logs/mix
mkdir -p logs/client

rm -f .config.json

NETWORK_LOG="logs/network_capture.log"
touch $NETWORK_LOG
tshark -l -i lo -f "udp port 5000" > $NETWORK_LOG & >/dev/null 2>&1 &

# ==========================================
# GENERATE CONFIG
# ==========================================

python3 -m scripts.configuration --path_length $PATH_LENGTH --threshold $THRESHOLD --authorities $AUTHORITIES --mixnodes $MIXNODES --clients $CLIENTS || exit 1

# ==========================================
# START AUTHORITIES
# ==========================================

if [ $CREDENTIALS -eq 1 ]; then

    for ((i=1; i<=AUTHORITIES; i++))
    do
        python3 -m nodes.authority --id $i &
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

for ((i=1; i<=MIXNODES; i++))
do
    python3 -m nodes.mixnode --id $i &
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

for ((i=1; i<=CLIENTS; i++))
do
    python3 -m nodes.client --id $i &
done

# ==========================================
# Automatically stop the script if no UDP activity is detected
# ==========================================

sleep 2
while true; do
    last=$(stat -c %Y $NETWORK_LOG)
    now=$(date +%s)

    # Exit if no UDP activity for 5 seconds
    if (( now - last >= 3)); then
        mv .config.json logs/config.json
        killall tshark
        exit 0
    fi

    sleep 1
done