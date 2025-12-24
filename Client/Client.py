import socket
import struct
import time
import random
import argparse
import sys

# Constants 
HEADER_FORMAT = "!HBBIBHB"
MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

VERSION = 1
HEARTBEAT_INTERVAL = 5

INIT_TIMEOUT = 2
INIT_MAX_RETRIES = 5

# Checksum 
def calculate_checksum(data):
    return sum(data) % 65536

# Args 
parser = argparse.ArgumentParser()
parser.add_argument("--server_ip", required=True)
parser.add_argument("--duration", type=int, default=60)
parser.add_argument("--batch_size", type=int, default=0)
parser.add_argument("--device_id", type=int, default=1)
parser.add_argument(
    "--interval",
    type=int,
    default=1,
    choices=[1, 5, 30],
    help="Reporting interval in seconds"
)
args = parser.parse_args()

SERVER_IP = args.server_ip
DEVICE_ID = args.device_id
DURATION = args.duration
BATCH_SIZE = max(0, args.batch_size)
SEND_INTERVAL = args.interval 

# Socket 
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_addr = (SERVER_IP, 9999)
sock.settimeout(INIT_TIMEOUT)

print(
    f"Connecting to server {SERVER_IP}:9999 "
    f"(interval={SEND_INTERVAL}s)",
    flush=True
)

# Relative Timestamp 
START_TIME = time.time()

def get_timestamp_ms():
    return int((time.time() - START_TIME) * 1000)

# INIT Handshake 
seq = 0
retry = 0

while retry < INIT_MAX_RETRIES:
    timestamp_ms = get_timestamp_ms()

    init = struct.pack(
        HEADER_FORMAT,
        seq, DEVICE_ID,
        MSG_INIT, timestamp_ms,
        0, 0, VERSION
    )

    checksum = calculate_checksum(init)
    init = init[:9] + struct.pack("!H", checksum) + init[11:]

    print(f"Sending INIT attempt {retry + 1}", flush=True)
    sock.sendto(init, server_addr)

    try:
        ack1, _ = sock.recvfrom(1024)
        if ack1 == b"ACK_INIT":
            ack2, _ = sock.recvfrom(1024)
            if ack2 == b"ACK_READY":
                print("Server READY — starting data\n", flush=True)
                seq += 1
                break
    except socket.timeout:
        print("No ACK, retrying...", flush=True)
        retry += 1

if retry == INIT_MAX_RETRIES:
    print("INIT handshake FAILED — exiting.", flush=True)
    sock.close()
    sys.exit(1)

# Send Helpers 
def send_packet(payload):
    global seq
    timestamp_ms = get_timestamp_ms()

    header = struct.pack(
        HEADER_FORMAT,
        seq, DEVICE_ID,
        MSG_DATA, timestamp_ms,
        0, 0, VERSION
    )

    packet = header + payload.encode()
    checksum = calculate_checksum(packet)
    packet = packet[:9] + struct.pack("!H", checksum) + packet[11:]

    sock.sendto(packet, server_addr)
    seq += 1

def send_single():
    temp = round(random.uniform(20, 35), 1)
    send_packet(str(temp))
    print(f"Sent temp {temp} (packet {seq-1})", flush=True)

def send_batch(buffer):
    payload = ",".join(buffer)
    send_packet(payload)
    print(f"Sent batch of {len(buffer)} readings (packet {seq-1})", flush=True)

# Main Loop 
start = time.time()
last_heartbeat = start
buffer = []

while time.time() - start < DURATION:

    now = time.time()

    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        timestamp_ms = get_timestamp_ms()
        hb = struct.pack(
            HEADER_FORMAT,
            seq, DEVICE_ID,
            MSG_HEARTBEAT, timestamp_ms,
            0, 0, VERSION
        )
        checksum = calculate_checksum(hb)
        hb = hb[:9] + struct.pack("!H", checksum) + hb[11:]

        sock.sendto(hb, server_addr)
        print("Heartbeat sent", flush=True)
        last_heartbeat = now

    if BATCH_SIZE == 0:
        send_single()
    else:
        temp = round(random.uniform(20, 35), 1)
        buffer.append(str(temp))
        if len(buffer) >= BATCH_SIZE:
            send_batch(buffer)
            buffer.clear()

    time.sleep(SEND_INTERVAL)

if BATCH_SIZE > 0 and buffer:
    send_batch(buffer)

print("Finished sending data", flush=True)
sock.close()
