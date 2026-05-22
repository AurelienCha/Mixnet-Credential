#!/bin/bash

THRESHOLD=7
AUTHORITIES=50
MIXNODES=30
CLIENTS=10

clear 

# ==========================================
# KILL OLD PROCESSES
# ==========================================

pkill -f Authority/node.py
pkill -f Mixnode/node.py
pkill -f Client/node.py

# ==========================================
# CLEAN LOGS and config
# ==========================================

rm -rf .logs

mkdir -p .logs/auth
mkdir -p .logs/mix
mkdir -p .logs/client

rm config.json
rm public.json

# ==========================================
# GENERATE CONFIG
# ==========================================

python3 config.py --threshold $THRESHOLD --authorities $AUTHORITIES || exit 1

# ==========================================
# START AUTHORITIES
# ==========================================

for ((i=1; i<=AUTHORITIES; i++))
do
    python3 Authority/node.py --id $i &
done

# ==========================================
# WAIT FOR SETUP COMPLETION
# ==========================================

echo "Waiting for authorities setup..."
while [ ! -f public.json ]
do
    sleep 0.1
done
echo "Authorities setup complete"

# ==========================================
# START MIXNODES
# ==========================================

for ((i=1; i<=MIXNODES; i++))
do
    python3 Mixnode/node.py --id $i &
done

# ==========================================
# WAIT ALL MIXNODES UPDATE public.json
# ==========================================

while true
do
    COUNT=$(jq '.mixnodes | length' public.json)

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
    python3 Client/node.py --id $i &
done

# ==========================================
# WAIT FOR EVERYTHING
# ==========================================

# wait