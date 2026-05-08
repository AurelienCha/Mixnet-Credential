#!/bin/bash

SESSION="nodes"

tmux kill-session -t $SESSION 2>/dev/null

tmux new-session -d -s $SESSION "python3 Authority/node.py --id 0; read;" # echo 'CRASHED'; read"

for i in {1..4}
do
    tmux split-window -h -t $SESSION "python3 Authority/node.py --id $i;" # echo 'CRASHED'; read"
done

tmux select-layout -t $SESSION even-horizontal

tmux attach -t $SESSION