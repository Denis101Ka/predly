"""Render the repository banners from HTML, so the type stays crisp and the palette exact.

    python brand/make_banner.py path/to/mascot.jpg

Writes assets/banner.png       1280x640, the GitHub social preview card
       assets/banner-wide.png  1600x400, the strip that sits on top of the README
       assets/banner.html      the source, kept so anyone can re-render it
"""
import base64, io, pathlib, subprocess, sys

from PIL import Image, ImageDraw

D = pathlib.Path(__file__).resolve().parent
ROOT = D.parent
ASSETS = ROOT / "assets"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

MASCOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else D / "mascot.jpg"

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:#000}
.stage{position:relative;overflow:hidden;background:#050604;color:#fff;
  font-family:'Segoe UI','Inter',Arial,sans-serif;-webkit-font-smoothing:antialiased;
  background-image:
    radial-gradient(900px 520px at 12% 108%, rgba(200,255,0,.20), transparent 62%),
    radial-gradient(700px 420px at 96% -20%, rgba(255,212,0,.10), transparent 60%),
    linear-gradient(0deg, rgba(255,255,255,.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);
  background-size:auto,auto,44px 44px,44px 44px}
.stage::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(120% 120% at 50% 50%, transparent 55%, rgba(0,0,0,.65) 100%)}
.rule{position:absolute;left:0;right:0;height:3px;
  background:linear-gradient(90deg,#C8FF00 0%,#C8FF00 62%,#FFD400 62%,#FFD400 100%)}
.mascot{position:absolute;object-fit:cover;background:#000;border-radius:26px;
  border:1px solid rgba(200,255,0,.30);
  box-shadow:0 0 70px rgba(200,255,0,.22), 0 22px 50px rgba(0,0,0,.65), inset 0 0 60px rgba(0,0,0,.6)}
.word{font-weight:900;letter-spacing:-.045em;line-height:.86;color:#fff}
.word i{font-style:normal;color:#C8FF00}
.tag{font-family:'JetBrains Mono','Consolas',monospace;color:#8A9179;letter-spacing:.22em;text-transform:uppercase}
.chips{display:flex;gap:10px;flex-wrap:wrap}
.chip{font-family:'JetBrains Mono','Consolas',monospace;border-radius:999px;
  border:1px solid rgba(200,255,0,.32);background:rgba(200,255,0,.07);color:#C8FF00;white-space:nowrap}
.chip.y{border-color:rgba(255,212,0,.30);background:rgba(255,212,0,.07);color:#FFD400}
.chip.n{border-color:rgba(255,255,255,.14);background:rgba(255,255,255,.04);color:#8A9179}
.card{background:#0B0D08;border:1px solid #1E2317;border-radius:14px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04), 0 20px 50px rgba(0,0,0,.5)}
.row{display:flex;align-items:center;gap:12px;border-bottom:1px solid #161A11}
.row:last-child{border-bottom:none}
.dot{border-radius:8px;flex:none;background:linear-gradient(140deg,#C8FF00,#9BE000)}
.q{color:#E9EEDD;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
.q b{color:#fff}
.track{border-radius:6px;overflow:hidden;display:flex;background:#14180E;border:1px solid #1E2317;flex:none}
.track .y{background:linear-gradient(90deg,#9BE000,#C8FF00);flex:none}
.track .n{background:linear-gradient(90deg,#FFA800,#FFD400);flex:none;opacity:.85}
.pill{font-family:'JetBrains Mono','Consolas',monospace;font-weight:800;border-radius:7px;text-align:center;flex:none}
.pill.y{background:rgba(200,255,0,.13);color:#C8FF00;border:1px solid rgba(200,255,0,.35)}
.pill.n{background:rgba(255,212,0,.12);color:#FFD400;border:1px solid rgba(255,212,0,.30)}
.url{position:absolute;font-family:'JetBrains Mono','Consolas',monospace;color:#5C6250;letter-spacing:.18em}
"""

MARKETS = [
    ("SLOTH", "reach <b>$154K</b> within the hour", 62),
    ("PONS", "double from <b>$493M</b> before 21:35 UTC", 40),
    ("DLORE", "stay above <b>$39K</b> till 15:00 UTC", 81),
]


def rows(font, pad, track_w, pill_w):
    out = []
    for sym, q, yes in MARKETS:
        out.append(
            f'<div class="row" style="padding:{pad}px 16px">'
            f'<span class="dot" style="width:{font+8}px;height:{font+8}px"></span>'
            f'<span class="q" style="font-size:{font}px">Will <b>${sym}</b> {q}</span>'
            f'<span class="track" style="width:{track_w}px;height:{font+6}px">'
            f'<span class="y" style="width:{yes}%"></span><span class="n" style="width:{100-yes}%"></span></span>'
            f'<span class="pill y" style="width:{pill_w}px;font-size:{font-1}px;padding:5px 0">{yes}c</span>'
            f'<span class="pill n" style="width:{pill_w}px;font-size:{font-1}px;padding:5px 0">{100-yes}c</span>'
            f"</div>")
    return "".join(out)


def social(mascot_uri):
    return f"""
<div class="stage" style="width:1280px;height:640px">
  <div class="rule" style="top:0"></div>
  <img class="mascot" src="{mascot_uri}" style="left:36px;top:96px;width:452px;height:452px">
  <div style="position:absolute;left:520px;top:150px;width:716px">
    <div class="word" style="font-size:132px">PRED<i>LY</i></div>
    <div class="tag" style="font-size:15px;margin-top:18px">prediction markets on meme caps</div>
    <div class="chips" style="margin-top:26px">
      <span class="chip" style="font-size:13px;padding:8px 15px">CAPS READ FROM THE CHAIN</span>
      <span class="chip y" style="font-size:13px;padding:8px 15px">ODDS YOU CAN RECOMPUTE</span>
      <span class="chip n" style="font-size:13px;padding:8px 15px">ROBINHOOD CHAIN · 4663</span>
    </div>
    <div class="card" style="margin-top:30px">{rows(15, 13, 150, 52)}</div>
  </div>
  <div class="url" style="right:38px;bottom:26px;font-size:14px">PREDLY.TECH</div>
  <div class="rule" style="bottom:0"></div>
</div>"""


def wide(mascot_uri):
    return f"""
<div class="stage" style="width:1600px;height:400px">
  <div class="rule" style="top:0"></div>
  <img class="mascot" src="{mascot_uri}" style="left:34px;top:34px;width:332px;height:332px">
  <div style="position:absolute;left:392px;top:96px;width:470px">
    <div class="word" style="font-size:104px">PRED<i>LY</i></div>
    <div class="tag" style="font-size:12.5px;margin-top:14px">prediction markets on meme caps</div>
    <div class="chips" style="margin-top:20px">
      <span class="chip" style="font-size:11px;padding:6px 12px">CAPS FROM CHAIN</span>
      <span class="chip y" style="font-size:11px;padding:6px 12px">RECOMPUTABLE ODDS</span>
    </div>
  </div>
  <div class="card" style="position:absolute;left:900px;top:74px;width:660px">{rows(14, 12, 138, 48)}</div>
  <div class="url" style="right:36px;bottom:22px;font-size:12px">PREDLY.TECH · CHAIN 4663</div>
  <div class="rule" style="bottom:0"></div>
</div>"""


def page(body):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"


def shot(html, name, w, h):
    ASSETS.mkdir(exist_ok=True)
    src = ASSETS / f"{name}.html"
    src.write_text(html, encoding="utf-8")
    png = ASSETS / f"{name}.png"
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", f"--screenshot={png}",
                    f"--window-size={w},{h}", "--hide-scrollbars", "--default-background-color=00000000",
                    src.as_uri()], check=False, capture_output=True)
    print(f"  {png.name}  {w}x{h}  {png.stat().st_size // 1024} kB")


def cutout(path, tol=44):
    """Flood the flat background in from the four corners and drop it to transparent.

    A global threshold would eat the mascot, whose body is nearly black as well, so the
    fill only follows pixels connected to the edge of the frame.
    """
    im = Image.open(path).convert("RGB")
    key = (255, 0, 255)
    for corner in ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1)):
        ImageDraw.floodfill(im, corner, key, thresh=tol)
    rgba = im.convert("RGBA")
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, _ = px[x, y]
            if (r, g, b) == key:
                px[x, y] = (0, 0, 0, 0)
    buf = io.BytesIO()
    rgba.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    if not MASCOT.exists():
        print("mascot image not found:", MASCOT)
        return
    ext = MASCOT.suffix.lstrip(".").replace("jpg", "jpeg")
    uri = f"data:image/{ext};base64," + base64.b64encode(MASCOT.read_bytes()).decode()
    shot(page(social(uri)), "banner", 1280, 640)
    shot(page(wide(uri)), "banner-wide", 1600, 400)
    print("done")


if __name__ == "__main__":
    main()
