import socket
import struct
import csv
import time

# Header format: DeviceID (H), SeqNum (H), Timestamp (I), MsgType (B), Flags (B), Reserved (H)
HEADER_FORMAT = "!HHIBBH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Message types
MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

# Create UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(("0.0.0.0", 5005))
print("Server listening on port 5005...")

# Track device info
device_last_seq = {}

# Prepare CSV file
with open("sensor_data.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["device_id", "seq", "timestamp", "arrival_time", "duplicate_flag", "gap_flag", "data_value"])

    while True:
        data, addr = server_socket.recvfrom(1024)
        arrival_time = time.time()

        if len(data) < HEADER_SIZE:
            continue  # ignore invalid packet

        # Parse header
        device_id, seq, timestamp, msg_type, flags, _ = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        payload = data[HEADER_SIZE:].decode("utf-8") if len(data) > HEADER_SIZE else ""

        duplicate_flag = 0
        gap_flag = 0

        if msg_type == MSG_INIT:
            print(f"[INIT] Device {device_id} connected from {addr}")
            device_last_seq[device_id] = seq

        elif msg_type == MSG_DATA:
            # Detect duplicates
            if device_id in device_last_seq:
                last_seq = device_last_seq[device_id]
                if seq == last_seq:
                    duplicate_flag = 1
                elif seq > last_seq + 1:
                    gap_flag = 1
            device_last_seq[device_id] = seq

            writer.writerow([device_id, seq, timestamp, arrival_time, duplicate_flag, gap_flag, payload])
            file.flush()
            print(f"[DATA] Device {device_id} Seq={seq} Value={payload} Dup={duplicate_flag} Gap={gap_flag}")

        elif msg_type == MSG_HEARTBEAT:
            print(f"[HEARTBEAT] from Device {device_id}")