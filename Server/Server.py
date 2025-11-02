import socket
import struct
import csv
import time
import argparse


# Gets duration to run from Baseline.py
parser = argparse.ArgumentParser()
parser.add_argument("--duration", type=int, default=60) # If not specified
args = parser.parse_args()


# Header format:
# SeqNum (H), DeviceID (B), MsgType (B), Timestamp (I), BatchFlag (B), Checksum (H), Version (B)
HEADER_FORMAT = "!HBBIBHB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Message types
MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3


DURATION = args.duration

# Metrics to collect
total_bytes = 0
packets_recieved = 0
duplicate_count = 0
sequence_gap_count = 0
total_cpu_time = 0


# Create UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", 9999))
print("Server waiting for readings on port 9999...", flush = True)

# Track device info
device_last_seq = {}

# Prepare CSV file
file = open("sensor_data.csv", "w", newline="")
csv_writer = csv.writer(file)
csv_writer.writerow(["device_id", "seq", "timestamp", "arrival_time", "duplicate_flag", "gap_flag", "data_value"])

start_time = time.time()

while time.time() - start_time < DURATION:
    data, clientAddress = server_socket.recvfrom(1024)
    arrival_time = time.time()
    cpu_start_time = time.perf_counter()

    packets_recieved += 1
    total_bytes += len(data)

    # Parse header
    seq, device_id, msg_type, timestamp, batch_flag, checksum, version = struct.unpack(
    HEADER_FORMAT, data[:HEADER_SIZE]
)

    if len(data) > HEADER_SIZE:
        payload_bytes = data[HEADER_SIZE:]  # Extracts all bytes after the header
        payload = payload_bytes.decode("utf-8", errors="ignore")

        duplicate_flag = 0
        gap_flag = 0

        if msg_type == MSG_INIT:
            print(f"[INIT] Device {device_id} (v{version}) connected from {clientAddress}", flush= True)
            device_last_seq[device_id] = seq  # Saves device's initial sequence number for later comparisons

        elif msg_type == MSG_DATA:
            if device_id in device_last_seq:
                last_seq = device_last_seq[device_id]
                if seq == last_seq:
                    duplicate_flag = 1
                    duplicate_count += 1
                elif seq > last_seq + 1:
                    gap_flag = 1
                    sequence_gap_count += 1

            device_last_seq[device_id] = seq

            

            csv_writer.writerow([device_id, seq, timestamp, arrival_time, duplicate_flag, gap_flag, payload])
            file.flush()  # Ensures buffer is emptied and everything is printed in csv

            print(f"[DATA] Dev={device_id} Seq={seq} Value={payload} "f"Dup={duplicate_flag} Gap={gap_flag} Batch={batch_flag}", flush= True)

    cpu_end_time = time.perf_counter()
    total_cpu_time += (cpu_end_time - cpu_start_time)


bytes_per_report = round(total_bytes / packets_recieved, 2)
duplicate_rate = (duplicate_count / packets_recieved) * 100
cpu_ms_per_report = (total_cpu_time / packets_recieved) * 1000 #milliseconds

print("Metrics Summary")
print(F"Average bytes per report: {bytes_per_report} " )
print(F"Packets recieved: {packets_recieved}")
print(F"Duplicate rate: {duplicate_rate}")
print(F"Sequence Gap counts: {sequence_gap_count} ")
print(F"Cpu time per report in ms: {cpu_ms_per_report:.6f}")