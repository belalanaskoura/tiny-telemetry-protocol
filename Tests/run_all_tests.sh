#!/bin/bash

TESTS=("normal" "loss5" "delay100")

echo "Running all loopback tests..."
echo ""

for t in "${TESTS[@]}"; do
    echo "------------------------------------------"
    echo "[START] Running test: $t"
    echo "------------------------------------------"
    ./run_test.sh "$t"
    echo ""
done

echo "[DONE] All loopback tests completed."
