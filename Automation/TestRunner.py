import subprocess
import sys
import threading
import time
import os
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


# Thread-safe printing 
print_lock = threading.Lock()

def safe_print(msg):
    with print_lock:
        print(msg, flush=True)


#  Output streaming from subprocesses
def stream_process(proc, prefix):
    """
    Read process stdout line by line
    and print with stable prefix.
    """
    for line in proc.stdout:
        clean = line.rstrip("\n")
        # Only add prefix if the line doesn't already start with that prefix,
        # to be robust in case child processes accidentally included prefixes.
        if clean.startswith(prefix):
            safe_print(clean)
        else:
            safe_print(f"{prefix} {clean}")


#  Locate Client/Server 
def find_file(filename, search_dir):
    for root, _, files in os.walk(search_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


#  MAIN PROGRAM
if len(sys.argv) < 5:
    print("Usage: python TestRunner.py <server_ip> <duration> <batch_size> <num_clients> [--interval N]")
    sys.exit(1)

INTERVAL = 1
if "--interval" in sys.argv:
    idx = sys.argv.index("--interval")
    INTERVAL = int(sys.argv[idx + 1])


SERVER_IP = sys.argv[1]
DURATION = int(sys.argv[2])
BATCH_SIZE = int(sys.argv[3])
NUM_CLIENTS = int(sys.argv[4])

PYTHON = sys.executable

base_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(base_dir)

server_path = find_file("Server.py", project_dir)
client_path = find_file("Client.py", project_dir)

if not server_path or not client_path:
    safe_print("ERROR: Could not find Server.py or Client.py!")
    sys.exit(1)

#  Start Server 
safe_print("Starting server...")
server_proc = subprocess.Popen(
    [PYTHON, "-u", server_path, "--duration", str(DURATION)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

# Start server log thread
threading.Thread(
    target=stream_process,
    args=(server_proc, "[SERVER]"),
    daemon=True
).start()

time.sleep(0.4)

# Start Clients  
safe_print(f"Starting {NUM_CLIENTS} client(s)...")
client_procs = []

for cid in range(1, NUM_CLIENTS + 1):
    proc = subprocess.Popen(
        [
            PYTHON, "-u", client_path,
            "--server_ip", SERVER_IP,
            "--duration", str(DURATION),
            "--batch_size", str(BATCH_SIZE),
            "--device_id", str(cid),
            "--interval", str(INTERVAL)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    client_procs.append(proc)

    threading.Thread(
        target=stream_process,
        args=(proc, f"[CLIENT {cid}]"),
        daemon=True
    ).start()

safe_print(f"{NUM_CLIENTS} clients started.\n")

#  Wait for all processes to finish
for proc in client_procs:
    proc.wait()

server_proc.wait()

safe_print("\nTest completed.\n")
