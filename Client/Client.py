import socket
import struct
import time
import random
import argparse

# Checksum Calculation
def calculate_checksum(data):
    return sum(data) % 65536

# Argument Parsing
parser = argparse.ArgumentParser()
parser.add_argument("--duration", type=int, default=60)
parser.add_argument("--server_ip", type=str, default="127.0.0.1")
parser.add_argument("--batch_size", type=int, default=1)  # OPTIONAL batching
args = parser.parse_args()

DURATION = args.duration
SERVER_IP = args.server_ip
BATCH_SIZE = max(1, args.batch_size)

# Packet Header Definition
HEADER_FORMAT = "!HBBIBHB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

SERVER_PORT = 9999
DEVICE_ID = 1
DATA_INTERVAL = 1
HEARTBEAT_INTERVAL = 5

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
seq_num = 0
batch_buffer = []

# Packet Construction
def construct_packet_with_checksum(
    device_id, seq_num, msg_type,
    payload=b"", batch_flag=0, version=1
):
    timestamp = int(time.time())

    header = struct.pack(
        HEADER_FORMAT,
        seq_num,
        device_id,
        msg_type,
        timestamp,
        batch_flag,
        0,
        version
    )

    full_packet = header + payload
    packet_for_checksum = full_packet[:9] + b"\x00\x00" + full_packet[11:]
    checksum = calculate_checksum(packet_for_checksum)

    header_with_checksum = struct.pack(
        HEADER_FORMAT,
        seq_num,
        device_id,
        msg_type,
        timestamp,
        batch_flag,
        checksum,
        version
    )

    return header_with_checksum + payload

# INIT
init_packet = construct_packet_with_checksum(DEVICE_ID, seq_num, MSG_INIT)
client_socket.sendto(init_packet, (SERVER_IP, SERVER_PORT))
print(f"Connected to server {SERVER_IP}:{SERVER_PORT}")

start_time = time.time()
last_heartbeat_time = start_time

while time.time() - start_time < DURATION:
    current_time = time.time()

    # Generate reading
    temperature = round(random.uniform(20.0, 34.0), 1)
    batch_buffer.append(str(temperature))

    # Send batch if full
    if len(batch_buffer) >= BATCH_SIZE:
        seq_num += 1
        payload = ",".join(batch_buffer).encode("utf-8")

        packet = construct_packet_with_checksum(
            DEVICE_ID,
            seq_num,
            MSG_DATA,
            payload,
            batch_flag=len(batch_buffer)
        )
        client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))

        print(f"Sent batch of {len(batch_buffer)} readings (packet {seq_num})")
        batch_buffer.clear()

    # Heartbeat
    if current_time - last_heartbeat_time >= HEARTBEAT_INTERVAL:
        seq_num += 1
        heartbeat = construct_packet_with_checksum(
            DEVICE_ID,
            seq_num,
            MSG_HEARTBEAT
        )
        client_socket.sendto(heartbeat, (SERVER_IP, SERVER_PORT))
        print("Heartbeat sent")
        last_heartbeat_time = current_time

    time.sleep(DATA_INTERVAL)

# Flush remaining batch
if batch_buffer:
    seq_num += 1
    payload = ",".join(batch_buffer).encode("utf-8")
    packet = construct_packet_with_checksum(
        DEVICE_ID,
        seq_num,
        MSG_DATA,
        payload,
        batch_flag=len(batch_buffer)
    )
    client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
    print(f"Sent final batch of {len(batch_buffer)} readings (packet {seq_num})")

print("Finished sending data.")
client_socket.close()
