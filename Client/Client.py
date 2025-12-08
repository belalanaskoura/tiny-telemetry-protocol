import socket
import struct
import time
import random
import argparse

# ------------------ Constants ------------------
HEADER_FORMAT = "!HBBIBHB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

DEVICE_ID = 1
VERSION = 1
HEARTBEAT_INTERVAL = 10
SEND_INTERVAL = 1


# ------------------ Checksum ------------------
def calculate_checksum(data):
    return sum(data) % 65536


# ------------------ Argument Parsing ------------------
parser = argparse.ArgumentParser()
parser.add_argument("--server_ip", type=str, required=True)
parser.add_argument("--duration", type=int, default=60)
parser.add_argument("--batch_size", type=int, default=0)
args = parser.parse_args()

SERVER_IP = args.server_ip
DURATION = args.duration
BATCH_SIZE = args.batch_size

if BATCH_SIZE < 0:
    BATCH_SIZE = 0


# ------------------ Socket Setup ------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (SERVER_IP, 9999)

print(f"Connected to server {SERVER_IP}:9999")

# ------------------ INIT ------------------
seq = 1
init_header = struct.pack(
    HEADER_FORMAT,
    seq,
    DEVICE_ID,
    MSG_INIT,
    int(time.time()),
    0,
    0,
    VERSION
)

checksum = calculate_checksum(init_header)
init_header = init_header[:9] + struct.pack("!H", checksum) + init_header[11:]

sock.sendto(init_header, server_address)
print("Initialization packet sent")

seq += 1


# ------------------ Send Logic ------------------
start_time = time.time()
last_heartbeat = start_time

batch_buffer = []


def send_packet(payload):
    global seq

    header = struct.pack(
        HEADER_FORMAT,
        seq,
        DEVICE_ID,
        MSG_DATA,
        int(time.time()),
        0,
        0,
        VERSION
    )

    packet = header + payload.encode()
    checksum = calculate_checksum(packet)
    packet = packet[:9] + struct.pack("!H", checksum) + packet[11:]

    sock.sendto(packet, server_address)
    seq += 1


def send_single_reading():
    temperature = round(random.uniform(20.0, 35.0), 1)
    send_packet(str(temperature))
    print(f"Sent temperature {temperature} (packet {seq - 1})")


def send_batch():
    global batch_buffer

    payload = ",".join(batch_buffer)
    send_packet(payload)
    print(f"Sent batch of {len(batch_buffer)} readings (packet {seq - 1})")
    batch_buffer = []


# ------------------ Main Loop ------------------
print(f"Batching {'Enabled' if BATCH_SIZE > 0 else 'Disabled'}")

while time.time() - start_time < DURATION:

    current_time = time.time()

    # -------- HEARTBEAT --------
    if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
        heartbeat_header = struct.pack(
            HEADER_FORMAT,
            seq,
            DEVICE_ID,
            MSG_HEARTBEAT,
            int(current_time),
            0,
            0,
            VERSION
        )

        checksum = calculate_checksum(heartbeat_header)
        heartbeat_packet = (
            heartbeat_header[:9] +
            struct.pack("!H", checksum) +
            heartbeat_header[11:]
        )

        sock.sendto(heartbeat_packet, server_address)
        print("Heartbeat sent")
        seq += 1
        last_heartbeat = current_time

    # -------- DATA SENDING --------
    if BATCH_SIZE == 0:
        # --- NO BATCHING MODE ---
        send_single_reading()
        time.sleep(SEND_INTERVAL)

    else:
        # --- BATCHING MODE ---
        temperature = round(random.uniform(20.0, 35.0), 1)
        batch_buffer.append(str(temperature))

        if len(batch_buffer) >= BATCH_SIZE:
            send_batch()

        time.sleep(SEND_INTERVAL)

# -------- Flush remaining batch --------
if BATCH_SIZE > 0 and batch_buffer:
    send_batch()

print("Finished sending data")
sock.close()
