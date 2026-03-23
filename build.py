"""
build.py — Generates a single integrated index.html for Cloudflare Pages
Run with:  python build.py
Output:    index.html  (upload this to Cloudflare Pages)
"""

import urllib.request, os

GITHUB_URL = "https://raw.githubusercontent.com/majinist/tdc-it-asset-tracker/main/index.html"
OUTPUT     = "index.html"

STATUS_URL = "https://raw.githubusercontent.com/LeoDeleonIT/ITtracker/main/status.json"

INJECT = """
<!-- TDC Live Server Monitor — fetches from GitHub status.json -->
<script>
(function () {
  var STATUS_URL = '""" + STATUS_URL + """';
  var _pollTmr   = null;
  var _active    = false;

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function renderGrid(data) {
    var grid = document.getElementById('server-grid');
    if (!grid || !Array.isArray(data)) return;
    if (!data.length) {
      grid.innerHTML = '<div style="color:var(--text-muted);padding:20px;">No server data yet — make sure dashboard.py is running.</div>';
      return;
    }
    var html = '';
    data.forEach(function(item) {
      var up  = item.online;
      var pct = (item.uptime_pct != null) ? item.uptime_pct : 100;
      var col = up ? 'rgba(0,230,118,.35)' : 'rgba(255,23,68,.35)';
      html += '<div class="server-card" style="background:var(--bg-card);border:1px solid '+col+';border-radius:12px;padding:16px;background-image:linear-gradient(135deg,'+(up?'rgba(0,230,118,.06)':'rgba(255,23,68,.06)')+',transparent);">'
        +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
        +'<span style="font-size:1rem;font-weight:600;color:var(--text-primary);">'+esc(item.name)+'</span>'
        +'<span style="padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;'
        +(up?'background:rgba(0,230,118,.15);color:var(--success)':'background:rgba(255,23,68,.15);color:var(--danger)')+';">'
        +(up?'ONLINE':'OFFLINE')+'</span></div>'
        +'<div style="font-size:.8rem;color:var(--text-secondary);">&#127760; '+esc(item.host||item.url||'')+'</div>'
        +'<div style="height:5px;background:rgba(255,255,255,.08);border-radius:3px;margin-top:10px;overflow:hidden;">'
        +'<div style="height:100%;width:'+pct+'%;background:'+(up?'var(--success)':'var(--danger)')+';border-radius:3px;"></div></div>'
        +'<div style="font-size:.75rem;color:var(--text-muted);margin-top:3px;">Session uptime: '+pct+'%</div>'
        +'</div>';
    });
    grid.innerHTML = html;
    var el = document.getElementById('servers-last-check');
    if (el) el.textContent = 'Last updated: ' + new Date().toLocaleTimeString();
  }

  function fetchAndRender() {
    if (!_active) return;
    fetch(STATUS_URL + '?_=' + Date.now(), {cache: 'no-store'})
      .then(function(r){ return r.json(); })
      .then(renderGrid)
      .catch(function(){});
  }

  function startPoll() {
    _active = true;
    fetchAndRender();
    clearInterval(_pollTmr);
    _pollTmr = setInterval(fetchAndRender, 60000);
  }

  function stopPoll() {
    _active = false;
    clearInterval(_pollTmr);
    _pollTmr = null;
  }

  window.addEventListener('load', function() {
    window.checkAllServers   = function() { fetchAndRender(); };
    window.setServerInterval = function() {
      var sel = document.getElementById('server-interval');
      var ms  = sel ? parseInt(sel.value,10)*1000 : 60000;
      clearInterval(_pollTmr);
      _pollTmr = setInterval(fetchAndRender, Math.max(ms, 60000));
      fetchAndRender();
    };
    if (document.querySelector('[data-tab="servers"].active')) startPoll();
  });

  document.addEventListener('click', function(e) {
    try {
      var btn = e.target.closest('[data-tab]');
      if (!btn) return;
      btn.getAttribute('data-tab') === 'servers' ? setTimeout(startPoll, 200) : stopPoll();
    } catch(e) {}
  });

})();
</script>
"""

def build():
    print("[*] Downloading latest index.html from GitHub...")
    req = urllib.request.Request(GITHUB_URL, headers={"User-Agent": "TDC-Build/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8")
    print("[+] Downloaded successfully.")

    # Use rfind to get the TRUE last </body> tag, not one inside a JS string
    pos = html.rfind("</body>")
    if pos != -1:
        html = html[:pos] + INJECT + "\n</body>" + html[pos + len("</body>"):]
        print("[+] Server monitor script injected.")
    else:
        html += INJECT
        print("[!] </body> not found — appended script to end.")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"[+] Saved to: {OUTPUT}  ({size_kb:.1f} KB)")
    print()
    print("=" * 50)
    print("  DONE! Upload 'index.html' to Cloudflare Pages.")
    print("  Make sure dashboard.py is running locally")
    print("  on port 5000 for live server monitoring.")
    print("=" * 50)

if __name__ == "__main__":
    build()
