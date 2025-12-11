import socket
import struct
import time
import random
import argparse
import sys

# ------------------ Constants ------------------
HEADER_FORMAT = "!HBBIBHB"
MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

DEVICE_ID = 1
VERSION = 1
SEND_INTERVAL = 1
HEARTBEAT_INTERVAL = 5

INIT_TIMEOUT = 2
INIT_MAX_RETRIES = 5

# ------------------ Checksum ------------------
def calculate_checksum(data):
    return sum(data) % 65536

# ------------------ Args ------------------
parser = argparse.ArgumentParser()
parser.add_argument("--server_ip", required=True)
parser.add_argument("--duration", type=int, default=60)
parser.add_argument("--batch_size", type=int, default=0)
args = parser.parse_args()

SERVER_IP = args.server_ip
DURATION = args.duration
BATCH_SIZE = max(0, args.batch_size)

# ------------------ Socket ------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_addr = (SERVER_IP, 9999)
sock.settimeout(INIT_TIMEOUT)

print(f"Connected to server {SERVER_IP}:9999")

# ------------------ INIT with Retransmission ------------------
seq = 1
retry = 0

while retry < INIT_MAX_RETRIES:
    init = struct.pack(
        HEADER_FORMAT, seq, DEVICE_ID,
        MSG_INIT, int(time.time()),
        0, 0, VERSION
    )
    checksum = calculate_checksum(init)
    init = init[:9] + struct.pack("!H", checksum) + init[11:]

    print(f"Sending INIT attempt {retry + 1}")
    sock.sendto(init, server_addr)

    try:
        ack, _ = sock.recvfrom(1024)
        if ack == b"ACK_INIT":
            print("INIT acknowledged by server\n")
            seq += 1
            break
    except socket.timeout:
        print("No ACK received, retrying...")
        retry += 1

if retry == INIT_MAX_RETRIES:
    print("Failed to complete INIT handshake. Exiting.")
    sock.close()
    sys.exit(1)

# ------------------ Main Loop Setup ------------------
start_time = time.time()
last_heartbeat = start_time
batch_buffer = []

# ------------------ Send Helpers ------------------
def send_packet(payload):
    global seq
    header = struct.pack(
        HEADER_FORMAT, seq, DEVICE_ID,
        MSG_DATA, int(time.time()),
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
    print(f"Sent temperature {temp} (packet {seq-1})")

def send_batch():
    payload = ",".join(batch_buffer)
    send_packet(payload)
    print(f"Sent batch of {len(batch_buffer)} readings (packet {seq-1})")
    batch_buffer.clear()

# ------------------ Loop ------------------
while time.time() - start_time < DURATION:
    now = time.time()

    # Heartbeat
    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        hb = struct.pack(
            HEADER_FORMAT, seq, DEVICE_ID,
            MSG_HEARTBEAT, int(now),
            0, 0, VERSION
        )
        checksum = calculate_checksum(hb)
        hb = hb[:9] + struct.pack("!H", checksum) + hb[11:]
        sock.sendto(hb, server_addr)

        print("Heartbeat sent", flush=True)
        last_heartbeat = now
        seq += 1

    # Data
    if BATCH_SIZE == 0:
        send_single()
    else:
        batch_buffer.append(str(round(random.uniform(20, 35), 1)))
        if len(batch_buffer) >= BATCH_SIZE:
            send_batch()

    time.sleep(SEND_INTERVAL)

# Final batch flush
if BATCH_SIZE > 0 and batch_buffer:
    send_batch()

print("Finished sending data")
sock.close()
