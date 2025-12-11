import socket
import struct
import csv
import time
import argparse
import os

# ------------------ Checksum ------------------
def calculate_checksum(data):
    return sum(data) % 65536


# ------------------ Argument Parsing ------------------
parser = argparse.ArgumentParser()
parser.add_argument("--duration", type=int, default=60)
args = parser.parse_args()

DURATION = args.duration

# ------------------ Packet Header ------------------
HEADER_FORMAT = "!HBBIBHB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

# ------------------ Metrics ------------------
total_bytes = 0
packets_received = 0
duplicate_count = 0
sequence_gap_count = 0
total_cpu_time = 0

# ------------------ CSV Setup (PROJECT ROOT) ------------------
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

# ------------------ Socket Setup ------------------
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", 9999))
server_socket.settimeout(1.0)

print("Server is running and listening on port 9999...", flush=True)

# ------------------ Device State ------------------
device_last_seq = {}

# ------------------ Main Loop ------------------
start_time = time.time()

while time.time() - start_time < DURATION:
    try:
        data, addr = server_socket.recvfrom(1024)
    except socket.timeout:
        continue

    arrival_time = time.time()
    cpu_start = time.perf_counter()

    packets_received += 1
    total_bytes += len(data)

    if len(data) < HEADER_SIZE:
        continue

    seq, device_id, msg_type, timestamp, _, checksum, version = struct.unpack(
        HEADER_FORMAT, data[:HEADER_SIZE]
    )

    data_wo_checksum = data[:9] + b"\x00\x00" + data[11:]
    integrity = "Valid" if calculate_checksum(data_wo_checksum) == checksum else "Corrupted"

    duplicate_flag = 0
    gap_flag = 0

    if msg_type == MSG_INIT:
        print(f"New device connected. ID={device_id}, Version={version}",flush=True)
        device_last_seq[device_id] = seq

        # Send ACK for INIT
        server_socket.sendto(b"ACK_INIT", addr)

    elif msg_type == MSG_HEARTBEAT:
        print(f"Heartbeat received from device {device_id}", flush=True)

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

        payload = data[HEADER_SIZE:].decode(errors="ignore")
        values = payload.split(",") if "," in payload else [payload]

        for value in values:
            csv_writer.writerow([
                device_id, seq, timestamp,
                arrival_time, duplicate_flag,
                gap_flag, value
            ])
        file.flush()

        if len(values) > 1:
            print(f"Batch of {len(values)} readings | Packet {seq} | Checksum {integrity}")
        else:
            print(f"Data received | Packet {seq} | Checksum {integrity}")

    total_cpu_time += time.perf_counter() - cpu_start

# ------------------ Summary ------------------
print("\nSession Summary")
print("-" * 30)
print(f"Total packets received: {packets_received}")
print(f"Average packet size: {round(total_bytes / packets_received, 2)} bytes")
print(f"Duplicate packet rate: {(duplicate_count / packets_received) * 100:.2f}%")
print(f"Sequence gaps detected: {sequence_gap_count}")
print(f"Average CPU time per packet: {(total_cpu_time / packets_received) * 1000:.4f} ms")
print("Server session ended.")

file.close()
server_socket.close()
