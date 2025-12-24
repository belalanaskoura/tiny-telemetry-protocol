import pandas as pd
import sys
import numpy as np

# HELPERS
def format_ms(seconds):
    return round(seconds * 1000, 3)


# 1. LOAD CSV
if len(sys.argv) < 2:
    print("Usage: python3 analyze_results.py <csv_file>")
    sys.exit(1)

csv_file = sys.argv[1]
df = pd.read_csv(csv_file)

# Filter only DATA packets (heartbeats don't matter for delay/loss)
df = df[df["duplicate_flag"].isin([0, 1])]

if df.empty:
    print("CSV contains no data packets.")
    sys.exit(0)

# 2. BASIC SEQUENCE STATS
received = df["seq"].nunique()
first_seq = df["seq"].min()
last_seq = df["seq"].max()
expected = (last_seq - first_seq) + 1
lost = expected - received
loss_percent = (lost / expected) * 100

print("\n PACKET STATS ")
print(f"CSV File: {csv_file}")
print(f"First seq          : {first_seq}")
print(f"Last seq           : {last_seq}")
print(f"Expected packets   : {expected}")
print(f"Received packets   : {received}")
print(f"Total lost packets : {lost}")
print(f"Loss % (calculated): {loss_percent:.2f}%")

# GAP ANALYSIS (LOSS TEST)
df_sorted = df.sort_values("seq")
seq_list = df_sorted["seq"].tolist()

gaps = []
for i in range(1, len(seq_list)):
    prev = seq_list[i - 1]
    curr = seq_list[i]
    diff = curr - prev
    if diff > 1:
        gaps.append((prev, curr, diff - 1))

print(" GAP ANALYSIS (LOSS TEST) ")
if not gaps:
    print("No gaps detected.")
else:
    for g in gaps:
        print(f"Gap after seq {g[0]} → next {g[1]} | Lost {g[2]} packets")

# DELAY & JITTER ANALYSIS
if "arrival_time" in df.columns and "timestamp" in df.columns:
    df["arrival_time"] = pd.to_numeric(df["arrival_time"], errors="coerce")
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")

    # Raw delay = arrival time - packet timestamp
    df["delay"] = df["arrival_time"] - df["timestamp"]

    avg_delay = df["delay"].mean()
    min_delay = df["delay"].min()
    max_delay = df["delay"].max()
    std_delay = df["delay"].std()

    # Inter-arrival time (difference between adjacent packets)
    df = df.sort_values("arrival_time")
    df["inter_arrival"] = df["arrival_time"].diff()

    avg_inter = df["inter_arrival"].mean()
    std_inter = df["inter_arrival"].std()

    # Detect out-of-order packets (should NOT happen unless delay > variation)
    df_sorted_by_arrival = df.sort_values("arrival_time")
    arrival_order = df_sorted_by_arrival["seq"].tolist()
    packet_reordering = arrival_order != sorted(arrival_order)

    print(" DELAY ANALYSIS ")
    print(f"Avg network delay     : {format_ms(avg_delay)} ms")
    print(f"Min delay             : {format_ms(min_delay)} ms")
    print(f"Max delay             : {format_ms(max_delay)} ms")
    print(f"Delay jitter (stddev) : {format_ms(std_delay)} ms")
    print("")
    print(f"Avg inter-arrival     : {format_ms(avg_inter)} ms")
    print(f"Inter-arrival jitter  : {format_ms(std_inter)} ms")
    print("")
    print(f"Packet reordering?    : {'YES' if packet_reordering else 'NO'}")
else:
    print("Arrival times not present — cannot compute delay analysis.")
