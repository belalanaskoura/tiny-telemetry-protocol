# 📡 Tiny Telemetry Protocol v1 (TTPv1)
A lightweight UDP-based telemetry system that simulates a client device sending temperature readings to a server.  
Includes automated Linux NetEm testing for delay, jitter, and packet loss evaluation.

---

### 📁 Project Structure

- **Automation/** – GUI & experiment orchestrator  
  - `Application.py`  
  - `TestRunner.py`  

- **Client/** – Telemetry client implementation  
  - `Client.py`

- **Server/** – UDP telemetry server  
  - `Server.py`

- **Documents/** – Project documentation  
  - **Reports/**  
    - `Project Proposal.pdf`  
    - `RFC.pdf`

- **Tests/** – Automated NetEm tests  
  - `run_test.sh`  
  - `run_all_tests.sh`  
  - **results/** (auto-generated; each folder contains CSV, analysis, logs, pcap)  
    - `baseline_<timestamp>/`  
    - `loss5_<timestamp>/`  
    - `delay100_<timestamp>/`  

- `analyze_loss.py` – Automated CSV analysis tool  
- `requirements.txt` – Python dependencies  
- `sensor_data.csv` – Latest CSV output  
- `README.md` – Project documentation

---

# 📘 System Overview

## **Application.py**
Graphical UI to run experiments, stream logs, and display CSV results.

## **TestRunner.py**
Automation layer that:
- Starts server  
- Starts client(s)  
- Streams logs  
- Runs selected experiment  

## **Client.py**
Simulated telemetry device:
- Sends temperature data over UDP  
- Includes checksums, sequence numbers, batching, and heartbeats  
- Uses **relative millisecond timestamps** for accurate delay testing  

## **Server.py**
Receives telemetry packets:
- Validates checksums  
- Detects duplicates and gaps  
- Logs data to CSV  
- Computes arrival timestamps  

---

# 🧪 Supported GUI Tests

## **Baseline Test (Fixed 60s)**
Reference experiment to measure:
- Natural latency  
- Sequence correctness  
- Inter-arrival stability  

## **Custom Test**
User may configure:
- Duration  
- Batch size  
- Number of clients  

---

# ⚙️ Features

- UDP-based telemetry protocol  
- Sequence numbers + gap detection  
- Duplicate detection  
- Heartbeats  
- Checksums  
- CSV telemetry logging  
- Automated NetEm tests  
- Wireshark packet captures  
- Works in Linux, WSL2, and Linux VMs  

---

# 📦 Installation

Requires **Python 3.10+**

```bash
pip install -r requirements.txt
```

(Optional) Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

---

# ▶️ Running the Project

## **GUI Version (Recommended)**

```bash
python Application.py
```

Then:
1. Select **Baseline** or **Custom Test**
2. Configure settings
3. Click **Run Test**

GUI will:
- Launch server + client  
- Stream logs  
- Display CSV output  

---

# 🖥️ CLI Version

```bash
python Automation/TestRunner.py <server_ip> <duration> <batch_size> <num_clients>
```

Example:

```bash
python Automation/TestRunner.py 127.0.0.1 60 0 1
```

---

# 🗂️ CSV Format

CSV saved at:

```
sensor_data.csv
```

| Column | Description |
|--------|-------------|
| `device_id` | Sensor device ID |
| `seq` | Packet sequence number |
| `timestamp` | Client timestamp (relative seconds) |
| `arrival_time` | Server timestamp (relative seconds) |
| `duplicate_flag` | 1 if duplicate packet |
| `gap_flag` | 1 if sequence gap |
| `data_value` | Temperature payload |

---

# 🌐 Network Impairment Tests (Automated with NetEm)

The project includes a fully automated pipeline for evaluating system performance under:

- Random packet loss  
- Delay injection  
- Jitter injection  

Located in:

```
Tests/run_test.sh
Tests/run_all_tests.sh
```

### ✔ Automatically:
- Applies NetEm rules  
- Runs TestRunner  
- Captures packets (pcap)  
- Saves CSV  
- Generates analysis report  
- Restores network state  

Each experiment is saved in:

```
tests/results/<testname_timestamp>/
```

Each experiment folder contains:

- `sensor_<test>.csv` — Telemetry log  
- `analysis_<test>.txt` — Automated delay/loss/jitter analysis  
- `test_output.log` — Combined client/server logs  
- `trace.pcap` — Packet capture for Wireshark  
- `netem_settings.txt` — Exact NetEm impairment applied  

---

# ⚠️ WSL2 Users — Important Note

WSL2 **does not support NetEm on eth0**.  
All impairment tests run on **loopback (`lo`)**, with:

```
--server_ip 127.0.0.1
```

WSL2 loopback adds ~350–500ms inherent latency.  
This is normal and expected.

NetEm jitter/delay/loss patterns remain valid.

---

# 🧪 Automated Tests Provided

## 1️⃣ Baseline Test

```bash
./run_test.sh baseline
```

NetEm rule:

```
noqueue (no impairment)
```

Measures:
- Reference delay  
- Natural inter-arrival jitter  
- Protocol stability  

---

## 2️⃣ Loss Test (5% Random Packet Loss)

```bash
./run_test.sh loss5
```

NetEm rule:

```
loss 5%
```

Evaluates:
- Packet survival  
- Duplicate detection  
- Gap detection  
- Robustness against loss  

---

## 3️⃣ Delay Test (100ms ± 10ms Jitter)

```bash
./run_test.sh delay100
```

NetEm rule:

```
delay 100ms 10ms
```

Evaluates:
- One-way delay  
- Real jitter  
- Inter-arrival delay  
- Reordering behavior  

WSL2 introduces an additional constant ~350ms delay, but jitter remains accurate.

---

# 🚀 Run All Tests at Once

```bash
./run_all_tests.sh
```

Produces:

- `baseline_<timestamp>/`
- `loss5_<timestamp>/`
- `delay100_<timestamp>/`

Each folder contains:
- CSV results  
- Packet capture (`trace.pcap`)  
- Raw logs  
- NetEm settings  
- Automated analysis file  

---

# 📊 Automated Analysis Output

Each test produces:

```
analysis_<test>.txt
```

Which includes:

- Total loss  
- Gaps detected  
- Duplicate packets  
- Average delay  
- Min/max delay  
- Jitter (stddev)  
- Inter-arrival jitter  
- Reordering detection  

Example:

```
Avg delay: 102.4 ms
Min delay: 90.2 ms
Max delay: 113.5 ms
Delay jitter: 9.8 ms
Reordering: NO
```

---

# 🕵️ Packet Capture (Wireshark)

Each test produces:

```
trace.pcap
```

Open in Wireshark to inspect:
- UDP timing  
- Sequence ordering  
- Loss patterns  
- Jitter behavior  

---

# 📝 Notes

- Server always starts before the client  
- Impairments are applied & removed automatically  
- Batching increases payload size but reduces packet frequency  
- Baseline test provides reference metrics for comparison  
