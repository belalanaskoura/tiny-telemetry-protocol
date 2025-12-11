import subprocess
import time
import os
import sys
import socket

# ------------------ Get LAN IP ------------------
def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ------------------ Read Arguments ------------------
# Usage:
# python TestRunner.py <server_ip> <duration> <batch_size> <num_clients>
if len(sys.argv) >= 5:
    SERVER_IP = sys.argv[1]
    DURATION = int(sys.argv[2])
    BATCH_SIZE = int(sys.argv[3])
    NUM_CLIENTS = int(sys.argv[4])
else:
    default_ip = get_lan_ip()
    SERVER_IP = input(f"Enter server IP (default {default_ip}): ").strip() or default_ip
    DURATION = int(input("Enter duration (seconds): "))
    BATCH_SIZE = int(input("Enter batch size (0 = no batching): "))
    NUM_CLIENTS = int(input("Enter number of clients: "))

# Defensive bounds
BATCH_SIZE = max(0, min(BATCH_SIZE, DURATION))
NUM_CLIENTS = max(1, NUM_CLIENTS)

PYTHON = sys.executable


# ------------------ Find Server & Client Paths ------------------
def find_file(filename, search_dir):
    for root, _, files in os.walk(search_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


automation_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.dirname(automation_dir)

server_path = find_file("Server.py", main_dir)
client_path = find_file("Client.py", main_dir)

if not server_path or not client_path:
    print("Error: Could not find Server.py or Client.py")
    sys.exit(1)


# ------------------ Start the Server ------------------
print("Starting server...")
server_process = subprocess.Popen(
    [PYTHON, "-u", server_path, "--duration", str(DURATION)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

time.sleep(1)


# ------------------ Start Multiple Clients ------------------
client_processes = []

print(f"Starting {NUM_CLIENTS} client(s)...")

for cid in range(1, NUM_CLIENTS + 1):
    cmd = [
        PYTHON,
        "-u", client_path,
        "--duration", str(DURATION),
        "--server_ip", SERVER_IP,
        "--batch_size", str(BATCH_SIZE),
        "--device_id", str(cid)
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    client_processes.append((cid, proc))


print(f"{NUM_CLIENTS} clients started.\n")


# ------------------ Stream Output ------------------
start_time = time.time()

while time.time() - start_time < DURATION:
    # Check server output
    if server_process.poll() is None:
        line = server_process.stdout.readline()
        if line:
            print(f"[SERVER] {line.strip()}")

    # Check each client output
    for cid, proc in client_processes:
        if proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                print(f"[CLIENT {cid}] {line.strip()}")

    time.sleep(0.05)


# Drain remaining output
for label, proc in [("SERVER", server_process)]:
    for line in proc.stdout.readlines():
        print(f"[{label}] {line.strip()}")

for cid, proc in client_processes:
    for line in proc.stdout.readlines():
        print(f"[CLIENT {cid}] {line.strip()}")

print("\nTest completed.")
