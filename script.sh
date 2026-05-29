#!/bin/bash

PATH_LENGTH=3
THRESHOLD=3
AUTHORITIES=3
MIXNODES=3
CLIENTS=1

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

rm -f config.json
rm -f public.json

# ==========================================
# GENERATE CONFIG
# ==========================================

python3 config.py --threshold $THRESHOLD --authorities $AUTHORITIES --path_length $PATH_LENGTH || exit 1

# ==========================================
# START AUTHORITIES
# ==========================================

if [ $CREDENTIALS -eq 1 ]; then
    for ((i=1; i<=AUTHORITIES; i++))
    do
        python3 Authority/node.py --id $i &
    done
else
    cp config.json public.json
fi

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
    python3 Mixnode/main.py --id $i &
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
    python3 Client/main.py --id $i &
done

# ==========================================
# WAIT FOR EVERYTHING
# ==========================================

# wait