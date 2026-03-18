"""
checker.py — Status check methods: ping, HTTP, TCP
"""

import socket
import urllib.request
import urllib.error
import subprocess
import platform
import time


def ping_check(host: str, timeout: int = 3) -> dict:
    """Send ICMP ping to host. Works on Windows and Linux."""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "1", "-w", str(timeout * 1000 if platform.system().lower() == "windows" else timeout), host]
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 2)
        online = result.returncode == 0
    except subprocess.TimeoutExpired:
        online = False
    return {"method": "ping", "host": host, "online": online}


def tcp_check(host: str, port: int, timeout: int = 3) -> dict:
    """Try to open a TCP connection to host:port."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        online = True
    except (socket.timeout, ConnectionRefusedError, OSError):
        online = False
    return {"method": "tcp", "host": host, "port": port, "online": online}


def http_check(url: str, timeout: int = 5, expected_status: int = 200) -> dict:
    """Send an HTTP GET request and check the status code."""
    if not url.startswith("http"):
        url = "http://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ServerMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.getcode()
            online = (status == expected_status)
            return {"method": "http", "url": url, "online": online, "status_code": status}
    except urllib.error.HTTPError as e:
        return {"method": "http", "url": url, "online": False, "status_code": e.code}
    except Exception as e:
        return {"method": "http", "url": url, "online": False, "error": str(e)}


def check_target(target: dict) -> dict:
    """
    Check a single target using the method defined in its config.
    Target example:
      {"name": "My Server", "method": "ping", "host": "192.168.1.1"}
      {"name": "Web App",   "method": "http",  "url": "https://example.com"}
      {"name": "DB Port",   "method": "tcp",   "host": "192.168.1.1", "port": 5432}
    """
    method = target.get("method", "ping").lower()
    result = {"name": target.get("name", target.get("host", "Unknown")), "timestamp": time.time()}

    if method == "ping":
        result.update(ping_check(target["host"], target.get("timeout", 3)))
    elif method == "http":
        result.update(http_check(target["url"], target.get("timeout", 5)))
    elif method == "tcp":
        result.update(tcp_check(target["host"], target["port"], target.get("timeout", 3)))
    else:
        result.update({"online": False, "error": f"Unknown method: {method}"})

    return result
