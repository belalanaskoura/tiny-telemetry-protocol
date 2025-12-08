import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import sys
import socket
import threading
import pandas as pd
from tabulate import tabulate

# ------------------ Path Setup ------------------
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

csv_path = os.path.join(base_path, "../sensor_data.csv")
test_runner_path = os.path.join(base_path, "TestRunner.py")


# ------------------ Utility Functions ------------------
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
        log_box.insert("end", "\n--- Test Completed ---\n")
        log_box.configure(state="disabled")
        show_csv_content()
    threading.Thread(target=reader, daemon=True).start()


# ------------------ Recommendation Logic ------------------
def recommend_batch_size(duration):
    return max(1, min(duration // 5, 10))


def update_batch_recommendation(event=None):
    if not batching_enabled.get():
        return
    if test_type.get() != "Custom Test":
        return

    duration_text = duration_entry.get().strip()
    if not duration_text.isdigit():
        return

    duration = int(duration_text)
    recommended = recommend_batch_size(duration)

    batch_entry.delete(0, "end")
    batch_entry.insert(0, str(recommended))


# ------------------ Test Switching Logic ------------------
def force_custom_test():
    # If currently baseline, switch to Custom and update UI
    if test_type.get() != "Custom Test":
        test_type.set("Custom Test")
        on_test_type_change()


# ------------------ Run Button Logic ------------------
def run_test():
    ip = ip_entry.get().strip() or get_lan_ip()

    # BASELINE TEST: fixed 60s, no batching
    if test_type.get() == "Baseline Test (60s, no batching)":
        duration = 60
        batch_size = 0

    # CUSTOM TEST
    else:
        duration_text = duration_entry.get().strip()

        if not duration_text.isdigit():
            messagebox.showerror("Invalid Input", "Run duration must be a number.")
            return

        duration = int(duration_text)

        if not batching_enabled.get():
            batch_size = 0
        else:
            batch_text = batch_entry.get().strip()

            if not batch_text.isdigit():
                messagebox.showerror("Invalid Input", "Batch size must be a number.")
                return

            batch_size = int(batch_text)

            if batch_size < 1 or batch_size > duration:
                messagebox.showerror(
                    "Invalid Batch Size",
                    "Batch size must be between 1 and run duration."
                )
                return

    threading.Thread(
        target=run_test_thread,
        args=(ip, duration, batch_size),
        daemon=True
    ).start()


def run_test_thread(ip, duration, batch_size):
    log_box.configure(state="normal")
    log_box.delete("1.0", "end")
    log_box.insert(
        "end",
        f"Starting test for {duration}s on server {ip} "
        f"(Batching {'Enabled' if batch_size > 0 else 'Disabled'})...\n\n"
    )
    log_box.configure(state="disabled")

    cmd = [sys.executable, "-u", test_runner_path, ip, str(duration), str(batch_size)]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    stream_process_output(process)


# ------------------ GUI Setup ------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Tiny Telemetry Protocol v1")
root.geometry("1000x700")


# Title
ctk.CTkLabel(
    root,
    text="Tiny Telemetry Protocol",
    font=ctk.CTkFont(size=22, weight="bold")
).pack(pady=(20, 10))


# ------------------ CONTROL PANEL ------------------
controls_frame = ctk.CTkFrame(root)
controls_frame.pack(pady=10, fill="x")


# Test Type Selector
test_type = ctk.StringVar(value="Baseline Test (60s, no batching)")

def on_test_type_change():
    # When switching modes, just handle batching visibility and state.
    # We do NOT disable the duration field so typing can auto-switch to custom.
    if test_type.get() == "Baseline Test (60s, no batching)":
        batching_enabled.set(False)
        batch_frame.pack_forget()
        batch_entry.delete(0, "end")
        batch_entry.insert(0, "0")
        # Optionally reset duration to 60 for clarity (fields are ignored in baseline anyway)
        # duration_entry.delete(0, "end")
        # duration_entry.insert(0, "60")
    else:
        # Custom Test: allow full control; nothing to auto-reset here
        pass

test_menu = ctk.CTkOptionMenu(
    controls_frame,
    values=["Baseline Test (60s, no batching)", "Custom Test"],
    variable=test_type,
    command=lambda _: on_test_type_change()
)
test_menu.pack(pady=5)


# Server IP
ip_frame = ctk.CTkFrame(controls_frame)
ip_frame.pack(pady=5)
ctk.CTkLabel(ip_frame, text="Server IP:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
ip_entry = ctk.CTkEntry(ip_frame, width=300)
ip_entry.insert(0, get_lan_ip())
ip_entry.grid(row=0, column=1, padx=5)


# Duration
duration_frame = ctk.CTkFrame(controls_frame)
duration_frame.pack(pady=5)
ctk.CTkLabel(duration_frame, text="Run Duration (seconds):", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
duration_entry = ctk.CTkEntry(duration_frame, width=100)
duration_entry.insert(0, "60")
duration_entry.grid(row=0, column=1, padx=5)

# If user tries to type seconds while in Baseline → auto-switch to Custom
duration_entry.bind("<KeyPress>", lambda e: force_custom_test())
duration_entry.bind("<KeyRelease>", update_batch_recommendation)


# Enable batching checkbox
batching_enabled = ctk.BooleanVar(value=False)

def toggle_batching():
    # If user enables batching while in Baseline mode → switch to Custom automatically
    if test_type.get() != "Custom Test":
        force_custom_test()

    if batching_enabled.get():
        batch_frame.pack(pady=5)
        update_batch_recommendation()
    else:
        batch_frame.pack_forget()
        batch_entry.delete(0, "end")
        batch_entry.insert(0, "0")


batch_check = ctk.CTkCheckBox(
    controls_frame,
    text="Enable Batching",
    variable=batching_enabled,
    command=toggle_batching
)
batch_check.pack(pady=5)


# Batch size frame
batch_frame = ctk.CTkFrame(controls_frame)
ctk.CTkLabel(batch_frame, text="Batch Size:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
batch_entry = ctk.CTkEntry(batch_frame, width=100)
batch_entry.insert(0, "0")
batch_entry.grid(row=0, column=1, padx=5)
batch_frame.pack_forget()


# Run button
ctk.CTkButton(
    root,
    text="Run Test",
    font=ctk.CTkFont(size=15, weight="bold"),
    width=160,
    height=40,
    command=run_test
).pack(pady=15)


# ------------------ LOG TERMINAL ------------------
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

# Initialize UI state
on_test_type_change()

root.mainloop()
