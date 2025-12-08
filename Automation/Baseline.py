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
if len(sys.argv) >= 4:
    SERVER_IP = sys.argv[1]
    RUN_DURATION = int(sys.argv[2])
    BATCH_SIZE = int(sys.argv[3])
else:
    try:
        default_ip = get_lan_ip()
        SERVER_IP = input(f"Enter server IP address (default {default_ip}): ").strip() or default_ip
        RUN_DURATION = int(input("Enter run duration in seconds: "))
        BATCH_SIZE = int(input("Enter batch size (1 = no batching): "))
    except ValueError:
        print("Invalid input. Please enter numeric values.")
        sys.exit(1)

# Safety check
if BATCH_SIZE < 1:
    BATCH_SIZE = 1
if BATCH_SIZE > RUN_DURATION:
    BATCH_SIZE = RUN_DURATION

PYTHON = sys.executable


# Find file in project directory
def find_file(filename, search_dir):
    for root, _, files in os.walk(search_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


# Paths
automation_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.dirname(automation_dir)

server_path = find_file("Server.py", main_dir)
client_path = find_file("Client.py", main_dir)

if not server_path or not client_path:
    print("Could not find both Server.py and Client.py.")
    print(f"Found server: {server_path}")
    print(f"Found client: {client_path}")
    sys.exit(1)

print(f"Found server: {server_path}")
print(f"Found client: {client_path}\n")


# Start server
print("Starting server...")
server_dir = os.path.dirname(server_path)
server_process = subprocess.Popen(
    [PYTHON, "-u", os.path.basename(server_path), "--duration", str(RUN_DURATION)],
    cwd=server_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

time.sleep(1)

# Start client
print("Starting client...")
client_dir = os.path.dirname(client_path)
client_process = subprocess.Popen(
    [
        PYTHON,
        "-u",
        os.path.basename(client_path),
        "--duration", str(RUN_DURATION),
        "--server_ip", SERVER_IP,
        "--batch_size", str(BATCH_SIZE)
    ],
    cwd=client_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)


start_time = time.time()
while time.time() - start_time < RUN_DURATION:
    if server_process.poll() is None:
        line = server_process.stdout.readline()
        if line:
            print(f"[SERVER] {line.strip()}")

    if client_process.poll() is None:
        line = client_process.stdout.readline()
        if line:
            print(f"[CLIENT] {line.strip()}")

    time.sleep(0.1)


# Drain remaining output (metrics)
for proc, name in [(server_process, "SERVER"), (client_process, "CLIENT")]:
    if proc.stdout:
        for line in proc.stdout.readlines():
            print(f"[{name}] {line.strip()}")


# Clean shutdown
for proc, name in [(client_process, "Client"), (server_process, "Server")]:
    if proc.poll() is None:
        print(f"Stopping {name}...")
        proc.terminate()
        try:
            proc.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            print(f"{name} did not stop, killing it...")
            proc.kill()
        else:
            print(f"{name} stopped cleanly.")

print("\nTTPv1 session complete!")
