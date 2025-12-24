import socket
import struct
import csv
import time
import argparse
import os

# Checksum 
def calculate_checksum(data):
    return sum(data) % 65536

# Args 
parser = argparse.ArgumentParser()
parser.add_argument("--duration", type=int, default=60)
args = parser.parse_args()
DURATION = args.duration

# Header 
HEADER_FORMAT = "!HBBIBHB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

# Metrics 
total_bytes = 0
packets_received = 0
duplicate_packets = 0
sequence_gap_count = 0
total_cpu_time = 0.0
total_readings = 0

# CSV Setup 
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(PROJECT_ROOT, "sensor_data.csv")

file = open(csv_path, "w", newline="")
csv_writer = csv.writer(file)
csv_writer.writerow([
    "device_id",
    "seq",
    "timestamp",
    "arrival_time",
    "duplicate_flag",
    "gap_flag",
    "data_value"
])

# Socket 
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", 9999))
server_socket.settimeout(1.0)

print("Server is running on port 9999...", flush=True)

SERVER_START = time.time()
device_last_seq = {}
start_time = time.time()

# Main Loop 
while time.time() - start_time < DURATION:
    try:
        data, addr = server_socket.recvfrom(1024)
    except socket.timeout:
        continue

    cpu_start = time.perf_counter()
    arrival = time.time() - SERVER_START

    if len(data) < HEADER_SIZE:
        continue

    seq, device_id, msg_type, timestamp_ms, _, checksum, version = struct.unpack(
        HEADER_FORMAT, data[:HEADER_SIZE]
    )

    timestamp = timestamp_ms / 1000.0
    temp_data = data[:9] + b"\x00\x00" + data[11:]
    integrity = calculate_checksum(temp_data) == checksum

    duplicate_flag = 0
    gap_flag = 0

    if msg_type == MSG_INIT:
        device_last_seq[device_id] = seq
        server_socket.sendto(b"ACK_INIT", addr)
        time.sleep(0.05)
        server_socket.sendto(b"ACK_READY", addr)
        print(f"INIT from device {device_id}", flush=True)
        continue

    if msg_type == MSG_HEARTBEAT:
        print(f"Heartbeat from device {device_id}", flush=True)
        continue

    if msg_type == MSG_DATA:
        packets_received += 1
        total_bytes += len(data)

        if device_id in device_last_seq:
            last = device_last_seq[device_id]
            if seq == last:
                duplicate_flag = 1
                duplicate_packets += 1
            elif seq > last + 1:
                gap_flag = 1
                sequence_gap_count += (seq - last - 1)

        device_last_seq[device_id] = seq

        payload = data[HEADER_SIZE:].decode(errors="ignore")
        values = payload.split(",") if "," in payload else [payload]
        total_readings += len(values)

        for v in values:
            csv_writer.writerow([
                device_id, seq, timestamp,
                arrival, duplicate_flag,
                gap_flag, v
            ])

        print(
            f"Data | Packet {seq} | Readings {len(values)} | Checksum {'OK' if integrity else 'BAD'}",
            flush=True
        )

    total_cpu_time += time.perf_counter() - cpu_start

# Metrics Summary 
print("\n Experiment Metrics", flush=True)

if packets_received > 0 and total_readings > 0:
    bytes_per_report = total_bytes / total_readings
    duplicate_rate = duplicate_packets / packets_received
    cpu_ms_per_report = (total_cpu_time / total_readings) * 1000
else:
    bytes_per_report = 0
    duplicate_rate = 0
    cpu_ms_per_report = 0

print(f"Packets received: {packets_received}", flush=True)
print(f"Total readings received: {total_readings}", flush=True)
print(f"Bytes per report: {bytes_per_report:.2f}", flush=True)
print(f"Duplicate rate: {duplicate_rate:.4f}", flush=True)
print(f"Sequence gaps detected: {sequence_gap_count}", flush=True)
print(f"CPU ms per report: {cpu_ms_per_report:.4f}", flush=True)

# Write metrics to file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
metrics_path = os.path.join(PROJECT_ROOT, "metrics.txt")

with open(metrics_path, "w") as f:
    f.write(f"bytes_per_report {bytes_per_report}\n")
    f.write(f"packets_received {packets_received}\n")
    f.write(f"duplicate_rate {duplicate_rate}\n")
    f.write(f"sequence_gap_count {sequence_gap_count}\n")
    f.write(f"cpu_ms_per_report {cpu_ms_per_report}\n")

print(f"Metrics written to {metrics_path}", flush=True)

file.close()
server_socket.close()
