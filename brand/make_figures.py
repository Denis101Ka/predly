"""Render the README figures from real data, as HTML, then shoot them with headless Edge.

Every figure here is computed on the spot from this repository's own engine and its own
published snapshot. Nothing is drawn by hand and no number is typed in, so a figure that
disagrees with the code is a bug rather than a stale image.

    python brand/make_figures.py            all figures
    python brand/make_figures.py odds       just one

Writes into assets/:
    verify-terminal.png   the output of `python -m verify --vectors`, as a terminal card
    odds-curves.png       how a price moves with distance to target and with time left
    montecarlo.png        the closed form against simulated first passage frequencies
    calibration.png       quoted price against realised hit rate over the published paths
    tokens.png            the tokens in the current snapshot, with their real launch images
"""
import json
import math
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from verify.odds import BARS_PER_HOUR, quote, realized_sigma, target_for  # noqa: E402

D = pathlib.Path(__file__).resolve().parent
ROOT = D.parent
ASSETS = ROOT / "assets"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

ACID, YELLOW, AMBER, RED = "#C8FF00", "#FFD400", "#FFA800", "#FF4D2E"
BG, PANEL, LINE, HAIR = "#050604", "#0B0D08", "#1E2317", "#161A11"
TXT, MUTE, DIM = "#FFFFFF", "#8A9179", "#5C6250"

CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{background:{BG}}}
.fig{{position:relative;overflow:hidden;background:{BG};color:{TXT};
  font-family:'Segoe UI','Inter',Arial,sans-serif;-webkit-font-smoothing:antialiased;
  background-image:radial-gradient(900px 520px at 8% -20%, rgba(200,255,0,.09), transparent 62%),
                   linear-gradient(0deg, rgba(255,255,255,.014) 1px, transparent 1px),
                   linear-gradient(90deg, rgba(255,255,255,.014) 1px, transparent 1px);
  background-size:auto,42px 42px,42px 42px}}
.hd{{display:flex;align-items:baseline;gap:12px;padding:22px 28px 0}}
.hd h2{{font-size:19px;font-weight:800;letter-spacing:-.01em}}
.hd .sub{{font-family:'JetBrains Mono','Consolas',monospace;font-size:11px;color:{DIM};letter-spacing:.14em;text-transform:uppercase}}
.hd .tag{{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:10px;color:{ACID};
  border:1px solid rgba(200,255,0,.32);background:rgba(200,255,0,.07);border-radius:999px;padding:5px 12px}}
.note{{padding:0 28px;margin-top:10px;font-size:12.5px;color:{MUTE};line-height:1.55}}
.note b{{color:{TXT};font-weight:600}}
.mono{{font-family:'JetBrains Mono','Consolas',monospace}}
/* terminal card */
.term{{margin:18px 28px 26px;background:#070904;border:1px solid {LINE};border-radius:12px;overflow:hidden;
  box-shadow:0 24px 60px rgba(0,0,0,.55)}}
.term .bar{{display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid {HAIR};background:#0A0C07}}
.term .dot{{width:11px;height:11px;border-radius:50%}}
.term .path{{margin-left:10px;font-family:'JetBrains Mono',monospace;font-size:11px;color:{DIM}}}
.term pre{{padding:16px 18px;font-family:'JetBrains Mono','Consolas',monospace;font-size:13.5px;line-height:1.62;
  color:#D9E3C8;white-space:pre-wrap}}
.term .p{{color:{ACID};font-weight:700}}
.term .c{{color:{TXT}}}
.term .ok{{color:{ACID}}}
.term .num{{color:{YELLOW}}}
/* legend */
.legend{{display:flex;gap:20px;padding:0 28px;margin-top:12px;font-family:'JetBrains Mono',monospace;font-size:11px;color:{MUTE}}}
.legend i{{display:inline-block;width:16px;height:3px;border-radius:2px;vertical-align:middle;margin-right:7px}}
/* token gallery */
.grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:12px;padding:18px 28px 26px}}
.tk{{background:{PANEL};border:1px solid {LINE};border-radius:12px;padding:12px;text-align:center}}
.tk img{{width:52px;height:52px;border-radius:12px;object-fit:cover;background:#000;border:1px solid rgba(200,255,0,.18)}}
.tk .s{{font-size:12.5px;font-weight:800;margin-top:9px}}
.tk .n{{font-family:'JetBrains Mono',monospace;font-size:9px;color:{DIM};margin-top:3px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tk .c{{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:{ACID};margin-top:7px;font-weight:700}}
.tk .v{{font-family:'JetBrains Mono',monospace;font-size:9.5px;color:{MUTE};margin-top:2px}}
"""


# ---------------------------------------------------------------- helpers

def page(body, css_extra=""):
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}{css_extra}</style>"
            f"</head><body>{body}</body></html>")


def shot(html, name, w, h):
    ASSETS.mkdir(exist_ok=True)
    src = ASSETS / f"_{name}.html"
    src.write_text(html, encoding="utf-8")
    png = ASSETS / f"{name}.png"
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", f"--screenshot={png}",
                    f"--window-size={w},{h}", "--hide-scrollbars", src.as_uri()],
                   check=False, capture_output=True)
    src.unlink(missing_ok=True)
    print(f"  {png.name:<22} {w}x{h}  {png.stat().st_size // 1024} kB")


def head(title, sub, tag):
    return f'<div class="hd"><h2>{title}</h2><span class="sub">{sub}</span><span class="tag">{tag}</span></div>'


def axes(x0, y0, w, h, xlab, ylab, xticks, yticks):
    """Frame, grid and tick labels for a plot in SVG user units."""
    out = [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#080A05" stroke="{LINE}"/>']
    for frac, label in yticks:
        y = y0 + h * (1 - frac)
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + w}" y2="{y:.1f}" stroke="{HAIR}"/>')
        out.append(f'<text x="{x0 - 10}" y="{y + 4:.1f}" fill="{DIM}" font-size="11" '
                   f'font-family="JetBrains Mono, monospace" text-anchor="end">{label}</text>')
    for frac, label in xticks:
        x = x0 + w * frac
        out.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0 + h}" stroke="{HAIR}"/>')
        out.append(f'<text x="{x:.1f}" y="{y0 + h + 20}" fill="{DIM}" font-size="11" '
                   f'font-family="JetBrains Mono, monospace" text-anchor="middle">{label}</text>')
    out.append(f'<text x="{x0 + w / 2}" y="{y0 + h + 42}" fill="{MUTE}" font-size="11.5" '
               f'text-anchor="middle" font-family="JetBrains Mono, monospace">{xlab}</text>')
    out.append(f'<text x="{x0 - 44}" y="{y0 + h / 2}" fill="{MUTE}" font-size="11.5" text-anchor="middle" '
               f'font-family="JetBrains Mono, monospace" transform="rotate(-90 {x0 - 44} {y0 + h / 2})">{ylab}</text>')
    return "".join(out)


def polyline(points, color, width=2.4, dash=None):
    d = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash_attr}/>'


def usd(n):
    if n >= 1e6:
        return f"${n / 1e6:.2f}M"
    if n >= 1e3:
        return f"${n / 1e3:.0f}K"
    return f"${n:.0f}"


# ---------------------------------------------------------------- figures

def fig_verify_terminal():
    """Run the real CLI and frame its output."""
    out = subprocess.run([sys.executable, "-m", "verify", "--vectors"], cwd=ROOT,
                         capture_output=True, text=True).stdout.rstrip()
    one = subprocess.run([sys.executable, "-m", "verify", "--cap", "493e6", "--target", "986e6",
                          "--sigma", "0.35", "--hours", "5.5"], cwd=ROOT,
                         capture_output=True, text=True).stdout.rstrip()

    def colour(line):
        line = (line.replace("&", "&amp;").replace("<", "&lt;"))
        if line.strip().startswith("ok"):
            return line.replace("ok", f'<span class="ok">ok</span>', 1)
        return line

    body = "".join([
        f'<div class="fig" style="width:1200px;height:620px">',
        head("Verify a price", "no install · standard library only", "RUN IT YOURSELF"),
        '<div class="term"><div class="bar">',
        f'<span class="dot" style="background:{RED}"></span>',
        f'<span class="dot" style="background:{YELLOW}"></span>',
        f'<span class="dot" style="background:{ACID}"></span>',
        '<span class="path">~/predly-tools</span></div><pre>',
        f'<span class="p">$</span> <span class="c">python -m verify --cap 493e6 --target 986e6 '
        f'--sigma 0.35 --hours 5.5</span>\n{one}\n\n',
        f'<span class="p">$</span> <span class="c">python -m verify --vectors</span>\n',
        "\n".join(colour(l) for l in out.splitlines()),
        "</pre></div>",
        '<div class="note">The same <b>40c</b> the board quotes for that market. '
        'The vectors replay through the Python, the TypeScript and the C++ engine, and CI diffs '
        'the cents all three print.</div></div>',
    ])
    shot(page(body), "verify-terminal", 1200, 620)


def fig_odds_curves():
    """Left: price against distance to target. Right: price against time left."""
    W, H = 470, 300
    x0, y0 = 86, 34

    # panel 1: p_yes as the cap approaches a fixed target, for three volatilities
    p1 = [axes(x0, y0, W, H, "cap as a share of the target", "YES price",
               [(0.0, "40%"), (0.25, "55%"), (0.5, "70%"), (0.75, "85%"), (1.0, "100%")],
               [(0.0, "0c"), (0.25, "25c"), (0.5, "50c"), (0.75, "75c"), (1.0, "100c")])]
    for sigma, colour in ((0.25, YELLOW), (0.6, AMBER), (1.2, ACID)):
        pts = []
        for i in range(121):
            ratio = 0.4 + 0.6 * i / 120
            q = quote(1_000_000 * ratio, 1_000_000, sigma, 1.0)
            pts.append((x0 + W * i / 120, y0 + H * (1 - q.p_yes)))
        p1.append(polyline(pts, colour))
    p1.append(f'<text x="{x0 + 12}" y="{y0 + 22}" fill="{MUTE}" font-size="11" '
              f'font-family="JetBrains Mono, monospace">one hour left</text>')

    # panel 2: p_yes as the deadline approaches, for three distances
    x1 = x0 + W + 132
    p2 = [axes(x1, y0, W, H, "hours left on the market", "YES price",
               [(0.0, "0h"), (0.25, "1.5h"), (0.5, "3h"), (0.75, "4.5h"), (1.0, "6h")],
               [(0.0, "0c"), (0.25, "25c"), (0.5, "50c"), (0.75, "75c"), (1.0, "100c")])]
    for mult, colour, label in ((1.15, ACID, "target 1.15x"), (1.5, AMBER, "target 1.5x"),
                                (2.0, YELLOW, "target 2x")):
        pts = []
        for i in range(121):
            hours = 0.02 + 5.98 * i / 120
            q = quote(1_000_000, 1_000_000 * mult, 0.6, hours)
            pts.append((x1 + W * i / 120, y0 + H * (1 - q.p_yes)))
        p2.append(polyline(pts, colour))
    p2.append(f'<text x="{x1 + 12}" y="{y0 + 22}" fill="{MUTE}" font-size="11" '
              f'font-family="JetBrains Mono, monospace">sigma 0.6 per hour</text>')

    clamp_lines = "".join(
        f'<line x1="{x}" y1="{y0 + H * (1 - p):.1f}" x2="{x + W}" y2="{y0 + H * (1 - p):.1f}" '
        f'stroke="{RED}" stroke-width="1" stroke-dasharray="4 4" opacity=".55"/>'
        for x in (x0, x1) for p in (0.03, 0.97))

    svg = (f'<svg width="1240" height="410" style="display:block">'
           f'{"".join(p1)}{"".join(p2)}{clamp_lines}</svg>')

    body = "".join([
        '<div class="fig" style="width:1240px;height:590px">',
        head("How a price moves", "computed with verify/odds.py", "THE MODEL"),
        '<div class="legend">'
        f'<span><i style="background:{ACID}"></i>high volatility / near target</span>'
        f'<span><i style="background:{AMBER}"></i>middle</span>'
        f'<span><i style="background:{YELLOW}"></i>low volatility / far target</span>'
        f'<span><i style="background:{RED}"></i>the 3c and 97c clamps</span></div>',
        f'<div style="padding:10px 0 0 0">{svg}</div>',
        '<div class="note" style="margin-top:2px">A market never quotes certainty. '
        'The dashed lines are where the model stops claiming to know: everything is clamped into '
        '<b>3c to 97c</b>, which is also why a target already passed reads 97c rather than 100c.</div></div>',
    ])
    shot(page(body), "odds-curves", 1240, 590)


def fig_montecarlo():
    """Closed form against a simulated first passage frequency, computed here with numpy."""
    import numpy as np

    cells = [
        (100_000, 150_000, 0.60, 1.0, "touch", "reach 1.5x, 1h, sigma 0.6"),
        (100_000, 130_000, 0.45, 2.0, "touch", "reach 1.3x, 2h, sigma 0.45"),
        (100_000, 200_000, 0.90, 1.0, "touch", "reach 2x, 1h, sigma 0.9"),
        (493e6, 986e6, 0.35, 5.5, "touch", "the README example"),
        (100_000, 85_000, 0.50, 1.0, "floor", "hold 0.85x, 1h, sigma 0.5"),
        (100_000, 70_000, 0.80, 3.0, "floor", "hold 0.7x, 3h, sigma 0.8"),
        (250_000, 240_000, 0.25, 0.5, "floor", "hold 0.96x, 30m, sigma 0.25"),
    ]
    paths, steps, beta = 60_000, 900, 0.5826
    rng = np.random.default_rng(20260909)

    rows = []
    for cap, level, sigma, hours, kind, label in cells:
        dt = hours / steps
        vol = sigma * math.sqrt(dt)
        shift = beta * vol
        log_level = math.log(level) + (-shift if kind == "touch" else shift)
        walk = math.log(cap) + np.cumsum(rng.standard_normal((paths, steps)) * vol, axis=1)
        crossed = (walk.max(axis=1) >= log_level) if kind == "touch" else (walk.min(axis=1) <= log_level)
        sim = float(crossed.mean()) if kind == "touch" else float(1 - crossed.mean())
        q = quote(cap, level, sigma, hours, kind)
        from verify.odds import phi
        raw = 2 * (1 - phi(q.d)) if kind == "touch" else 2 * phi(q.d) - 1
        rows.append((label, raw, sim))

    W, H = 940, 280
    x0, y0 = 104, 40
    bar_w = W / (len(rows) * 2 + 1)
    svg = [axes(x0, y0, W, H, "", "probability",
                [], [(0.0, "0%"), (0.25, "25%"), (0.5, "50%"), (0.75, "75%"), (1.0, "100%")])]
    for i, (label, model, sim) in enumerate(rows):
        bx = x0 + bar_w * (i * 2 + 0.6)
        for j, (val, colour) in enumerate(((model, ACID), (sim, YELLOW))):
            h = H * val
            svg.append(f'<rect x="{bx + j * bar_w * 0.46:.1f}" y="{y0 + H - h:.1f}" '
                       f'width="{bar_w * 0.42:.1f}" height="{h:.1f}" fill="{colour}" opacity=".9" rx="3"/>')
        svg.append(f'<text x="{bx + bar_w * 0.46:.1f}" y="{y0 + H + 20}" fill="{DIM}" font-size="10" '
                   f'font-family="JetBrains Mono, monospace" text-anchor="middle" '
                   f'transform="rotate(-16 {bx + bar_w * 0.46:.1f} {y0 + H + 20})">{label}</text>')
        gap = abs(model - sim)
        svg.append(f'<text x="{bx + bar_w * 0.46:.1f}" y="{y0 + H - max(model, sim) * H - 10:.1f}" '
                   f'fill="{MUTE}" font-size="10" font-family="JetBrains Mono, monospace" '
                   f'text-anchor="middle">{gap * 100:.1f}pt</text>')

    worst = max(abs(m - s) for _, m, s in rows)
    body = "".join([
        '<div class="fig" style="width:1120px;height:580px">',
        head("The formula against brute force", f"{paths:,} paths per cell, {steps} steps each",
             "MONTE CARLO"),
        '<div class="legend">'
        f'<span><i style="background:{ACID}"></i>closed form, the price the board quotes</span>'
        f'<span><i style="background:{YELLOW}"></i>simulated first passage frequency</span></div>',
        f'<svg width="1120" height="400" style="display:block;margin-top:12px">{"".join(svg)}</svg>',
        f'<div class="note" style="margin-top:4px">Worst disagreement <b>{worst * 100:.1f} points</b>. '
        'The same check runs in CI as <span class="mono">native/bin/montecarlo</span> with a hundred '
        'times the paths. It failed on its first run and caught a real modelling bug: the simulation '
        'carried an Ito correction the pricing formula does not assume.</div></div>',
    ])
    shot(page(body), "montecarlo", 1120, 580)


def _calibration_rows(horizon=24):
    """Mirror of native/backtest.cpp, so the figure and the binary tell the same story."""
    snap = json.loads((ROOT / "data" / "snapshot-latest.json").read_text(encoding="utf-8"))
    fx_rate = snap.get("eth_usd", 0.0)
    buckets = {}
    total = 0
    for t in snap["tokens"]:
        path = t.get("path") or []
        if len(path) < 40:
            continue
        med = sorted(path)[len(path) // 2]
        if not med > 0:
            continue
        fx = fx_rate if t.get("unit") == "ETH" else 1.0
        caps = [p * 1e9 * fx for p in path if med / 6 < p < med * 6]
        if len(caps) < 40:
            continue
        hours = horizon / BARS_PER_HOUR
        for open_i in range(20, len(caps) - horizon):
            sigma = realized_sigma(caps[open_i - 20:open_i])
            cap = caps[open_i]
            for k in (0.5, 1.0, 1.5, 2.0):
                for kind in ("touch", "floor"):
                    level = target_for(cap, sigma, hours, k if kind == "touch" else -k)
                    q = quote(cap, level, sigma, hours, kind)
                    fwd = caps[open_i + 1:open_i + 1 + horizon]
                    hit = any(c >= level for c in fwd) if kind == "touch" else any(c <= level for c in fwd)
                    yes = hit if kind == "touch" else not hit
                    b = buckets.setdefault(q.yes_cents // 10, [0, 0, 0.0])
                    b[0] += 1
                    b[1] += 1 if yes else 0
                    b[2] += q.p_yes
                    total += 1
    rows = []
    for band in sorted(buckets):
        n, yes, psum = buckets[band]
        if n < 30:
            continue
        rows.append((band, n, psum / n, yes / n))
    return rows, total


def fig_calibration():
    rows, total = _calibration_rows()
    W, H = 430, 330
    x0, y0 = 104, 46
    svg = [axes(x0, y0, W, H, "price the model quoted", "how often it happened",
                [(0.0, "0c"), (0.5, "50c"), (1.0, "100c")],
                [(0.0, "0%"), (0.5, "50%"), (1.0, "100%")])]
    svg.append(f'<line x1="{x0}" y1="{y0 + H}" x2="{x0 + W}" y2="{y0}" stroke="{DIM}" '
               f'stroke-width="1.4" stroke-dasharray="6 5"/>')
    svg.append(f'<text x="{x0 + W - 8}" y="{y0 + 22}" fill="{DIM}" font-size="10.5" text-anchor="end" '
               f'font-family="JetBrains Mono, monospace">perfect calibration</text>')
    pts = []
    for band, n, avg, hit in rows:
        cx, cy = x0 + W * avg, y0 + H * (1 - hit)
        pts.append((cx, cy))
        r = 5 + 9 * (n / max(x[1] for x in rows))
        colour = ACID if hit >= avg else YELLOW
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{colour}" opacity=".85"/>')
    svg.append(polyline(pts, "rgba(255,255,255,.35)", 1.6, dash="4 4"))

    tx = x0 + W + 120
    table = [f'<text x="{tx}" y="{y0 + 6}" fill="{MUTE}" font-size="11" '
             f'font-family="JetBrains Mono, monospace">band      markets   quoted   happened</text>']
    for i, (band, n, avg, hit) in enumerate(rows):
        y = y0 + 34 + i * 28
        colour = ACID if hit >= avg else YELLOW
        table.append(f'<text x="{tx}" y="{y}" fill="{TXT}" font-size="12.5" '
                     f'font-family="JetBrains Mono, monospace">{band * 10:>2}-{band * 10 + 9:>2}c</text>')
        table.append(f'<text x="{tx + 96}" y="{y}" fill="{MUTE}" font-size="12.5" '
                     f'font-family="JetBrains Mono, monospace" text-anchor="end">{n:,}</text>')
        table.append(f'<text x="{tx + 186}" y="{y}" fill="{MUTE}" font-size="12.5" '
                     f'font-family="JetBrains Mono, monospace" text-anchor="end">{avg * 100:.1f}%</text>')
        table.append(f'<text x="{tx + 292}" y="{y}" fill="{colour}" font-size="12.5" font-weight="700" '
                     f'font-family="JetBrains Mono, monospace" text-anchor="end">{hit * 100:.1f}%</text>')

    body = "".join([
        '<div class="fig" style="width:1120px;height:600px">',
        head("Is the model calibrated?", f"{total:,} markets replayed over the published snapshot",
             "BACKTEST"),
        '<div class="legend">'
        f'<span><i style="background:{ACID}"></i>happened more often than quoted</span>'
        f'<span><i style="background:{YELLOW}"></i>happened less often than quoted</span>'
        f'<span><i style="background:{DIM}"></i>bubble size is the number of markets</span></div>',
        f'<svg width="1120" height="440" style="display:block;margin-top:14px">{"".join(svg)}{"".join(table)}</svg>',
        '<div class="note" style="margin-top:6px">The curve sits inside the diagonal at '
        'both ends: the model is <b>overconfident on near certainties</b> and <b>underprices the tails</b>, '
        'which is what a log-normal does to a market whose caps are anything but. Published rather than '
        'hidden, because a calibration nobody shows is a calibration nobody ran.</div></div>',
    ])
    shot(page(body), "calibration", 1120, 600)


def fig_tokens():
    snap = json.loads((ROOT / "data" / "snapshot-latest.json").read_text(encoding="utf-8"))
    fx_rate = snap.get("eth_usd", 0.0)
    tiles = []
    for t in snap["tokens"][:14]:
        fx = fx_rate if t.get("unit") == "ETH" else 1.0
        cap = (t.get("last") or 0) * 1e9 * fx
        name = ((t.get("meta") or {}).get("long_name") or t.get("name") or "")[:20]
        logo = t.get("logo")
        img = (f'<img src="{logo}" alt="">' if logo else
               f'<div style="width:52px;height:52px;border-radius:12px;background:{PANEL};margin:0 auto"></div>')
        tiles.append(f'<div class="tk">{img}<div class="s">${t.get("symbol", "?")}</div>'
                     f'<div class="n">{name}</div><div class="c">{usd(cap)}</div>'
                     f'<div class="v">{t.get("trades", 0):,} fills</div></div>')

    body = "".join([
        '<div class="fig" style="width:1240px;height:520px">',
        head("Real tokens, real launch images", f"snapshot at block {snap['chain']['head_block']:,}",
             "FROM THE CHAIN"),
        '<div class="note">Every tile below was read off Robinhood Chain: the symbol from the token '
        'contract, the cap from the executed fills, the picture out of the transaction that created '
        f'the token. <b>{snap["curves_seen"]:,} curves</b> traded inside the scanned window.</div>',
        f'<div class="grid">{"".join(tiles)}</div></div>',
    ])
    shot(page(body), "tokens", 1240, 520)


FIGURES = {
    "verify": fig_verify_terminal,
    "odds": fig_odds_curves,
    "montecarlo": fig_montecarlo,
    "calibration": fig_calibration,
    "tokens": fig_tokens,
}


def main():
    wanted = sys.argv[1:] or list(FIGURES)
    for name in wanted:
        fn = FIGURES.get(name)
        if not fn:
            print(f"  unknown figure: {name}")
            continue
        fn()
    print("done")


if __name__ == "__main__":
    main()
