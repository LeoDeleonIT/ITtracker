"""
dashboard.py — TDC IT Asset Tracker + Live Server Monitor
Run with:  python dashboard.py
Visit:     http://localhost:5000
"""

import json
import os
import time
import urllib.request
from datetime import datetime
from flask import Flask, jsonify, Response
from checker import check_target

app = Flask(__name__)

CONFIG_FILE   = "config.json"
TRACKER_CACHE = "tracker_cache.html"
GITHUB_URL    = "https://raw.githubusercontent.com/majinist/tdc-it-asset-tracker/main/index.html"

# In-memory uptime history: {name: [{"time": ..., "online": bool}, ...]}
history   = {}
MAX_HIST  = 50


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return json.load(f)


def _calc_uptime(records: list) -> float:
    if not records:
        return 100.0
    up = sum(1 for r in records if r["online"])
    return round((up / len(records)) * 100, 1)


def get_latest_results() -> list:
    config  = load_config()
    results = []
    for target in config["targets"]:
        r    = check_target(target)
        name = r["name"]
        history.setdefault(name, []).append(
            {"time": datetime.now().strftime("%H:%M:%S"), "online": r["online"]}
        )
        if len(history[name]) > MAX_HIST:
            history[name].pop(0)
        r["uptime_pct"] = _calc_uptime(history.get(name, []))
        results.append(r)
    return results


def fetch_tracker_html() -> str:
    """Download the GitHub Pages tracker and cache it locally."""
    print("[*] Downloading tracker HTML from GitHub...")
    try:
        req = urllib.request.Request(
            GITHUB_URL,
            headers={"User-Agent": "TDC-Dashboard/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")
        with open(TRACKER_CACHE, "w", encoding="utf-8") as f:
            f.write(html)
        print("[+] Tracker HTML cached.")
        return html
    except Exception as e:
        print(f"[!] Could not fetch tracker HTML: {e}")
        if os.path.exists(TRACKER_CACHE):
            print("[*] Using existing cache.")
            with open(TRACKER_CACHE, encoding="utf-8") as f:
                return f.read()
        return "<h1>Could not load tracker. Check your connection.</h1>"


def build_page() -> str:
    """Return the tracker HTML with the live server-monitor script injected."""
    if os.path.exists(TRACKER_CACHE):
        with open(TRACKER_CACHE, encoding="utf-8") as f:
            html = f.read()
    else:
        html = fetch_tracker_html()

    inject = """
<!-- ═══════════════════════════════════════════════════════════════
     LIVE SERVER MONITOR — injected by dashboard.py
     Overrides the Servers tab to show real TCP-check results
     from the Flask backend at /api/status
════════════════════════════════════════════════════════════════ -->
<script>
(function () {
  'use strict';

  /* ── Config ─────────────────────────────────────────────────── */
  var API_URL      = '/api/status';
  var _interval    = null;
  var _intervalMs  = 30000;   // default 30 s
  var _lastResults = [];

  /* ── Fetch & render ─────────────────────────────────────────── */
  function fetchAndRender() {
    var grid = document.getElementById('server-grid');
    if (!grid) return;

    fetch(API_URL)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _lastResults = data;
        renderAPIGrid(data);
        var el = document.getElementById('servers-last-check');
        if (el) el.textContent = 'Updated: ' + new Date().toLocaleTimeString();
      })
      .catch(function (err) {
        var grid = document.getElementById('server-grid');
        if (grid) grid.innerHTML =
          '<div style="color:var(--danger);padding:20px;">&#9888; Could not reach backend: ' +
          err.message + '</div>';
      });
  }

  function renderAPIGrid(data) {
    var grid = document.getElementById('server-grid');
    if (!grid) return;

    if (!data || data.length === 0) {
      grid.innerHTML =
        '<div style="color:var(--text-muted);font-size:13px;padding:20px;">No servers in config.json.</div>';
      return;
    }

    var html = '';
    data.forEach(function (item) {
      var online  = item.online;
      var uptime  = item.uptime_pct != null ? item.uptime_pct : 100;
      var host    = item.host || item.url || '';
      var method  = (item.method || 'tcp').toUpperCase();
      var color   = online ? 'var(--success)' : 'var(--danger)';
      var bgtop   = online
        ? 'linear-gradient(135deg,rgba(0,230,118,.08),transparent)'
        : 'linear-gradient(135deg,rgba(255,23,68,.08),transparent)';

      html +=
        '<div class="server-card" style="' +
          'background:var(--bg-card);' +
          'border:1px solid ' + (online ? 'rgba(0,230,118,.35)' : 'rgba(255,23,68,.35)') + ';' +
          'border-radius:12px;padding:16px 16px 14px;' +
          'background-image:' + bgtop + ';' +
          'transition:transform .15s;' +
        '">' +

          /* Header row */
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
            '<span style="font-size:1rem;font-weight:600;color:var(--text-primary);">' + _esc(item.name) + '</span>' +
            '<span style="' +
              'padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;letter-spacing:.04em;' +
              (online
                ? 'background:rgba(0,230,118,.15);color:var(--success);'
                : 'background:rgba(255,23,68,.15);color:var(--danger);') +
            '">' + (online ? 'ONLINE' : 'OFFLINE') + '</span>' +
          '</div>' +

          /* Details */
          '<div style="font-size:.8rem;color:var(--text-secondary);margin-top:3px;">&#128207; ' + _esc(method) + '</div>' +
          '<div style="font-size:.8rem;color:var(--text-secondary);margin-top:3px;">&#127760; ' + _esc(host) + '</div>' +
          (item.status_code
            ? '<div style="font-size:.8rem;color:var(--text-secondary);margin-top:3px;">HTTP ' + item.status_code + '</div>'
            : '') +

          /* Uptime bar */
          '<div style="height:5px;background:rgba(255,255,255,.08);border-radius:3px;margin-top:12px;overflow:hidden;">' +
            '<div style="height:100%;width:' + uptime + '%;background:' + color + ';border-radius:3px;transition:width .5s;"></div>' +
          '</div>' +
          '<div style="font-size:.75rem;color:var(--text-muted);margin-top:4px;">Session uptime: ' + uptime + '%</div>' +

        '</div>';
    });

    grid.innerHTML = html;
  }

  function _esc(s) {
    return String(s)
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;');
  }

  /* ── Interval management ────────────────────────────────────── */
  function startInterval(ms) {
    stopInterval();
    if (ms > 0) _interval = setInterval(fetchAndRender, ms);
  }

  function stopInterval() {
    if (_interval) { clearInterval(_interval); _interval = null; }
  }

  /* ── Override tracker functions ─────────────────────────────── */

  // checkAllServers — called by the "Check All" button
  window.checkAllServers = function () { fetchAndRender(); };

  // setServerInterval — called by the interval dropdown
  window.setServerInterval = function () {
    var sel = document.getElementById('server-interval');
    _intervalMs = sel ? parseInt(sel.value, 10) * 1000 : 30000;
    startInterval(_intervalMs);
    fetchAndRender();
  };

  /* ── Boot when the Servers tab is first activated ───────────── */
  // Watch for tab switches (the tracker uses data-tab + click events)
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-tab="servers"]');
    if (btn) {
      // small delay so the tab section becomes visible first
      setTimeout(function () {
        fetchAndRender();
        startInterval(_intervalMs);
      }, 80);
    }
    // Pause auto-check when leaving the servers tab
    if (e.target.closest('[data-tab]') && !e.target.closest('[data-tab="servers"]')) {
      stopInterval();
    }
  });

  // Also run immediately if the page loads on the servers tab
  window.addEventListener('DOMContentLoaded', function () {
    if (document.querySelector('[data-tab="servers"].active') ||
        window.location.hash === '#servers') {
      fetchAndRender();
      startInterval(_intervalMs);
    }

    // Wire the interval selector if it already exists in DOM
    var sel = document.getElementById('server-interval');
    if (sel) {
      sel.addEventListener('change', function () {
        _intervalMs = parseInt(sel.value, 10) * 1000;
        startInterval(_intervalMs);
      });
    }
  });

  console.log('[TDC] Live server monitor injected — backend:', API_URL);
})();
</script>
"""

    # Inject before </body>
    if "</body>" in html:
        html = html.replace("</body>", inject + "\n</body>", 1)
    else:
        html += inject

    return html


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return Response(build_page(), mimetype="text/html; charset=utf-8")


@app.route("/api/status")
def api_status():
    results = get_latest_results()
    resp = jsonify(results)
    # CORS — allow the GitHub Pages site to call this endpoint
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/api/status", methods=["OPTIONS"])
def api_status_preflight():
    resp = Response("", status=204)
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/api/refresh")
def api_refresh():
    """Force re-download of the tracker HTML from GitHub."""
    if os.path.exists(TRACKER_CACHE):
        os.remove(TRACKER_CACHE)
    fetch_tracker_html()
    resp = jsonify({"status": "tracker refreshed from GitHub"})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Pre-fetch the tracker HTML on startup
    if not os.path.exists(TRACKER_CACHE):
        fetch_tracker_html()
    print("\n" + "=" * 55)
    print("  TDC IT Asset Tracker + Live Server Monitor")
    print("  http://localhost:5000")
    print("  API:  http://localhost:5000/api/status")
    print("  To refresh tracker HTML: /api/refresh")
    print("=" * 55 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
