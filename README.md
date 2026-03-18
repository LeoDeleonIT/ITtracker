# Server Monitor

A lightweight Python server monitoring tool with email alerts and a web dashboard.

## Project Structure

```
server-monitor/
├── monitor.py        ← Main script (run this)
├── checker.py        ← Ping / HTTP / TCP check logic
├── emailer.py        ← Email alert sender + user management
├── dashboard.py      ← Web dashboard (Flask)
├── config.json       ← Your targets + SMTP settings
├── users.json        ← Alert recipients
└── monitor.log       ← Auto-generated log file
```

---

## Quick Setup

### 1. Install Python
Download from https://python.org (3.8+). Check "Add to PATH" during install.

### 2. Install dependencies
```
pip install flask
```

### 3. Configure `config.json`

Edit the SMTP section with your email credentials:

**For Gmail:**
- Enable 2-Step Verification on your Google account
- Go to https://myaccount.google.com/apppasswords
- Generate an App Password (16-char code)
- Use your Gmail as `sender_email` and the app password as `sender_password`

**For Outlook/Hotmail:**
```json
"smtp_host": "smtp-mail.outlook.com",
"smtp_port": 587,
"use_ssl": false
```

### 4. Add targets to `config.json`

Three check methods available:

**Ping (ICMP):**
```json
{ "name": "My Router", "method": "ping", "host": "192.168.1.1" }
```

**HTTP (web server):**
```json
{ "name": "My Website", "method": "http", "url": "https://mysite.com" }
```

**TCP (specific port):**
```json
{ "name": "SSH Server", "method": "tcp", "host": "192.168.1.100", "port": 22 }
```

---

## Usage

### Run the monitor
```
python monitor.py
```

### Manage alert recipients
```
python monitor.py --add-user "Alice" alice@example.com
python monitor.py --remove-user alice@example.com
python monitor.py --list-users
```

### Test your email setup
```
python monitor.py --test-alert
```

### Run a one-time check (no loop)
```
python monitor.py --check-once
```

### Launch the web dashboard
```
python dashboard.py
```
Then open http://localhost:5000 in your browser.

---

## Run as a Windows Service (always-on monitoring)

### Option A: Keep it simple with Task Scheduler
1. Open Task Scheduler
2. Create Basic Task → "Server Monitor"
3. Trigger: "When computer starts"
4. Action: Start a program → `python` → Arguments: `C:\Users\Trinity\Documents\server-monitor\monitor.py`
5. Check "Run whether user is logged on or not"

### Option B: NSSM (Non-Sucking Service Manager)
1. Download NSSM from https://nssm.cc
2. Run: `nssm install ServerMonitor`
3. Set Path to `python.exe`, Arguments to `monitor.py`, and Start Directory to the project folder

---

## Key Settings in `config.json`

| Setting | Default | Description |
|---|---|---|
| `check_interval_seconds` | 60 | How often to check targets |
| `alert_after_failures` | 2 | Consecutive failures before alerting |
