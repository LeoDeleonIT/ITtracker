"""
emailer.py — Send alert emails via SMTP (Gmail, Outlook, or any SMTP server)
"""

import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def load_users(users_file: str = "users.json") -> list:
    """Load the list of alert recipients from users.json."""
    if not os.path.exists(users_file):
        return []
    with open(users_file, "r") as f:
        data = json.load(f)
    return data.get("users", [])


def add_user(name: str, email: str, users_file: str = "users.json"):
    """Add a user to the alert list."""
    users = {"users": load_users(users_file)}
    # Prevent duplicates
    for u in users["users"]:
        if u["email"].lower() == email.lower():
            print(f"  [!] {email} is already in the list.")
            return
    users["users"].append({"name": name, "email": email, "active": True})
    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)
    print(f"  [+] Added {name} <{email}> to alert list.")


def remove_user(email: str, users_file: str = "users.json"):
    """Remove a user from the alert list by email."""
    data = {"users": load_users(users_file)}
    before = len(data["users"])
    data["users"] = [u for u in data["users"] if u["email"].lower() != email.lower()]
    if len(data["users"]) < before:
        with open(users_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  [-] Removed {email} from alert list.")
    else:
        print(f"  [!] {email} not found in alert list.")


def build_down_email(target_name: str, details: dict) -> tuple:
    """Build the subject and HTML body for a DOWN alert."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"🚨 ALERT: {target_name} is DOWN"
    body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;">
      <div style="border-left:4px solid #e74c3c;padding:10px 20px;background:#fdf3f2;">
        <h2 style="color:#e74c3c;">⚠️ Server Down Alert</h2>
        <p><strong>Target:</strong> {target_name}</p>
        <p><strong>Time:</strong> {now}</p>
        <p><strong>Method:</strong> {details.get('method','N/A').upper()}</p>
        <p><strong>Details:</strong> {details}</p>
        <p style="color:#888;font-size:12px;">Sent by ServerMonitor — monitoring your infrastructure.</p>
      </div>
    </body></html>
    """
    return subject, body


def build_up_email(target_name: str, downtime_seconds: float) -> tuple:
    """Build the subject and HTML body for a RECOVERY alert."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    minutes = int(downtime_seconds // 60)
    seconds = int(downtime_seconds % 60)
    subject = f"✅ RESOLVED: {target_name} is back ONLINE"
    body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;">
      <div style="border-left:4px solid #2ecc71;padding:10px 20px;background:#f2fdf6;">
        <h2 style="color:#27ae60;">✅ Server Recovered</h2>
        <p><strong>Target:</strong> {target_name}</p>
        <p><strong>Recovered at:</strong> {now}</p>
        <p><strong>Total downtime:</strong> {minutes}m {seconds}s</p>
        <p style="color:#888;font-size:12px;">Sent by ServerMonitor.</p>
      </div>
    </body></html>
    """
    return subject, body


def send_alerts(subject: str, html_body: str, smtp_config: dict, users_file: str = "users.json"):
    """Send an email to all active users in the list."""
    users = [u for u in load_users(users_file) if u.get("active", True)]
    if not users:
        print("  [!] No users to alert.")
        return

    sender = smtp_config["sender_email"]

    try:
        if smtp_config.get("use_ssl", True):
            server = smtplib.SMTP_SSL(smtp_config["smtp_host"], smtp_config["smtp_port"], timeout=10)
        else:
            server = smtplib.SMTP(smtp_config["smtp_host"], smtp_config["smtp_port"], timeout=10)
            server.starttls()

        server.login(smtp_config["sender_email"], smtp_config["sender_password"])

        sent_count = 0
        for user in users:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"ServerMonitor <{sender}>"
            msg["To"] = user["email"]
            msg.attach(MIMEText(html_body, "html"))
            try:
                server.sendmail(sender, user["email"], msg.as_string())
                print(f"  [✓] Alert sent to {user['name']} <{user['email']}>")
                sent_count += 1
            except Exception as e:
                print(f"  [✗] Failed to send to {user['email']}: {e}")

        server.quit()
        print(f"  [i] {sent_count}/{len(users)} alerts sent.")

    except smtplib.SMTPAuthenticationError:
        print("  [✗] SMTP authentication failed. Check your email/password in config.json.")
    except Exception as e:
        print(f"  [✗] SMTP error: {e}")
