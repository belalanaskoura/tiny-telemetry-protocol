import socket
import struct
import time
import random
import argparse

# Calculate simple checksum by summing all bytes modulo 65536
def calculate_checksum(data):
    return sum(data) % 65536

parser = argparse.ArgumentParser()
parser.add_argument("--duration", type=int, default=60)
args = parser.parse_args()

HEADER_FORMAT = "!HBBIBHB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9999
DEVICE_ID = 1
INTERVAL = 1
DURATION = args.duration

# Simulation controls
LOSS_PROBABILITY = 0.15       # 15% chance to drop a packet
DUPLICATE_PROBABILITY = 0.10  # 10% chance to resend the same packet

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
seq_num = 0
last_packet = None

def construct_packet_with_checksum(device_id, seq_num, msg_type, payload=b"", batch_flag=0, version=1):
    """Construct complete packet with proper checksum"""
    timestamp = int(time.time())

    # Pack header with checksum=0
    header = struct.pack(HEADER_FORMAT, seq_num, device_id, msg_type,
                         timestamp, batch_flag, 0, version)

    full_packet = header + payload

    # Calculate checksum with checksum field zeroed
    packet_for_checksum = full_packet[:9] + b'\x00\x00' + full_packet[11:]
    checksum = calculate_checksum(packet_for_checksum)

    # Repack header with correct checksum
    header_with_checksum = struct.pack(HEADER_FORMAT, seq_num, device_id, msg_type,
                                       timestamp, batch_flag, checksum, version)

    return header_with_checksum + payload, checksum


# Send INIT packet
init_packet, init_checksum = construct_packet_with_checksum(DEVICE_ID, seq_num, MSG_INIT)
client_socket.sendto(init_packet, (SERVER_IP, SERVER_PORT))
print(f"[INIT] sent to server, checksum={init_checksum}", flush=True)

start_time = time.time()

# Send data packets for the specified duration
while time.time() - start_time < DURATION:
    seq_num += 1

    if seq_num > 65535:
        seq_num = 1

    # Simulated sensor reading (temperature)
    temperature = round(random.uniform(20.0, 34.0), 1)
    payload = f"{temperature}".encode("utf-8")

    # Construct packet with proper checksum
    packet, checksum = construct_packet_with_checksum(DEVICE_ID, seq_num, MSG_DATA, payload)

    # Randomly simulate packet loss or duplication
    r = random.random()

    if r < LOSS_PROBABILITY:
        time.sleep(INTERVAL)
        continue

    if r < LOSS_PROBABILITY + DUPLICATE_PROBABILITY and last_packet:
        client_socket.sendto(last_packet, (SERVER_IP, SERVER_PORT))

    # Normal send
    client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
    last_packet = packet
    print(f"[DATA] sent seq={seq_num}, temp={temperature}, checksum={checksum}", flush=True)

    # Drift-corrected sleep: Ensures that each packet is sent EXACTLY 1 second after its predecessor
    next_time = start_time + seq_num * INTERVAL
    sleep_time = next_time - time.time()
    if sleep_time > 0:
        time.sleep(sleep_time)

print(f"Finished sending data for {DURATION} seconds.")
client_socket.close()
