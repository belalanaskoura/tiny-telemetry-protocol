import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import sys
import socket
import threading
import pandas as pd
from tabulate import tabulate

# ------------------ Path Setup for .exe ------------------
# Determine the base path depending on whether we are running as a PyInstaller exe or normal script
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # Temporary folder created by PyInstaller
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# Paths for CSV and Baseline.py
csv_path = os.path.join(base_path, "../Server/sensor_data.csv")  # Adjust relative to exe
baseline_path = os.path.join(base_path, "Baseline.py")          # Baseline.py must be here

# ------------------ Utility Functions ------------------

def get_lan_ip():
    """Get LAN IP address automatically."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def show_csv_content():
    """Read and display the CSV file after the process ends in a pretty table."""
    if not os.path.exists(csv_path):
        return  # Skip if CSV missing

    try:
        df = pd.read_csv(csv_path)

        # Convert timestamp and arrival_time to human-readable format
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        if 'arrival_time' in df.columns:
            df['arrival_time'] = pd.to_datetime(df['arrival_time'], unit='s')

        # Pretty table for logs
        pretty_table = tabulate(df, headers='keys', tablefmt='grid', showindex=False)
        log_box.configure(state="normal")
        log_box.insert("end", "\n" + pretty_table + "\n")
        log_box.configure(state="disabled")
    except Exception as e:
        log_box.configure(state="normal")
        log_box.insert("end", f"\n[Error reading CSV: {e}]\n")
        log_box.configure(state="disabled")

def stream_process_output(process):
    """Stream live process output from Baseline.py to GUI log box."""
    def reader():
        for line in iter(process.stdout.readline, ''):
            if line:
                log_box.configure(state="normal")
                log_box.insert("end", line)
                log_box.see("end")
                log_box.configure(state="disabled")
        process.stdout.close()
        process.wait()
        # Mark baseline as finished
        log_box.configure(state="normal")
        log_box.insert("end", "\n--- Baseline Completed ---\n")
        log_box.configure(state="disabled")
        show_csv_content()  # Display CSV once after process finishes
    threading.Thread(target=reader, daemon=True).start()

def run_baseline_thread(ip, duration):
    """Run Baseline.py and stream all console output."""
    if not os.path.exists(baseline_path):
        log_box.configure(state="normal")
        log_box.insert("end", f"Error: Baseline.py not found at {baseline_path}\n")
        log_box.configure(state="disabled")
        return

    log_box.configure(state="normal")
    log_box.delete("1.0", "end")
    log_box.insert("end", f"Starting Baseline for {duration}s on server {ip}...\n\n")
    log_box.configure(state="disabled")

    cmd = [sys.executable, "-u", baseline_path, ip, duration]
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        stream_process_output(process)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def run_baseline():
    """Triggered by Run button — validates input then starts thread."""
    ip = ip_entry.get().strip() or get_lan_ip()
    duration = duration_entry.get().strip()

    if not duration.isdigit():
        messagebox.showerror("Invalid Input", "Run duration must be a number.")
        return

    threading.Thread(target=run_baseline_thread, args=(ip, duration), daemon=True).start()


# ------------------ GUI Setup ------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Tiny Telemetry Protocol v1")
root.geometry("1000x700")  # Bigger window for wide tables

# Title label
title_label = ctk.CTkLabel(
    root, text="Baseline Automation Test",
    font=ctk.CTkFont(size=22, weight="bold")
)
title_label.pack(pady=(20, 10))

# IP Input
ip_frame = ctk.CTkFrame(root)
ip_frame.pack(pady=10)
ctk.CTkLabel(ip_frame, text="Server IP:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
ip_entry = ctk.CTkEntry(ip_frame, width=300, placeholder_text="Leave empty for LAN IP")
ip_entry.insert(0, get_lan_ip())
ip_entry.grid(row=0, column=1, padx=5)

# Duration Input
duration_frame = ctk.CTkFrame(root)
duration_frame.pack(pady=10)
ctk.CTkLabel(duration_frame, text="Run Duration (seconds):", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
duration_entry = ctk.CTkEntry(duration_frame, width=100)
duration_entry.insert(0, "60")
duration_entry.grid(row=0, column=1, padx=5)

# Run Button
run_button = ctk.CTkButton(
    root, text="Run Baseline",
    font=ctk.CTkFont(size=15, weight="bold"),
    width=160, height=40,
    command=run_baseline
)
run_button.pack(pady=15)

# Log Box with Scrollbars
log_frame = ctk.CTkFrame(root)
log_frame.pack(padx=20, pady=10, fill="both", expand=True)

log_box = ctk.CTkTextbox(log_frame, font=("Consolas", 11), wrap="none")
log_box.pack(side="left", fill="both", expand=True)

# Vertical scrollbar
v_scroll = ctk.CTkScrollbar(log_frame, orientation="vertical", command=log_box.yview)
log_box.configure(yscrollcommand=v_scroll.set)
v_scroll.pack(side="right", fill="y")

# Horizontal scrollbar
h_scroll = ctk.CTkScrollbar(root, orientation="horizontal", command=log_box.xview)
log_box.configure(xscrollcommand=h_scroll.set)
h_scroll.pack(fill="x", padx=20)

# Initial log message
log_box.insert("end", "Logs will appear here...\n")
log_box.configure(state="disabled")

# Footer
footer = ctk.CTkLabel(
    root,
    text="© 2025 TTP",
    font=ctk.CTkFont(size=12, slant="italic")
)
footer.pack(pady=5)

root.mainloop()
