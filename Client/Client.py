import socket
import struct
import time
import random

# Header format same as server
HEADER_FORMAT = "!HBBIBHB"
MSG_INIT = 1
MSG_DATA = 2
MSG_HEARTBEAT = 3

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9999
DEVICE_ID = 1 #Changes based on the number of sensors
INTERVAL = 1
DURATION = 60 #Sends 60 packets per minute 

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
seq_num = 0

# Function to create header of packet
def build_header(device_id, seq_num, msg_type, batch_flag=0, checksum=0, version=1):
    timestamp = int(time.time())
    return struct.pack(HEADER_FORMAT, seq_num, device_id, msg_type, timestamp, batch_flag, checksum, version)


# Send INIT packet
init_header = build_header(DEVICE_ID, seq_num, MSG_INIT, version= 1)
client_socket.sendto(init_header, (SERVER_IP, SERVER_PORT))
print("[INIT] sent to server")

start_time = time.time()

#Send data packets for the specified duration
while time.time() - start_time < DURATION:
    seq_num += 1
    header = build_header(DEVICE_ID, seq_num, MSG_DATA, batch_flag= 0, checksum= 0, version= 1)

    # Simulated sensor reading (temperature)
    temperature = round(random.uniform(20.0, 34.0), 1)
    payload = f"{temperature}".encode("utf-8")
    packet = header + payload

    client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
    print(f"[DATA] sent seq={seq_num}, temp={temperature}")
    time.sleep(INTERVAL)

print(f" Finished sending data for {DURATION} seconds.")
client_socket.close()    
