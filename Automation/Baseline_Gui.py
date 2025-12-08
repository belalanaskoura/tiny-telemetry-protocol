import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import sys
import socket
import threading
import pandas as pd
from tabulate import tabulate

# Path setup
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

csv_path = os.path.join(base_path, "../Server/sensor_data.csv")
baseline_path = os.path.join(base_path, "Baseline.py")


# Utility
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
            df['arrival_time'] = pd.to_datetime(df['arrival_time'], unit='s')

        table = tabulate(df, headers='keys', tablefmt='grid', showindex=False)
        log_box.configure(state="normal")
        log_box.insert("end", "\n" + table + "\n")
        log_box.configure(state="disabled")
    except Exception as e:
        log_box.configure(state="normal")
        log_box.insert("end", f"\nError reading CSV: {e}\n")
        log_box.configure(state="disabled")


def stream_process_output(process):
    def reader():
        for line in iter(process.stdout.readline, ''):
            if line:
                log_box.configure(state="normal")
                log_box.insert("end", line)
                log_box.see("end")
                log_box.configure(state="disabled")
        process.wait()
        log_box.configure(state="normal")
        log_box.insert("end", "\n--- Baseline Completed ---\n")
        log_box.configure(state="disabled")
        show_csv_content()
    threading.Thread(target=reader, daemon=True).start()


def run_baseline_thread(ip, duration, batch_size):
    log_box.configure(state="normal")
    log_box.delete("1.0", "end")
    log_box.insert(
        "end",
        f"Starting Baseline for {duration}s on server {ip} (Batch size: {batch_size})...\n\n"
    )
    log_box.configure(state="disabled")

    cmd = [sys.executable, "-u", baseline_path, ip, str(duration), str(batch_size)]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    stream_process_output(process)


def run_baseline():
    ip = ip_entry.get().strip() or get_lan_ip()
    duration = duration_entry.get().strip()
    batch_size = batch_entry.get().strip()

    if not duration.isdigit() or not batch_size.isdigit():
        messagebox.showerror("Invalid Input", "Duration and batch size must be numbers.")
        return

    duration = int(duration)
    batch_size = int(batch_size)

    if batch_size < 1:
        messagebox.showerror("Invalid Batch Size", "Batch size must be at least 1.")
        return

    if batch_size > duration:
        messagebox.showerror(
            "Invalid Batch Size",
            "Batch size cannot be greater than run duration."
        )
        return

    threading.Thread(
        target=run_baseline_thread,
        args=(ip, duration, batch_size),
        daemon=True
    ).start()


# GUI setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Tiny Telemetry Protocol v1")
root.geometry("1000x700")

title_label = ctk.CTkLabel(
    root,
    text="Baseline Automation Test",
    font=ctk.CTkFont(size=22, weight="bold")
)
title_label.pack(pady=(20, 10))


# Server IP
ip_frame = ctk.CTkFrame(root)
ip_frame.pack(pady=10)
ctk.CTkLabel(ip_frame, text="Server IP:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
ip_entry = ctk.CTkEntry(ip_frame, width=300)
ip_entry.insert(0, get_lan_ip())
ip_entry.grid(row=0, column=1, padx=5)


# Duration
duration_frame = ctk.CTkFrame(root)
duration_frame.pack(pady=10)
ctk.CTkLabel(duration_frame, text="Run Duration (seconds):", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
duration_entry = ctk.CTkEntry(duration_frame, width=100)
duration_entry.insert(0, "60")
duration_entry.grid(row=0, column=1, padx=5)


# Batch Size
batch_frame = ctk.CTkFrame(root)
batch_frame.pack(pady=10)
ctk.CTkLabel(
    batch_frame,
    text="Batch Size (1 = no batching):",
    font=ctk.CTkFont(size=14)
).grid(row=0, column=0, padx=5)
batch_entry = ctk.CTkEntry(batch_frame, width=100)
batch_entry.insert(0, "1")
batch_entry.grid(row=0, column=1, padx=5)


# Run Button
run_button = ctk.CTkButton(
    root,
    text="Run Baseline",
    font=ctk.CTkFont(size=15, weight="bold"),
    width=160,
    height=40,
    command=run_baseline
)
run_button.pack(pady=20)


# Log box
log_frame = ctk.CTkFrame(root)
log_frame.pack(padx=20, pady=10, fill="both", expand=True)

log_box = ctk.CTkTextbox(log_frame, font=("Consolas", 11), wrap="none")
log_box.pack(side="left", fill="both", expand=True)

v_scroll = ctk.CTkScrollbar(log_frame, orientation="vertical", command=log_box.yview)
log_box.configure(yscrollcommand=v_scroll.set)
v_scroll.pack(side="right", fill="y")

h_scroll = ctk.CTkScrollbar(root, orientation="horizontal", command=log_box.xview)
log_box.configure(xscrollcommand=h_scroll.set)
h_scroll.pack(fill="x", padx=20)

log_box.insert("end", "Logs will appear here...\n")
log_box.configure(state="disabled")

root.mainloop()
