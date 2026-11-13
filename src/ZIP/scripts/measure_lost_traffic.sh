#!/bin/bash
cd "$(dirname "$0")/.."
FILE="logs/network_capture.log"

# Pattern for Sending Packets == Client -> Mixnode == 127.0.100.x -> 127.0.10.y
SEND=$(grep -Eo '127\.0\.100\..* → 127\.0\.10\..*' "$FILE" | wc -l)

# Pattern for Receiving Packets == Mixnode -> Client == 127.0.10.x -> 127.0.100.y
RECEIVED=$(grep -Eo '127\.0\.10\..* → 127\.0\.100\..*' "$FILE" | wc -l)

# SUCCESS RATE
SUCCESS_RATE=$(echo "scale=2; $RECEIVED / $SEND * 100" | bc)

if [ "$1" == "--value" ]; then
    # Return only the value for other scripts
    echo "$SUCCESS_RATE"
else
    echo "Nbr send packets: $SEND"
    echo "Nbr received packets: $RECEIVED"
    echo "Traffic success rate: ${SUCCESS_RATE}%"
fi
