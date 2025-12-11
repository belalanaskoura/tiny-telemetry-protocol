#!/bin/bash

#########################################
# AUTO-DETECT PROJECT ROOT
#########################################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

TESTRUNNER="$PROJECT_ROOT/Automation/TestRunner.py"
CSV_FILE="$PROJECT_ROOT/sensor_data.csv"


#########################################
# LOOPBACK CONFIGURATION
#########################################

# Use loopback interface because WSL eth0 doesn't support netem
IFACE="lo"
SERVER_IP="127.0.0.1"

DURATION=60
BATCH=0
CLIENTS=1

TEST_NAME="$1"

if [ -z "$TEST_NAME" ]; then
    echo "Usage: ./run_test.sh <test_name>"
    echo "Example tests: loss5, delay100, normal"
    exit 1
fi

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RESULT_DIR="$PROJECT_ROOT/tests/results/${TEST_NAME}_${TIMESTAMP}"
mkdir -p "$RESULT_DIR"

echo "[INFO] Results will be stored in $RESULT_DIR"
echo ""


#########################################
# APPLY NETEM (LOOPBACK)
#########################################

echo "[INFO] Applying netem settings to loopback..."
sudo tc qdisc del dev $IFACE root 2>/dev/null

case "$TEST_NAME" in
    loss5)
        echo "[INFO] Applying 5% packet loss on lo"
        sudo tc qdisc add dev $IFACE root netem loss 5%
        ;;
    delay100)
        echo "[INFO] Applying 100ms delay ±10ms jitter on lo"
        sudo tc qdisc add dev $IFACE root netem delay 100ms 10ms
        ;;
    normal)
        echo "[INFO] Running without impairment"
        ;;
    *)
        echo "[WARN] Unknown test '$TEST_NAME'. Running without netem."
        ;;
esac

tc qdisc show dev $IFACE > "$RESULT_DIR/netem_settings.txt"


#########################################
# PACKET CAPTURE (tcpdump on lo)
#########################################

echo "[INFO] Starting tcpdump on loopback..."
sudo tcpdump -i $IFACE -w "$RESULT_DIR/trace.pcap" > /dev/null 2>&1 &
TCPDUMP_PID=$!


#########################################
# RUN TESTRUNNER
#########################################

if [ ! -f "$TESTRUNNER" ]; then
    echo "[ERROR] Could not find TestRunner at $TESTRUNNER"
    exit 1
fi

echo "[INFO] Running TestRunner (client + server on 127.0.0.1)..."
python3 "$TESTRUNNER" "$SERVER_IP" "$DURATION" "$BATCH" "$CLIENTS" \
    | tee "$RESULT_DIR/test_output.log"


#########################################
# SAVE CSV OUTPUT
#########################################

if [ -f "$CSV_FILE" ]; then
    OUT_CSV="$RESULT_DIR/sensor_${TEST_NAME}_${TIMESTAMP}.csv"
    echo "[INFO] Saving CSV to: $OUT_CSV"
    cp "$CSV_FILE" "$OUT_CSV"
else
    echo "[WARN] No sensor_data.csv found."
fi

#########################################
# ANALYZE RESULTS (LOSS, GAPS, ETC.)
#########################################

if [ -f "$OUT_CSV" ]; then
    echo "[INFO] Running loss/gap analysis..."
    python3 "$PROJECT_ROOT/analyze_loss.py" "$OUT_CSV" \
        | tee "$RESULT_DIR/analysis_${TEST_NAME}_${TIMESTAMP}.txt"
else
    echo "[WARN] Cannot analyze – CSV missing."
fi


#########################################
# CLEANUP
#########################################

echo "[INFO] Stopping tcpdump..."
sudo kill $TCPDUMP_PID 2>/dev/null

echo "[INFO] Removing netem..."
sudo tc qdisc del dev $IFACE root 2>/dev/null

echo ""
echo "[DONE] Test '$TEST_NAME' complete."
echo "Results saved in: $RESULT_DIR"
