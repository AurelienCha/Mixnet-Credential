#!/bin/bash

# ==========================================
# CLEAN LOGS
# ==========================================

rm -rf logs
mkdir logs
mkdir logs/auth

# ==========================================
# GENERATE CONFIG
# ==========================================

python3 config.py || exit 1

# ==========================================
# LAUNCH NODES
# ==========================================

for i in {0..4}
do
    python3 Authority/node.py --id $i &
done

# Wait for all background processes
wait