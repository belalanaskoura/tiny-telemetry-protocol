import socket
import struct
import csv
import time
import argparse
import os

# ------------------ Checksum ------------------
def calculate_checksum(data):
    return sum(data) % 65536


# ------------------ Args ------------------
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

# ------------------ CSV Setup ------------------
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

device_last_seq = {}
start_time = time.time()


# ------------------ Main Loop ------------------
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

    # Checksum validation
    temp_data = data[:9] + b"\x00\x00" + data[11:]
    integrity = calculate_checksum(temp_data) == checksum

    duplicate_flag = 0
    gap_flag = 0

    # ------------------ INIT ------------------
    if msg_type == MSG_INIT:
        print(f"New device connected. ID={device_id}, Version={version}", flush=True)
        device_last_seq[device_id] = seq

        server_socket.sendto(b"ACK_INIT", addr)
        time.sleep(0.05)
        server_socket.sendto(b"ACK_READY", addr)
        continue

    # ------------------ HEARTBEAT ------------------
    if msg_type == MSG_HEARTBEAT:
        print(f"Heartbeat received from device {device_id}", flush=True)
        continue

    # ------------------ DATA ------------------
    if msg_type == MSG_DATA:
        if device_id in device_last_seq:
            last = device_last_seq[device_id]
            if seq == last:
                duplicate_flag = 1
                duplicate_count += 1
            elif seq > last + 1:
                gap_flag = 1
                sequence_gap_count += 1

        device_last_seq[device_id] = seq

        payload = data[HEADER_SIZE:].decode(errors="ignore")
        values = payload.split(",") if "," in payload else [payload]

        for v in values:
            csv_writer.writerow([
                device_id, seq, timestamp,
                arrival_time, duplicate_flag,
                gap_flag, v
            ])
        file.flush()

        msg = "Batch of {} readings".format(len(values)) if len(values) > 1 else "Data received"
        print(f"{msg} | Packet {seq} | Checksum {'Valid' if integrity else 'Corrupted'}", flush=True)

    total_cpu_time += time.perf_counter() - cpu_start


# ------------------ Summary ------------------
print("\nSession Summary", flush=True)
print("-" * 30, flush=True)
print(f"Total packets received: {packets_received}", flush=True)
print(f"Average packet size: {round(total_bytes / packets_received, 2)} bytes", flush=True)
print(f"Duplicate packet rate: {(duplicate_count / packets_received) * 100:.2f}%", flush=True)
print(f"Sequence gaps detected: {sequence_gap_count}", flush=True)
print(f"Average CPU time per packet: {(total_cpu_time / packets_received) * 1000:.4f} ms", flush=True)
print("Server session ended.", flush=True)

file.close()
server_socket.close()
