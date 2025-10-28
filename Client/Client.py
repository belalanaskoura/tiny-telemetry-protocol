import socket
import struct
import time
import random

# Header format same as server
HEADER_FORMAT = "!HHIBBH"
MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

SERVER_IP = "127.0.0.1"   # change to server IP if needed
SERVER_PORT = 5005
DEVICE_ID = 1
INTERVAL = 1      # seconds

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
seq_num = 0

def build_header(device_id, seq_num, msg_type, flags=0):
    timestamp = int(time.time())
    return struct.pack(HEADER_FORMAT, device_id, seq_num, timestamp, msg_type, flags, 0)

# Step 1: Send INIT packet
init_header = build_header(DEVICE_ID, seq_num, MSG_INIT)
client_socket.sendto(init_header, (SERVER_IP, SERVER_PORT))
print("[INIT] sent to server")

# Step 2: Periodically send data packets
while True:
    seq_num += 1
    header = build_header(DEVICE_ID, seq_num, MSG_DATA)
    # Simulated sensor reading (temperature)
    temperature = round(random.uniform(20.0, 30.0), 2)
    payload = f"{temperature}".encode("utf-8")
    packet = header + payload

    client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
    print(f"[DATA] sent seq={seq_num}, temp={temperature}")
    time.sleep(INTERVAL)
