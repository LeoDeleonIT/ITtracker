"""
monitor.py — Main monitoring loop
Run with:  python monitor.py
Manage users:
  python monitor.py --add-user "Alice" alice@example.com
  python monitor.py --remove-user alice@example.com
  python monitor.py --list-users
"""

import json
import time
import os
import sys
import argparse
from datetime import datetime

from checker import check_target
from emailer import send_alerts, add_user, remove_user, load_users, build_down_email, build_up_email

CONFIG_FILE = "config.json"
LOG_FILE = "monitor.log"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_config(path: str = CONFIG_FILE) -> dict:
    if not os.path.exists(path):
        print(f"[!] Config file '{path}' not found. Creating default...")
        create_default_config(path)
    with open(path, "r") as f:
        return json.load(f)


def create_default_config(path: str):
    default = {
        "check_interval_seconds": 60,
        "alert_after_failures": 2,
        "smtp": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 465,
            "use_ssl": True,
            "sender_email": "your_email@gmail.com",
            "sender_password": "your_app_password_here"
        },
        "targets": [
            {
                "name": "Google DNS",
                "method": "ping",
                "host": "8.8.8.8"
            },
            {
                "name": "Example Website",
                "method": "http",
                "url": "https://example.com"
            },
            {
                "name": "Local Device Port 80",
                "method": "tcp",
                "host": "192.168.1.1",
                "port": 80
            }
        ]
    }
    with open(path, "w") as f:
        json.dump(default, f, indent=2)
    print(f"[+] Default config created at '{path}'. Edit it before running the monitor.")


def log(message: str):
    """Write timestamped message to console and log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def status_symbol(online: bool) -> str:
    return "[ONLINE] " if online else "[OFFLINE]"


# ─── Main Monitor Loop ────────────────────────────────────────────────────────

def run_monitor():
    config = load_config()
    smtp_config = config["smtp"]
    targets = config["targets"]
    interval = config.get("check_interval_seconds", 60)
    alert_threshold = config.get("alert_after_failures", 2)

    # Track state per target: {"failures": 0, "alerted": False, "down_since": None}
    state = {t["name"]: {"failures": 0, "alerted": False, "down_since": None} for t in targets}

    log(f"Server Monitor started. Checking {len(targets)} target(s) every {interval}s.")
    log(f"Alert threshold: {alert_threshold} consecutive failure(s) before email.")

    while True:
        log("-" * 60)
        for target in targets:
            result = check_target(target)
            name = result["name"]
            online = result["online"]

            log(f"  {status_symbol(online)} {name}  [{result.get('method','?').upper()}]")

            s = state[name]

            if online:
                # Recovery — was previously alerted
                if s["alerted"] and s["down_since"] is not None:
                    downtime = time.time() - s["down_since"]
                    log(f"  >> {name} RECOVERED after {int(downtime)}s. Sending recovery alert...")
                    subject, body = build_up_email(name, downtime)
                    send_alerts(subject, body, smtp_config)
                # Reset state
                s["failures"] = 0
                s["alerted"] = False
                s["down_since"] = None

            else:
                s["failures"] += 1
                log(f"  >> Failure #{s['failures']} for {name}")

                if s["down_since"] is None:
                    s["down_since"] = time.time()

                # Send alert only once per outage, after threshold is reached
                if s["failures"] >= alert_threshold and not s["alerted"]:
                    log(f"  >> Threshold reached! Sending DOWN alert for {name}...")
                    subject, body = build_down_email(name, result)
                    send_alerts(subject, body, smtp_config)
                    s["alerted"] = True

        log(f"Next check in {interval} seconds...")
        time.sleep(interval)


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Server Monitor")
    parser.add_argument("--add-user", nargs=2, metavar=("NAME", "EMAIL"), help="Add an alert recipient")
    parser.add_argument("--remove-user", metavar="EMAIL", help="Remove an alert recipient")
    parser.add_argument("--list-users", action="store_true", help="List all alert recipients")
    parser.add_argument("--test-alert", action="store_true", help="Send a test alert to all users")
    parser.add_argument("--check-once", action="store_true", help="Run checks once and exit (no loop)")
    args = parser.parse_args()

    if args.add_user:
        name, email = args.add_user
        add_user(name, email)
        return

    if args.remove_user:
        remove_user(args.remove_user)
        return

    if args.list_users:
        users = load_users()
        if not users:
            print("No users registered.")
        else:
            print(f"\n{'#':<4} {'Name':<20} {'Email':<30} {'Active'}")
            print("-" * 60)
            for i, u in enumerate(users, 1):
                print(f"{i:<4} {u['name']:<20} {u['email']:<30} {u.get('active', True)}")
        return

    if args.test_alert:
        config = load_config()
        subject = "🔔 Test Alert from ServerMonitor"
        body = "<html><body><h2>This is a test alert.</h2><p>Your monitoring setup is working correctly.</p></body></html>"
        send_alerts(subject, body, config["smtp"])
        return

    if args.check_once:
        config = load_config()
        print(f"\nRunning one-time check on {len(config['targets'])} target(s)...\n")
        for target in config["targets"]:
            result = check_target(target)
            symbol = status_symbol(result["online"])
            print(f"  {symbol} {result['name']}  |  {result}")
        return

    # Default: run the continuous monitor
    try:
        run_monitor()
    except KeyboardInterrupt:
        log("Monitor stopped by user (Ctrl+C).")


if __name__ == "__main__":
    main()
