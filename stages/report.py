"""Stage 4 — HTML report renderer -> report.html.

Reads strategy.json + profile.json from the run dir and produces a
single self-contained report.html with dark/light mode toggle.
No external dependencies; pure stdlib.
"""

from __future__ import annotations

import html as _html_mod
import json
from datetime import date
from pathlib import Path

_PATH_LABELS = {
    "build": "Build",
    "buy": "Buy",
    "buy_then_extend": "Buy-then-Extend",
    "adopt_self_host": "Adopt & Self-host",
}

_PATH_COLORS = {
    "build": "#14b8a6",
    "buy": "#3b82f6",
    "buy_then_extend": "#6366f1",
    "adopt_self_host": "#8b5cf6",
}

_STATUS_COLORS = {
    "SUPPORTED": "#22c55e",
    "PARTIAL": "#f59e0b",
    "UNSUPPORTED": "#ef4444",
}


def _e(s: object) -> str:
    return _html_mod.escape(str(s) if s is not None else "")


def _label(path: str) -> str:
    return _PATH_LABELS.get(path, path.replace("_", " ").title())


def _color(path: str) -> str:
    return _PATH_COLORS.get(path, "#94a3b8")


def _sc(status: str) -> str:
    return _STATUS_COLORS.get(status, "#94a3b8")


def _cites(ids: list[str]) -> str:
    if not ids:
        return ""
    parts = "".join(
        f'<a href="#claim-{_e(cid)}" class="cite" title="{_e(cid)}">{_e(cid[:6])}</a>'
        for cid in ids
    )
    return f'<sup class="cites">{parts}</sup>'


def _bullets(items: list[dict], icon: str) -> str:
    if not items:
        return ""
    lis = "".join(
        f'<li><span class="bi">{_e(icon)}</span>'
        f'{_e(b.get("text", ""))}'
        f'{_cites(b.get("cited_claim_ids", []))}</li>'
        for b in items
    )
    return f'<ul class="blist">{lis}</ul>'


def _dossier(d: dict, is_rec: bool) -> str:
    path = d["path"]
    c = _color(path)
    lbl = _label(path)
    badge = (
        f'<span class="rec-badge" style="background:{c}22;color:{c}">&#9733; Recommended</span>'
        if is_rec else ""
    )
    rev = d.get("reversibility") or {}

    parts: list[str] = []
    if pros := _bullets(d.get("pros", []), "✓"):
        parts.append(f'<div class="ds"><h4 class="dsh">Pros</h4>{pros}</div>')
    if cons := _bullets(d.get("cons", []), "✕"):
        parts.append(f'<div class="ds"><h4 class="dsh">Cons</h4>{cons}</div>')
    if risks := _bullets(d.get("key_risks", []), "!"):
        parts.append(f'<div class="ds"><h4 class="dsh">Key Risks</h4>{risks}</div>')
    if rt := rev.get("text"):
        rc = _cites(rev.get("cited_claim_ids", []))
        parts.append(
            f'<div class="ds"><h4 class="dsh">Reversibility</h4>'
            f'<p class="rev">&#8617; {_e(rt)}{rc}</p></div>'
        )

    body = "".join(parts) or "<p class='empty'>No evidence items.</p>"
    return (
        f'<div class="dossier">'
        f'<div class="dos-hdr">'
        f'<span class="chip" style="background:{c}22;color:{c};border:1px solid {c}44">{_e(lbl)}</span>'
        f'{badge}'
        f'</div>{body}</div>'
    )


def _claim_row(cid: str, c: dict) -> str:
    status = c.get("status", "")
    sc = _sc(status)
    src = c.get("source") or {}
    url = src.get("url", "")
    title = _e(src.get("title", ""))
    link = f'<a href="{_e(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
    quote = _e(src.get("display_quote", ""))
    track = c.get("track", "")
    dim = _e(c.get("dimension", ""))
    flags = _e(", ".join(c.get("flags", [])))
    sdate = _e(src.get("source_date", ""))
    text = _e(c.get("text", ""))
    date_part = f'<p class="cdate">{sdate}</p>' if sdate else ""

    return (
        f'<tr id="claim-{_e(cid)}">'
        f'<td><code class="cid">{_e(cid[:6])}</code></td>'
        f'<td class="ctd"><p class="ct">{text}</p>'
        f'<p class="cq">&ldquo;{quote}&rdquo;</p>'
        f'<p class="cs">{link}</p>{date_part}</td>'
        f'<td><span class="sbadge" style="background:{sc}22;color:{sc}">{_e(status)}</span></td>'
        f'<td><span class="trk t{_e(track.lower())}">{_e(track)}</span></td>'
        f'<td class="dim">{dim}</td>'
        f'<td class="flags">{flags}</td>'
        f'</tr>\n'
    )


_CSS = """\
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  font-size:15px;line-height:1.6;
  background:var(--bg);color:var(--text);
  transition:background .2s,color .2s;
}

:root{
  --bg:#0d0f18;--surface:#141724;--surface2:#1c2033;--border:#252a3d;
  --text:#c9d1e0;--muted:#7a8599;--heading:#eef0f8;
  --accent:#6366f1;--shadow:0 1px 6px rgba(0,0,0,.55);
}
[data-theme=light]{
  --bg:#f2f4fb;--surface:#ffffff;--surface2:#eef0f8;--border:#dde1ef;
  --text:#374151;--muted:#6b7280;--heading:#111827;
  --accent:#4f46e5;--shadow:0 1px 4px rgba(0,0,0,.08);
}

header{
  position:sticky;top:0;z-index:100;
  display:flex;align-items:center;justify-content:space-between;
  padding:.7rem 1.5rem;
  background:var(--surface);border-bottom:1px solid var(--border);
  box-shadow:var(--shadow);
}
.brand{font-weight:800;font-size:.95rem;color:var(--heading);letter-spacing:-.02em}
.brand em{color:var(--accent);font-style:normal}
#theme-btn{
  cursor:pointer;background:var(--surface2);border:1px solid var(--border);
  color:var(--muted);border-radius:6px;padding:.28rem .8rem;font-size:.78rem;
  font-weight:600;letter-spacing:.03em;transition:all .15s;
}
#theme-btn:hover{border-color:var(--accent);color:var(--accent)}

main{max-width:1100px;margin:0 auto;padding:2rem 1.5rem 3rem}

.hero{
  border-radius:12px;padding:2rem 2.25rem;margin-bottom:2rem;
  background:var(--surface);border:1px solid var(--border);
  box-shadow:var(--shadow);
  background-image:linear-gradient(135deg,var(--surface) 60%,var(--surface2));
}
.rec-pill{
  display:inline-flex;align-items:center;gap:.5rem;
  font-size:.72rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  padding:.3rem 1rem;border-radius:999px;margin-bottom:1.1rem;border:1px solid;
}
.hero h1{font-size:1.45rem;color:var(--heading);margin-bottom:.6rem;font-weight:800;letter-spacing:-.02em}
.thesis{color:var(--text);margin-bottom:1.5rem;font-size:.95rem;max-width:72ch}
.need-grid{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.75rem;
  border-top:1px solid var(--border);padding-top:1.25rem;margin-top:.25rem;
}
.need-item h5{
  font-size:.65rem;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);margin-bottom:.3rem;font-weight:700;
}
.need-item p{font-size:.83rem;color:var(--text);line-height:1.5}

.section{margin-bottom:2.5rem}
.section>h2{
  font-size:1rem;font-weight:800;color:var(--heading);letter-spacing:-.01em;
  margin-bottom:1rem;padding-bottom:.5rem;
  border-bottom:2px solid var(--border);
  display:flex;align-items:center;gap:.6rem;
}

.factor-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.875rem}
.factor-card{
  background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:1.1rem 1.2rem;box-shadow:var(--shadow);transition:border-color .15s;
}
.factor-card:hover{border-color:var(--accent)}
.factor-card h4{font-size:.82rem;font-weight:700;color:var(--heading);margin-bottom:.35rem}
.factor-card p{font-size:.8rem;color:var(--muted);line-height:1.55}

.tab-nav{
  display:flex;gap:0;flex-wrap:wrap;
  border-bottom:2px solid var(--border);margin-bottom:0;
}
.tab-btn{
  cursor:pointer;background:none;border:none;
  padding:.55rem 1.1rem;font-size:.83rem;font-weight:600;
  color:var(--muted);border-bottom:2px solid transparent;
  margin-bottom:-2px;transition:color .15s,border-color .15s;
  display:flex;align-items:center;gap:.4rem;
}
.tab-btn:hover{color:var(--heading)}
.tab-btn.active{color:var(--accent);border-bottom-color:var(--accent)}
.rec-dot{
  width:7px;height:7px;border-radius:50%;
  display:inline-block;flex-shrink:0;
}
.tab-content{
  background:var(--surface);border:1px solid var(--border);border-top:none;
  border-radius:0 0 10px 10px;padding:1.5rem 1.75rem;box-shadow:var(--shadow);
  min-height:180px;
}
.tab-panel{display:none}

.dossier{}
.dos-hdr{display:flex;align-items:center;gap:.65rem;margin-bottom:1.25rem;flex-wrap:wrap}
.chip{
  font-size:.72rem;font-weight:700;padding:.25rem .75rem;border-radius:999px;
  letter-spacing:.04em;
}
.rec-badge{
  font-size:.68rem;font-weight:700;padding:.2rem .6rem;border-radius:4px;
  letter-spacing:.04em;
}
.ds{margin-bottom:1.1rem}
.dsh{
  font-size:.7rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  color:var(--muted);margin-bottom:.45rem;
}
.blist{list-style:none;padding:0;display:flex;flex-direction:column;gap:.4rem}
.blist li{
  display:flex;align-items:baseline;gap:.5rem;
  font-size:.858rem;color:var(--text);line-height:1.55;
}
.bi{font-style:normal;flex-shrink:0;width:1rem;font-size:.72rem;font-weight:700}
.rev{font-size:.85rem;color:var(--muted);font-style:italic;line-height:1.55}
.empty{color:var(--muted);font-size:.85rem;font-style:italic}
sup.cites{font-size:.62rem;margin-left:.1rem;line-height:1}
a.cite{
  color:var(--accent);text-decoration:none;margin:0 .05rem;
  padding:.05rem .22rem;background:var(--surface2);border-radius:3px;
  font-variant-numeric:tabular-nums;transition:background .12s;
}
a.cite:hover{background:var(--border);text-decoration:underline}

.challenger-card{
  background:var(--surface);border:1px solid var(--border);
  border-left:3px solid var(--accent);
  border-radius:10px;padding:1.4rem 1.6rem;box-shadow:var(--shadow);
}
.ch-hdr{display:flex;align-items:center;gap:.65rem;flex-wrap:wrap;margin-bottom:.75rem}
.ch-tag{
  font-size:.65rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  padding:.15rem .5rem;border-radius:4px;
  background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b44;
}
.wins-label{font-size:.75rem;color:var(--muted);font-weight:700;margin-bottom:.3rem}
.wins-list{
  margin:.15rem 0 .85rem 1.1rem;
  font-size:.83rem;color:var(--muted);display:flex;flex-direction:column;gap:.2rem;
}
.ch-body{font-size:.858rem;color:var(--text);line-height:1.65}

.oq-list{list-style:none;padding:0;display:flex;flex-direction:column;gap:.55rem}
.oq-list li{
  background:var(--surface);border:1px solid var(--border);
  border-radius:8px;padding:.7rem 1rem .7rem 2.1rem;
  font-size:.858rem;color:var(--text);position:relative;
  box-shadow:var(--shadow);
}
.oq-list li::before{
  content:"?";position:absolute;left:.75rem;top:.72rem;
  color:var(--accent);font-weight:900;font-size:.8rem;
}

.ev-wrap{overflow-x:auto;border-radius:10px;border:1px solid var(--border);box-shadow:var(--shadow)}
.ev-table{width:100%;border-collapse:collapse;font-size:.8rem}
.ev-table th{
  text-align:left;padding:.5rem .8rem;
  font-size:.67rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  color:var(--muted);background:var(--surface2);
  border-bottom:1px solid var(--border);position:sticky;top:0;
}
.ev-table td{
  padding:.6rem .8rem;border-bottom:1px solid var(--border);
  vertical-align:top;color:var(--text);
}
.ev-table tr:last-child td{border-bottom:none}
.ev-table tr:target td{background:var(--surface2)}
.ev-table tr:hover td{background:var(--surface2);transition:background .1s}
.cid{
  font-family:monospace;font-size:.75rem;color:var(--muted);
  padding:.1rem .35rem;background:var(--surface2);border-radius:3px;
}
.ct{font-size:.8rem;color:var(--text);margin-bottom:.2rem;line-height:1.45}
.cq{font-size:.75rem;color:var(--muted);font-style:italic;margin-bottom:.2rem}
.cs a{
  font-size:.72rem;color:var(--accent);text-decoration:none;
  display:block;max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.cs a:hover{text-decoration:underline}
.cdate{font-size:.68rem;color:var(--muted);margin-top:.15rem}
.sbadge{
  font-size:.65rem;font-weight:700;padding:.15rem .45rem;
  border-radius:4px;white-space:nowrap;
}
.trk{
  font-size:.68rem;font-weight:700;padding:.15rem .4rem;border-radius:4px;
  text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;
}
.tbuild{background:#14b8a622;color:#14b8a6}
.tbuy{background:#3b82f622;color:#3b82f6}
.dim{font-size:.72rem;color:var(--muted);font-family:monospace}
.flags{font-size:.68rem;color:var(--muted)}

footer{
  text-align:center;padding:1.5rem;font-size:.72rem;color:var(--muted);
  border-top:1px solid var(--border);margin-top:1rem;
}
footer code{font-family:monospace;font-size:.7rem;
  background:var(--surface2);padding:.1rem .3rem;border-radius:3px}
"""

_JS = """\
function showTab(path) {
  document.querySelectorAll('.tab-panel').forEach(function(p) {
    p.style.display = 'none';
  });
  document.querySelectorAll('.tab-btn').forEach(function(b) {
    b.classList.remove('active');
  });
  var panel = document.getElementById('tab-' + path);
  if (panel) panel.style.display = 'block';
  var btn = document.querySelector('[data-path="' + path + '"]');
  if (btn) btn.classList.add('active');
}

function toggleTheme() {
  var root = document.documentElement;
  var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  var btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = next === 'dark' ? '☀ Light' : '☾ Dark';
  try { localStorage.setItem('vvv-theme', next); } catch(e) {}
}

(function() {
  try {
    var saved = localStorage.getItem('vvv-theme');
    if (saved && saved !== 'dark') {
      document.documentElement.setAttribute('data-theme', saved);
      var btn = document.getElementById('theme-btn');
      if (btn) btn.textContent = saved === 'dark' ? '☀ Light' : '☾ Dark';
    }
  } catch(e) {}
})();
"""

_TEMPLATE = """\
<!DOCTYPE html>
<html data-theme="dark" lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vendor vs Valor &mdash; <<<REC_LABEL>>></title>
<style><<<CSS>>></style>
</head>
<body>
<header>
  <div class="brand">Vendor <em>vs</em> Valor</div>
  <button id="theme-btn" onclick="toggleTheme()">&#9728; Light</button>
</header>
<main>

  <div class="hero">
    <div class="rec-pill" style="background:<<<REC_COLOR>>>22;color:<<<REC_COLOR>>>;border-color:<<<REC_COLOR>>>44">
      &#10003; Recommendation &mdash; <<<REC_LABEL>>>
    </div>
    <h1>Strategy Report</h1>
    <p class="thesis"><<<THESIS>>></p>
    <div class="need-grid">
      <div class="need-item"><h5>Capability</h5><p><<<CAPABILITY>>></p></div>
      <div class="need-item"><h5>Context</h5><p><<<BIZ_CONTEXT>>></p></div>
      <div class="need-item"><h5>Problem</h5><p><<<PROBLEM>>></p></div>
    </div>
  </div>

  <div class="section">
    <h2>Decisive Factors</h2>
    <div class="factor-grid"><<<FACTOR_CARDS>>></div>
  </div>

  <div class="section">
    <h2>Path Analysis</h2>
    <div class="tab-nav"><<<TAB_BUTTONS>>></div>
    <div class="tab-content"><<<TAB_PANELS>>></div>
  </div>

<<<CHALLENGER_SECTION>>>

  <div class="section">
    <h2>Open Questions</h2>
    <<<OPEN_Q_HTML>>>
  </div>

  <div class="section">
    <h2>Evidence Index</h2>
    <div class="ev-wrap">
      <table class="ev-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Claim / Source</th>
            <th>Status</th>
            <th>Track</th>
            <th>Dim</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody><<<CLAIM_ROWS>>></tbody>
      </table>
    </div>
  </div>

</main>
<footer>
  Run&nbsp;<code><<<RUN_ID>>></code> &bull; Generated&nbsp;<<<TODAY>>>
</footer>
<script><<<JS>>></script>
</body>
</html>"""


def run_report(run_dir: str | Path) -> Path:
    """Render strategy.json + profile.json -> report.html. Returns the output path."""
    run_dir = Path(run_dir)
    strategy = json.loads((run_dir / "strategy.json").read_text(encoding="utf-8"))
    profile = json.loads((run_dir / "profile.json").read_text(encoding="utf-8"))

    rec = strategy["recommendation"]
    rec_path = rec["path"]
    rec_lbl = _label(rec_path)
    rec_c = _color(rec_path)
    thesis = _e(rec["thesis"])

    decisive = strategy.get("decisive_factors", [])
    dossiers = strategy.get("dossiers", [])
    runner_up = strategy.get("runner_up") or {}
    open_qs = strategy.get("open_questions", [])
    claims = strategy.get("claims_index", {})
    need = profile.get("need", {})
    run_id = profile.get("run_id", run_dir.name)

    # Recommended path first, then others in original order
    dmap = {d["path"]: d for d in dossiers}
    order = [rec_path] + [d["path"] for d in dossiers if d["path"] != rec_path]

    # Factor cards
    factor_cards = "".join(
        f'<div class="factor-card">'
        f'<h4>{_e(f.get("dimension", ""))}</h4>'
        f'<p>{_e(f.get("why", ""))}</p>'
        f'</div>'
        for f in decisive
    )

    # Tabs
    tab_buttons = ""
    tab_panels = ""
    for path in order:
        if path not in dmap:
            continue
        d = dmap[path]
        c = _color(path)
        lbl = _label(path)
        is_rec = path == rec_path
        active_cls = " active" if is_rec else ""
        dot = f'<span class="rec-dot" style="background:{c}"></span>' if is_rec else ""
        tab_buttons += (
            f'<button class="tab-btn{active_cls}" '
            f'onclick="showTab(\'{path}\')" data-path="{path}">'
            f'{dot}{_e(lbl)}</button>'
        )
        display = "block" if is_rec else "none"
        tab_panels += (
            f'<div class="tab-panel" id="tab-{path}" style="display:{display}">'
            f'{_dossier(d, is_rec)}'
            f'</div>'
        )

    # Challenger / runner-up section
    challenger_section = ""
    if runner_up:
        ru_path = runner_up.get("path", "")
        ru_c = _color(ru_path)
        ru_lbl = _label(ru_path)
        ru_case = _e(runner_up.get("case", ""))
        ru_wins = runner_up.get("wins_when", [])
        from_ch = runner_up.get("from_challenger", False)
        wins_items = "".join(f"<li>{_e(w)}</li>" for w in ru_wins)
        ch_tag = '<span class="ch-tag">Challenger</span>' if from_ch else ""
        ru_cites = _cites(runner_up.get("cited_claim_ids", []))

        challenger_section = (
            f'<div class="section">'
            f'<h2>Second Opinion {ch_tag}</h2>'
            f'<div class="challenger-card">'
            f'<div class="ch-hdr">'
            f'<span class="chip" style="background:{ru_c}22;color:{ru_c};border:1px solid {ru_c}44">'
            f'{_e(ru_lbl)}</span>'
            f'</div>'
            f'<p class="wins-label">Wins when:</p>'
            f'<ul class="wins-list">{wins_items}</ul>'
            f'<p class="ch-body">{ru_case}{ru_cites}</p>'
            f'</div>'
            f'</div>'
        )

    # Open questions
    oq_html = (
        '<ul class="oq-list">'
        + "".join(f"<li>{_e(q)}</li>" for q in open_qs)
        + "</ul>"
    ) if open_qs else "<p style='color:var(--muted);font-size:.875rem'>None recorded.</p>"

    # Evidence rows: BUILD first, then BUY, alpha within track
    claim_rows = "".join(
        _claim_row(cid, c)
        for cid, c in sorted(claims.items(), key=lambda x: (x[1].get("track", ""), x[0]))
    )

    out = _TEMPLATE
    for marker, value in {
        "<<<CSS>>>": _CSS,
        "<<<JS>>>": _JS,
        "<<<REC_LABEL>>>": _e(rec_lbl),
        "<<<REC_COLOR>>>": rec_c,
        "<<<THESIS>>>": thesis,
        "<<<CAPABILITY>>>": _e(need.get("capability", "")),
        "<<<BIZ_CONTEXT>>>": _e(need.get("business_context", "")),
        "<<<PROBLEM>>>": _e(need.get("problem", "")),
        "<<<FACTOR_CARDS>>>": factor_cards,
        "<<<TAB_BUTTONS>>>": tab_buttons,
        "<<<TAB_PANELS>>>": tab_panels,
        "<<<CHALLENGER_SECTION>>>": challenger_section,
        "<<<OPEN_Q_HTML>>>": oq_html,
        "<<<CLAIM_ROWS>>>": claim_rows,
        "<<<RUN_ID>>>": _e(run_id),
        "<<<TODAY>>>": _e(date.today().isoformat()),
    }.items():
        out = out.replace(marker, value)

    out_path = run_dir / "report.html"
    out_path.write_text(out, encoding="utf-8")
    return out_path
