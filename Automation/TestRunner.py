import subprocess
import time
import os
import sys
import socket

# Get LAN IP or fallback to localhost
def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# Read arguments
# Usage:
# python TestRunner.py <server_ip> <duration> <batch_size>
if len(sys.argv) >= 4:
    SERVER_IP = sys.argv[1]
    DURATION = int(sys.argv[2])
    BATCH_SIZE = int(sys.argv[3])
else:
    default_ip = get_lan_ip()
    SERVER_IP = input(f"Enter server IP (default {default_ip}): ").strip() or default_ip
    DURATION = int(input("Enter duration (seconds): "))
    BATCH_SIZE = int(input("Enter batch size (0 = no batching): "))

# Defensive bounds
if BATCH_SIZE < 0:
    BATCH_SIZE = 0
if BATCH_SIZE > DURATION:
    BATCH_SIZE = DURATION

PYTHON = sys.executable


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


print("Starting server...")
server_process = subprocess.Popen(
    [PYTHON, "-u", server_path, "--duration", str(DURATION)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

time.sleep(1)

print("Starting client...")
client_process = subprocess.Popen(
    [
        PYTHON,
        "-u", client_path,
        "--duration", str(DURATION),
        "--server_ip", SERVER_IP,
        "--batch_size", str(BATCH_SIZE)
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

start_time = time.time()

while time.time() - start_time < DURATION:
    for proc, label in [(server_process, "SERVER"), (client_process, "CLIENT")]:
        if proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                print(f"[{label}] {line.strip()}")
    time.sleep(0.1)

# Drain remaining output
for proc, label in [(server_process, "SERVER"), (client_process, "CLIENT")]:
    if proc.stdout:
        for line in proc.stdout.readlines():
            print(f"[{label}] {line.strip()}")

print("Test completed.")
