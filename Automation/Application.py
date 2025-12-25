import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import sys
import socket
import threading
import pandas as pd
from tabulate import tabulate
import time

# Path Setup 
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

csv_path = os.path.join(base_path, "../sensor_data.csv")
test_runner_path = os.path.join(base_path, "TestRunner.py")


# Utility Functions 
def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def show_csv_content():
    if not os.path.exists(csv_path):
        return

    try:
        df = pd.read_csv(csv_path)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        if 'arrival_time' in df.columns:
            try:
                df['arrival_time'] = pd.to_datetime(df['arrival_time'], unit='s')
            except Exception:
                pass

        table = tabulate(df, headers='keys', tablefmt='grid', showindex=False)
        log_box.configure(state="normal")
        log_box.insert("end", "\n" + table + "\n")
        log_box.configure(state="disabled")

    except Exception as e:
        log_box.configure(state="normal")
        log_box.insert("end", f"\nError reading CSV: {e}\n")
        log_box.configure(state="disabled")

# Stream process output (NO METRICS)  
def stream_process_output(process):
    # Reader Thread
    def reader():
        for raw in iter(process.stdout.readline, ''):
            if not raw:
                if process.poll() is not None:
                    break
                time.sleep(0.01)
                continue

            clean = raw.rstrip("\n")

            # Insert log line
            log_box.configure(state="normal")
            log_box.insert("end", clean + "\n")
            log_box.see("end")
            log_box.configure(state="disabled")

        # Show completion
        log_box.configure(state="normal")
        log_box.insert("end", "\n--- Test Completed ---\n")
        log_box.see("end")
        log_box.configure(state="disabled")

        show_csv_content()

    threading.Thread(target=reader, daemon=True).start()

# Recommendation Logic  
def recommend_batch_size(duration):
    return max(1, min(duration // 5, 10))

def update_batch_recommendation(event=None):
    if not batching_enabled.get():
        return
    if test_type.get() != "Custom Test":
        return
    if not duration_entry.get().isdigit():
        return
    duration = int(duration_entry.get())
    batch_entry.delete("0", "end")
    batch_entry.insert(0, str(recommend_batch_size(duration)))

#  Test Switching Logic  
def force_custom_test():
    if test_type.get() != "Custom Test":
        test_type.set("Custom Test")
        on_test_type_change()

def on_test_type_change():
    if test_type.get() == "Baseline Test (60s, no batching)":
        batching_enabled.set(False)
        batch_frame.pack_forget()
        batch_entry.delete(0, "end")
        batch_entry.insert(0, "0")
        interval_var.set("1")
        interval_menu.configure(state="disabled")
    else:
        interval_menu.configure(state="normal")


# Run Test  
def run_test():
    ip = ip_entry.get().strip() or get_lan_ip()
    if test_type.get() == "Baseline Test (60s, no batching)":
        duration = 60
        batch_size = 0
        num_clients = 1
        interval = 1
    else:
        if not duration_entry.get().isdigit():
            messagebox.showerror("Invalid Input", "Duration must be a number.")
            return

        duration = int(duration_entry.get())

        if not clients_entry.get().isdigit() or int(clients_entry.get()) < 1:
            messagebox.showerror("Invalid Input", "Clients must be >= 1.")
            return

        num_clients = int(clients_entry.get())
        interval = int(interval_var.get())
        

        if batching_enabled.get():
            if not batch_entry.get().isdigit():
                messagebox.showerror("Invalid Input", "Batch size must be numeric.")
                return
            batch_size = int(batch_entry.get())
        else:
            batch_size = 0

    log_box.configure(state="normal")
    log_box.delete("1.0", "end")
    log_box.insert(
        "end",
        f"Running test: duration={duration}, batch={batch_size}, clients={num_clients}\n\n"
    )
    log_box.configure(state="disabled")

    cmd = [
        sys.executable, "-u", test_runner_path,
        ip, str(duration), str(batch_size), str(num_clients),
        "--interval", str(interval)
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    stream_process_output(process)

# GUI Setup  
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Tiny Telemetry Protocol")
root.geometry("1300x750")

# Title
ctk.CTkLabel(
    root,
    text="Tiny Telemetry Protocol v1",
    font=ctk.CTkFont(size=24, weight="bold")
).pack(pady=10)

# Control Panel  
controls_frame = ctk.CTkFrame(root)
controls_frame.pack(fill="x", pady=8)

# Test Mode
test_type = ctk.StringVar(value="Baseline Test (60s, no batching)")

ctk.CTkOptionMenu(
    controls_frame,
    values=["Baseline Test (60s, no batching)", "Custom Test"],
    variable=test_type,
    command=lambda _: on_test_type_change()
).pack(side="left", padx=10)

# Server IP
ip_frame = ctk.CTkFrame(controls_frame)
ip_frame.pack(side="left", padx=10)
ctk.CTkLabel(ip_frame, text="Server IP:").grid(row=0, column=0, padx=5)
ip_entry = ctk.CTkEntry(ip_frame, width=180)
ip_entry.insert(0, get_lan_ip())
ip_entry.grid(row=0, column=1, padx=5)

# Duration
dur_frame = ctk.CTkFrame(controls_frame)
dur_frame.pack(side="left", padx=10)
ctk.CTkLabel(dur_frame, text="Duration:").grid(row=0, column=0, padx=5)
duration_entry = ctk.CTkEntry(dur_frame, width=80)
duration_entry.insert(0, "60")
duration_entry.grid(row=0, column=1, padx=5)
duration_entry.bind("<KeyPress>", lambda e: force_custom_test())
duration_entry.bind("<KeyRelease>", update_batch_recommendation)

# Clients
cl_frame = ctk.CTkFrame(controls_frame)
cl_frame.pack(side="left", padx=10)
ctk.CTkLabel(cl_frame, text="Clients:").grid(row=0, column=0, padx=5)
clients_entry = ctk.CTkEntry(cl_frame, width=60)
clients_entry.insert(0, "1")
clients_entry.grid(row=0, column=1, padx=5)

# Batching Checkbox
batching_enabled = ctk.BooleanVar(value=False)

def toggle_batch():
    if test_type.get() != "Custom Test":
        force_custom_test()
    if batching_enabled.get():
        batch_frame.pack(side="left", padx=10)
        update_batch_recommendation()
    else:
        batch_frame.pack_forget()
        batch_entry.delete(0, "end")
        batch_entry.insert(0, "0")

ctk.CTkCheckBox(
    controls_frame,
    text="Enable Batching",
    variable=batching_enabled,
    command=toggle_batch
).pack(side="left", padx=10)

# Batch Size
batch_frame = ctk.CTkFrame(controls_frame)
ctk.CTkLabel(batch_frame, text="Batch Size:").grid(row=0, column=0, padx=5)
batch_entry = ctk.CTkEntry(batch_frame, width=80)
batch_entry.insert(0, "0")
batch_entry.grid(row=0, column=1, padx=5)
batch_frame.pack_forget()

# Reporting Interval
interval_frame = ctk.CTkFrame(controls_frame)
interval_frame.pack(side="left", padx=10)

ctk.CTkLabel(interval_frame, text="Interval (s):").grid(row=0, column=0, padx=5)

interval_var = ctk.StringVar(value="1")

interval_menu = ctk.CTkOptionMenu(
    interval_frame,
    values=["1", "5", "30"],
    variable=interval_var
)
interval_menu.grid(row=0, column=1, padx=5)

# Run test button
run_button = ctk.CTkButton(
    controls_frame,
    text="RUN TEST",
    font=ctk.CTkFont(size=18, weight="bold"),
    width=220,
    height=50,
    corner_radius=12,
    command=run_test
)
run_button.pack(side="right", padx=20)

# Log Box 
log_frame = ctk.CTkFrame(root)
log_frame.pack(fill="both", expand=True, padx=12, pady=12)

log_box = ctk.CTkTextbox(log_frame, wrap="none", font=("Consolas", 11))
log_box.pack(side="left", fill="both", expand=True)

scroll = ctk.CTkScrollbar(log_frame, orientation="vertical", command=log_box.yview)
log_box.configure(yscrollcommand=scroll.set)
scroll.pack(side="right", fill="y")

log_box.insert("end", "Logs will appear here...\n")
log_box.configure(state="disabled")

# Start GUI
root.mainloop()
