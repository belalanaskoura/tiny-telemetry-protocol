import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import sys
import socket
import threading
import pandas as pd
from tabulate import tabulate

# ------------------ Utility Functions ------------------

# Get the local network IP of the machine
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS to detect LAN IP
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except:
        return "127.0.0.1"

# Display the sensor CSV in the log box in a formatted table
def display_sensor_csv():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_directory)
    csv_file_path = os.path.join(repo_root, "Server", "sensor_data.csv")

    # Exit if CSV does not exist
    if not os.path.exists(csv_file_path):
        return

    try:
        # Read CSV into a DataFrame
        df = pd.read_csv(csv_file_path)

        # Convert timestamps to human-readable format
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        if 'arrival_time' in df.columns:
            df['arrival_time'] = pd.to_datetime(df['arrival_time'], unit='s')

        # Format DataFrame into a professional-looking table
        formatted_table = tabulate(df, headers='keys', tablefmt='grid', showindex=False)
        log_textbox.configure(state="normal")
        log_textbox.insert("end", "\n" + formatted_table + "\n")
        log_textbox.configure(state="disabled")

    except Exception as e:
        # Display error if CSV cannot be read
        log_textbox.configure(state="normal")
        log_textbox.insert("end", f"\n[Error reading CSV: {e}]\n")
        log_textbox.configure(state="disabled")

# Stream the output of a subprocess into the log box
def stream_subprocess_output(process):
    def output_reader():
        for line in iter(process.stdout.readline, ''):
            if line:
                log_textbox.configure(state="normal")
                log_textbox.insert("end", line)
                log_textbox.see("end")
                log_textbox.configure(state="disabled")
        process.stdout.close()
        process.wait()

        # Indicate baseline process completion
        log_textbox.configure(state="normal")
        log_textbox.insert("end", "\n--- Baseline Process Completed ---\n")
        log_textbox.configure(state="disabled")

        # Display the sensor CSV
        display_sensor_csv()

    # Run reader in a separate daemon thread
    threading.Thread(target=output_reader, daemon=True).start()

# Execute the baseline process in a background thread
def execute_baseline_process(server_ip, run_duration):
    script_directory = os.path.dirname(os.path.abspath(__file__))
    baseline_script_path = os.path.join(script_directory, "Baseline.py")

    # Check if Baseline.py exists
    if not os.path.exists(baseline_script_path):
        log_textbox.configure(state="normal")
        log_textbox.insert("end", f"Error: Baseline.py not found in {script_directory}\n")
        log_textbox.configure(state="disabled")
        return

    # Clear previous logs and display start message
    log_textbox.configure(state="normal")
    log_textbox.delete("1.0", "end")
    log_textbox.insert("end", f"Starting baseline for {run_duration}s on server {server_ip}...\n\n")
    log_textbox.configure(state="disabled")

    # Build subprocess command
    command = [sys.executable, "-u", baseline_script_path, server_ip, run_duration]

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        stream_subprocess_output(process)
    except Exception as e:
        messagebox.showerror("Execution Error", str(e))

# Handler for Run button click
def on_run_button_click():
    server_ip = ip_entry.get().strip() or get_local_ip()
    run_duration = duration_entry.get().strip()

    if not run_duration.isdigit():
        messagebox.showerror("Invalid Input", "Run duration must be a numeric value.")
        return

    # Run baseline in a background thread
    threading.Thread(target=execute_baseline_process, args=(server_ip, run_duration), daemon=True).start()

# ------------------ GUI Setup ------------------

# Configure CTk appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Main window configuration
root = ctk.CTk()
root.title("Tiny Telemetry Protocol v1")
root.geometry("1000x700")  # Larger window for wide tables

# Title label
title_label = ctk.CTkLabel(
    root,
    text="Baseline Automation Dashboard",
    font=ctk.CTkFont(size=22, weight="bold")
)
title_label.pack(pady=(20, 10))

# Server IP input frame
ip_frame = ctk.CTkFrame(root)
ip_frame.pack(pady=10)
ctk.CTkLabel(ip_frame, text="Server IP:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
ip_entry = ctk.CTkEntry(ip_frame, width=300, placeholder_text="Leave empty for LAN IP")
ip_entry.insert(0, get_local_ip())
ip_entry.grid(row=0, column=1, padx=5)

# Run duration input frame
duration_frame = ctk.CTkFrame(root)
duration_frame.pack(pady=10)
ctk.CTkLabel(duration_frame, text="Run Duration (seconds):", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5)
duration_entry = ctk.CTkEntry(duration_frame, width=100)
duration_entry.insert(0, "60")
duration_entry.grid(row=0, column=1, padx=5)

# Run button
run_button = ctk.CTkButton(
    root,
    text="Run Baseline",
    font=ctk.CTkFont(size=15, weight="bold"),
    width=160,
    height=40,
    command=on_run_button_click
)
run_button.pack(pady=15)

# Log box frame
log_frame = ctk.CTkFrame(root)
log_frame.pack(padx=20, pady=10, fill="both", expand=True)

# Log textbox for live output
log_textbox = ctk.CTkTextbox(log_frame, font=("Consolas", 11), wrap="none")
log_textbox.pack(side="left", fill="both", expand=True)

# Vertical scrollbar for log box
vertical_scroll = ctk.CTkScrollbar(log_frame, orientation="vertical", command=log_textbox.yview)
log_textbox.configure(yscrollcommand=vertical_scroll.set)
vertical_scroll.pack(side="right", fill="y")

# Horizontal scrollbar for wide tables
horizontal_scroll = ctk.CTkScrollbar(root, orientation="horizontal", command=log_textbox.xview)
log_textbox.configure(xscrollcommand=horizontal_scroll.set)
horizontal_scroll.pack(fill="x", padx=20)

# Initial placeholder text in log box
log_textbox.insert("end", "Logs will appear here...\n")
log_textbox.configure(state="disabled")

# Footer label
footer_label = ctk.CTkLabel(
    root,
    text="© 2025 Tiny Telemetry Protocol",
    font=ctk.CTkFont(size=12, slant="italic")
)
footer_label.pack(pady=5)

# Start the main GUI loop
root.mainloop()
