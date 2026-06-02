#!/bin/bash

PATH_LENGTH=7
THRESHOLD=10
AUTHORITIES=50
MIXNODES=50
CLIENTS=20

if [ "$1" = "--without-credential" ]; then
    CREDENTIALS=0
else
    CREDENTIALS=1
fi
export CREDENTIALS

clear 

# ==========================================
# KILL OLD PROCESSES
# ==========================================

pkill -f Authority/node.py
pkill -f Mixnode/main.py
pkill -f Client/main.py

# ==========================================
# CLEAN LOGS and config
# ==========================================

rm -rf .logs

mkdir -p .logs/auth
mkdir -p .logs/mix
mkdir -p .logs/client

rm -f .config.json
rm -f .public.json

# ==========================================
# GENERATE CONFIG
# ==========================================

python3 config.py --path_length $PATH_LENGTH --threshold $THRESHOLD --authorities $AUTHORITIES --mixnodes $MIXNODES || exit 1

# ==========================================
# START AUTHORITIES
# ==========================================

if [ $CREDENTIALS -eq 1 ]; then
    echo "AUTHORITIES SETUP ..."
    for ((i=1; i<=AUTHORITIES; i++))
    do
        python3 Authority/node.py --id $i &
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

echo "MIXNODES SETUP ..."
for ((i=1; i<=MIXNODES; i++))
do
    python3 Mixnode/main.py --id $i &
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


echo "RUNNING CLIENTS ..."
for ((i=1; i<=CLIENTS; i++))
do
    python3 Client/main.py --id $i &
done

# ==========================================
# Automatically stop the script if no UDP activity is detected
# ==========================================

tshark -l -i lo -f "udp port 5000" 2>/dev/null |
sleep 0.1
while read -r line; do
    touch /tmp/udp_activity
done &

while true; do
    last=$(stat -c %Y /tmp/udp_activity)
    now=$(date +%s)

    if (( now - last >= 1 )); then
        echo "No activity for 1 seconds - exiting..."

        pkill -f Authority/node.py
        pkill -f Mixnode/main.py
        pkill -f Client/main.py
        rm -f /tmp/udp_activity

        exit 0
    fi
    sleep 1
done