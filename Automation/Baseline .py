import subprocess
import time
import os
import signal
import sys

# Let user specify run duration
try:
    RUN_DURATION = int(input("Enter run duration in seconds: "))
except ValueError:
    print("Invalid input. Please enter a number.")
    exit(1)

PYTHON = sys.executable

# Function to find file in project directory
def find_file(filename, search_dir):
    for root, dirs, files in os.walk(search_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None

# Defines Project folder path and this script's path
automation_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.dirname(automation_dir)


server_path = find_file("Server.py", main_dir)
client_path = find_file("Client.py", main_dir)

# Existance Check
if not server_path or not client_path:
    print("Could not find both server.py and client.py in subfolders of the project folder.")
    print(f"Found server: {server_path}")
    print(f"Found client: {client_path}")
    sys.exit(1)

print(f"Found server: {server_path}")
print(f"Found client: {client_path}\n")

# Server should start first
print("Starting server...")
server_dir = os.path.dirname(server_path)
server_process = subprocess.Popen(
    [PYTHON, "-u", os.path.basename(server_path), "--duration", str(RUN_DURATION)],
    cwd=server_dir,  # Run inside its own folder
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Wait for server to bind
time.sleep(1)

# Client starts after server binds
print("Starting client...")
client_dir = os.path.dirname(client_path)
client_process = subprocess.Popen(
    [PYTHON, "-u", os.path.basename(client_path), "--duration", str(RUN_DURATION)],
    cwd=client_dir,  # Run inside its own folder
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)


start_time = time.time()
while time.time() - start_time < RUN_DURATION:
    # Print server output
    if server_process.poll() is None:
        line = server_process.stdout.readline()
        if line:
            print(f"[SERVER] {line.strip()}")

    # Print client output
    if client_process.poll() is None:
        line = client_process.stdout.readline()
        if line:
            print(f"[CLIENT] {line.strip()}")

    time.sleep(0.1)

# To print metrics
for proc, name in [(server_process, "SERVER"), (client_process, "CLIENT")]:
    if proc.stdout:
        for line in proc.stdout.readlines():
            print(f"[{name}] {line.strip()}")   


for proc, name in [(client_process, "Client"), (server_process, "Server")]:
    if proc.poll() is None:
        os.kill(proc.pid, signal.SIGTERM)
        print(f"{name} stopped.")

print("\n TTPv1 session complete!")
