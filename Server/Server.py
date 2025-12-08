import socket
import struct
import csv
import time
import argparse

# Checksum Calculation
def calculate_checksum(data):
    return sum(data) % 65536

# Argument Parsing
parser = argparse.ArgumentParser()
parser.add_argument("--duration", type=int, default=60)
args = parser.parse_args()

DURATION = args.duration


# Packet Header Definition
# SeqNum (H), DeviceID (B), MsgType (B), Timestamp (I),
# BatchFlag (B), Checksum (H), Version (B)
HEADER_FORMAT = "!HBBIBHB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3



# Metrics
total_bytes = 0
packets_received = 0
duplicate_count = 0
sequence_gap_count = 0
total_cpu_time = 0

# Socket Setup
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", 9999))

print("Server is running and listening for sensor data on port 9999...", flush=True)


# Device State Tracking
device_last_seq = {}


# CSV Setup
file = open("sensor_data.csv", "w", newline="")
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

# Main Receive Loop
start_time = time.time()

while time.time() - start_time < DURATION:
    data, client_address = server_socket.recvfrom(1024)
    arrival_time = time.time()
    cpu_start_time = time.perf_counter()

    packets_received += 1
    total_bytes += len(data)

    # Basic Validation
    if len(data) < HEADER_SIZE:
        print(f"Warning: Ignored malformed packet ({len(data)} bytes)", flush=True)
        continue

    # Parse Header
    seq, device_id, msg_type, timestamp, batch_flag, checksum, version = struct.unpack(
        HEADER_FORMAT, data[:HEADER_SIZE]
    )

    # Checksum verification
    data_without_checksum = data[:9] + b"\x00\x00" + data[11:]
    calculated_checksum = calculate_checksum(data_without_checksum)

    if calculated_checksum != checksum:
        print(
            f"Warning: Checksum mismatch for packet {seq} from device {device_id}",
            flush=True
        )

    # Payload Handling
    payload = ""
    if len(data) > HEADER_SIZE:
        payload = data[HEADER_SIZE:].decode("utf-8", errors="ignore")

    duplicate_flag = 0
    gap_flag = 0

    # INIT Message
    if msg_type == MSG_INIT:
        print(
            f"New device connected. ID={device_id}, "
            f"Version={version}, Address={client_address}",
            flush=True
        )
        device_last_seq[device_id] = seq

    # DATA Message
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

        csv_writer.writerow([
            device_id,
            seq,
            timestamp,
            arrival_time,
            duplicate_flag,
            gap_flag,
            payload
        ])
        file.flush()

        integrity_status = "Valid" if calculated_checksum == checksum else "Corrupted"

        print(
            f"Data received from device {device_id} | "
            f"Packet {seq} | Value: {payload} | "
            f"Duplicate: {'Yes' if duplicate_flag else 'No'} | "
            f"Sequence gap: {'Yes' if gap_flag else 'No'} | "
            f"Checksum: {integrity_status}",
            flush=True
        )

    cpu_end_time = time.perf_counter()
    total_cpu_time += (cpu_end_time - cpu_start_time)


# Final Metrics Summary
bytes_per_report = round(total_bytes / packets_received, 2) if packets_received else 0
duplicate_rate = (duplicate_count / packets_received) * 100 if packets_received else 0
cpu_ms_per_report = (total_cpu_time / packets_received) * 1000 if packets_received else 0

print("\nSession Summary")
print("-" * 30)
print(f"Total packets received: {packets_received}")
print(f"Average packet size: {bytes_per_report} bytes")
print(f"Duplicate packet rate: {duplicate_rate:.2f}%")
print(f"Sequence gaps detected: {sequence_gap_count}")
print(f"Average CPU time per packet: {cpu_ms_per_report:.6f} ms")
print("Server session ended.")

file.close()
server_socket.close()
