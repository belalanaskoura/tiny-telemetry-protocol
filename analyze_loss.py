import pandas as pd
import sys

# ---------------------------
# 1. LOAD CSV
# ---------------------------
if len(sys.argv) < 2:
    print("Usage: python3 analyze_loss.py <csv_file>")
    sys.exit(1)

csv_file = sys.argv[1]
df = pd.read_csv(csv_file)

# Only DATA packets matter for loss analysis
data_df = df[df["duplicate_flag"].isin([0,1])]

# ---------------------------
# 2. BASIC STATS
# ---------------------------
received_packets = len(data_df)
unique_sequences = data_df["seq"].nunique()

first_seq = data_df["seq"].min()
last_seq  = data_df["seq"].max()

expected_packets = (last_seq - first_seq) + 1
lost_packets = expected_packets - unique_sequences

loss_percentage = (lost_packets / expected_packets) * 100

print("\n================ LOSS ANALYSIS ================")
print(f"CSV File: {csv_file}")
print("-----------------------------------------------")
print(f"First sequence number: {first_seq}")
print(f"Last sequence number : {last_seq}")
print(f"Expected packets     : {expected_packets}")
print(f"Received packets     : {unique_sequences}")
print(f"Total lost packets   : {lost_packets}")
print(f"Loss % (calculated)  : {loss_percentage:.2f}%")
print("===============================================\n")

# ---------------------------
# 3. GAP ANALYSIS
# ---------------------------
df_sorted = data_df.sort_values("seq")
seq_list = df_sorted["seq"].tolist()

gaps = []
for i in range(1, len(seq_list)):
    prev_seq = seq_list[i-1]
    curr_seq = seq_list[i]
    diff = curr_seq - prev_seq

    if diff > 1:
        gaps.append((prev_seq, curr_seq, diff - 1))

# Print detailed gap info
print("Detected Sequence Gaps:")
if not gaps:
    print("  No gaps detected.")
else:
    for g in gaps:
        print(f"  Gap after seq {g[0]} → next received {g[1]} | Lost {g[2]} packets")

print("\n===============================================\n")
