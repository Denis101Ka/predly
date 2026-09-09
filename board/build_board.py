"""Build board/board.html out of data/snapshot-latest.json.

The token list, the caps, the volumes, the trade counts and every price path on the
board come from Robinhood Chain. The markets, odds, order book and payouts on top of
them are a product preview, and the sheet says so in the footer.
"""
import json, pathlib, subprocess, sys

D = pathlib.Path(__file__).resolve().parent
SNAP = json.loads((D.parent / "data" / "snapshot-latest.json").read_text(encoding="utf-8"))

CSS = """
:root{
  --bg:#050604; --panel:#0B0D08; --panel2:#101309; --line:#1E2317; --hair:#161A11;
  --txt:#FFFFFF; --mute:#8A9179; --dim:#5C6250;
  --acid:#C8FF00; --acid2:#9BE000; --yellow:#FFD400; --amber:#FFA800; --red:#FF4D2E;
  --acidd:rgba(200,255,0,.13); --yellowd:rgba(255,212,0,.13);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;overflow:hidden;
  font-family:'Inter','Segoe UI',Arial,sans-serif;-webkit-font-smoothing:antialiased}
#stage{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;background:var(--bg);color:var(--txt);
  display:grid;grid-template-rows:70px 30px 1fr 138px 26px;
  background-image:radial-gradient(1400px 700px at 50% -14%,rgba(200,255,0,.10),transparent 62%),
                   radial-gradient(900px 500px at 100% 110%,rgba(255,212,0,.05),transparent 60%)}
/* header */
#hd{display:flex;align-items:center;gap:18px;padding:0 22px;border-bottom:1px solid var(--line)}
#mark{width:40px;height:40px;flex:none;filter:drop-shadow(0 0 14px rgba(200,255,0,.45))}
#brand{font-size:26px;font-weight:800;letter-spacing:-.01em;line-height:1}
#brand b{color:var(--acid)}
#tagline{font-size:9.5px;letter-spacing:.24em;color:var(--dim);text-transform:uppercase;margin-top:5px}
.chip{display:flex;align-items:center;gap:8px;padding:6px 12px;border:1px solid var(--line);border-radius:999px;
  font-family:'JetBrains Mono','Consolas',monospace;font-size:10.5px;color:var(--mute);background:rgba(200,255,0,.04)}
.chip i{width:7px;height:7px;border-radius:50%;background:var(--acid);display:block;
  box-shadow:0 0 10px var(--acid);animation:blink 1s infinite}
.chip b{color:var(--txt);font-variant-numeric:tabular-nums}
.chip.real{border-color:rgba(200,255,0,.4)}
@keyframes blink{50%{opacity:.15}}
#hud{margin-left:auto;display:flex;gap:30px;align-items:center}
.hb{text-align:right}
.hb .k{font-size:8.5px;letter-spacing:.18em;color:var(--dim);text-transform:uppercase}
.hb .v{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.15;
  font-family:'JetBrains Mono',monospace;letter-spacing:-.02em}
.hb .v.acid{color:var(--acid)} .hb .v.yellow{color:var(--yellow)} .hb .v.red{color:var(--red)}
.live{font-size:11px;font-weight:800;letter-spacing:.2em;color:#000;background:var(--acid);
  padding:5px 11px;border-radius:5px;animation:pulse 1.6s infinite}
@keyframes pulse{50%{box-shadow:0 0 22px rgba(200,255,0,.7)}}
/* strip */
#strip{border-bottom:1px solid var(--line);overflow:hidden;white-space:nowrap;display:flex;align-items:center;
  background:linear-gradient(90deg,rgba(200,255,0,.06),rgba(255,212,0,.03))}
#stripin{display:inline-block;animation:scroll 38s linear infinite;font-family:'JetBrains Mono',monospace;font-size:11px}
#stripin span{margin-right:32px;color:var(--dim)}
#stripin b{color:var(--txt);font-weight:700}
#stripin i{font-style:normal;font-weight:700}
#stripin i.u{color:var(--acid)} #stripin i.d{color:var(--amber)}
@keyframes scroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
/* layout */
#main{display:grid;grid-template-columns:318px 1fr 404px;gap:12px;padding:12px 14px;min-height:0}
.col{display:flex;flex-direction:column;gap:12px;min-height:0}
.pan{background:var(--panel);border:1px solid var(--line);border-radius:14px;display:flex;flex-direction:column;
  min-height:0;overflow:hidden;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
.ph{display:flex;align-items:center;gap:9px;padding:10px 14px 9px;border-bottom:1px solid var(--hair);flex:none}
.ph .t{font-size:10px;font-weight:800;letter-spacing:.19em;text-transform:uppercase}
.ph .m{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:9.5px;color:var(--dim)}
.ph .dot{width:6px;height:6px;border-radius:50%;background:var(--acid);box-shadow:0 0 8px var(--acid);animation:blink 1.3s infinite}
.ph .src{font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.12em;padding:2px 6px;border-radius:4px}
.src.chain{background:var(--acidd);color:var(--acid);border:1px solid rgba(200,255,0,.3)}
.src.demo{background:rgba(255,212,0,.09);color:var(--yellow);border:1px solid rgba(255,212,0,.25)}
.pb{flex:1;min-height:0;overflow:hidden;position:relative}
/* token avatar */
.av{width:32px;height:32px;border-radius:10px;flex:none;display:flex;align-items:center;justify-content:center;
  font-size:10px;font-weight:800;color:#0A0B08;letter-spacing:-.02em;overflow:hidden;
  background:#14180E;border:1px solid rgba(200,255,0,.18)}
.av img{width:100%;height:100%;object-fit:cover;display:block}
.av.sm{width:22px;height:22px;border-radius:7px;font-size:8px}
.av.sm img{border-radius:6px}
/* board */
#boardhead,.brow{display:grid;grid-template-columns:194px 1fr 150px 96px 176px 74px 74px 84px;align-items:center;gap:10px;padding:0 16px}
#boardhead{height:30px;border-bottom:1px solid var(--line);font-size:8.5px;letter-spacing:.16em;color:var(--dim);
  text-transform:uppercase;flex:none}
#boardhead span:nth-child(n+4){text-align:right}
#boardhead span:nth-child(5){text-align:left}
#board{display:flex;flex-direction:column;height:100%}
#rows{flex:1;display:flex;flex-direction:column;min-height:0}
.brow{flex:1 1 0;min-height:0;border-bottom:1px solid var(--hair);position:relative}
.brow.flash{animation:rowflash .8s ease-out}
@keyframes rowflash{0%{background:rgba(200,255,0,.10)}100%{background:transparent}}
.brow.new{animation:rowin .65s cubic-bezier(.2,.9,.2,1)}
@keyframes rowin{0%{opacity:0;transform:translateY(-16px);background:var(--acidd)}100%{opacity:1;transform:none}}
.brow.out{animation:rowout .8s ease-in forwards}
@keyframes rowout{to{opacity:0;transform:translateX(46px)}}
.brow.hero{background:linear-gradient(90deg,rgba(200,255,0,.09),transparent 60%);
  box-shadow:inset 3px 0 0 var(--acid)}
.mk{display:flex;align-items:center;gap:11px;min-width:0}
.mk .tk{font-size:15px;font-weight:800;letter-spacing:-.02em}
.mk .sub{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--dim);margin-top:2px}
.mk .tag{font-size:8px;font-weight:800;letter-spacing:.1em;padding:2px 6px;border-radius:4px;
  background:var(--acid);color:#0A0B08}
.q{font-size:13px;color:#E9EEDD;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.3}
.q b{color:#fff;font-weight:700}
.q em{font-style:normal;color:var(--mute)}
.capw{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:var(--mute);font-variant-numeric:tabular-nums;text-align:right}
.capw b{color:var(--txt);font-weight:700;font-size:12.5px}
.capw .bar{height:5px;background:#1A1E13;border-radius:3px;margin-top:5px;overflow:hidden;display:flex}
.capw .bar i{display:block;height:100%;background:linear-gradient(90deg,var(--acid2),var(--acid));transition:width .5s}
.spark{width:96px;height:26px;display:block;margin-left:auto}
.odds{display:flex;align-items:center;gap:9px}
.odds .track{flex:1;height:26px;background:#14180E;border-radius:7px;overflow:hidden;display:flex;border:1px solid var(--hair)}
.odds .track .y{flex:none;background:linear-gradient(90deg,var(--acid2),var(--acid));transition:width .5s cubic-bezier(.3,.9,.3,1)}
.odds .track .n{flex:none;background:linear-gradient(90deg,var(--amber),var(--yellow));opacity:.85;transition:width .5s cubic-bezier(.3,.9,.3,1)}
.odds .pct{font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:800;width:44px;text-align:right;font-variant-numeric:tabular-nums}
.pill{font-family:'JetBrains Mono',monospace;font-size:12.5px;font-weight:800;padding:6px 0;border-radius:7px;
  text-align:center;font-variant-numeric:tabular-nums}
.pill.y{background:var(--acidd);color:var(--acid);border:1px solid rgba(200,255,0,.35)}
.pill.n{background:var(--yellowd);color:var(--yellow);border:1px solid rgba(255,212,0,.3)}
.num{font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;font-variant-numeric:tabular-nums;color:var(--txt)}
.num s{text-decoration:none;display:block;font-size:9px;color:var(--dim);margin-top:2px}
/* feeds */
.frow{display:flex;align-items:center;gap:9px;padding:0 14px;height:33px;flex:none;border-bottom:1px solid var(--hair);
  font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums}
.frow.new{animation:slidein .5s ease-out}
@keyframes slidein{0%{opacity:0;transform:translateY(-12px);background:var(--acidd)}100%{opacity:1;transform:none}}
.frow .tk{color:var(--txt);font-weight:700;font-size:12px}
.frow .r{margin-left:auto;text-align:right;color:var(--acid)}
.lrow{display:grid;grid-template-columns:18px 24px 1fr 54px 74px;align-items:center;gap:9px;padding:0 14px;
  flex:1 1 0;min-height:0;border-bottom:1px solid var(--hair);
  font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums}
.lrow .rk{color:var(--dim);font-size:9.5px}
.lrow .w{color:var(--txt)} .lrow .pnl{text-align:right;font-weight:700} .lrow .wr{text-align:right}
.lrow.me{background:rgba(200,255,0,.07)} .lrow.me .w{color:var(--acid)}
.prow{display:grid;grid-template-columns:18px 1fr 46px 48px 74px;align-items:center;gap:8px;padding:0 14px;height:31px;
  flex:none;border-bottom:1px solid var(--hair);
  font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums}
.prow .tk{color:var(--txt);font-weight:700} .prow .sd{font-weight:800}
.prow .sd.y{color:var(--acid)} .prow .sd.n{color:var(--yellow)}
.prow .r{text-align:right;font-weight:700}
.up{color:var(--acid)} .down{color:var(--red)}
/* order book */
#dom{display:flex;flex-direction:column;min-height:0;flex:1}
.drow{position:relative;display:flex;align-items:center;justify-content:space-between;padding:0 14px;flex:1 1 0;min-height:0;
  font-family:'JetBrains Mono',monospace;font-size:11.5px;font-variant-numeric:tabular-nums}
.drow .fill{position:absolute;top:1px;bottom:1px;right:0;opacity:.16;transition:width .35s}
.drow.a .fill{background:var(--yellow)} .drow.b .fill{background:var(--acid)}
.drow span{position:relative;z-index:2}
.drow .px{font-weight:800} .drow.a .px{color:var(--yellow)} .drow.b .px{color:var(--acid)}
.drow .sz{color:var(--mute)}
#spread{display:flex;align-items:center;justify-content:space-between;padding:7px 14px;background:#0E1109;flex:none;
  border-top:1px solid var(--line);border-bottom:1px solid var(--line);
  font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--dim)}
#spread b{color:var(--txt);font-size:14px;font-weight:800}
.trow{display:grid;grid-template-columns:48px 40px 56px 1fr 72px;align-items:center;gap:7px;padding:0 14px;height:27px;
  flex:none;border-bottom:1px solid var(--hair);
  font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums}
.trow.new{animation:slidein .4s ease-out}
.trow .side{font-weight:800} .trow .side.y{color:var(--acid)} .trow .side.n{color:var(--yellow)}
.trow .px{color:var(--txt);font-weight:700} .trow .r{text-align:right}
/* focus */
#focuswrap{position:relative;height:100%}
#focus{position:absolute;inset:0;width:100%;height:100%}
/* resolved */
#res{display:flex;gap:12px;padding:11px 14px;overflow:hidden;border-top:1px solid var(--line);background:#080A06}
#reshead{width:120px;flex:none;display:flex;flex-direction:column;justify-content:center}
#reshead .t{font-size:10px;font-weight:800;letter-spacing:.17em;text-transform:uppercase}
#reshead .m{font-family:'JetBrains Mono',monospace;font-size:9.5px;color:var(--dim);margin-top:5px;line-height:1.4}
#rescards{flex:1;display:flex;gap:12px;overflow:hidden}
.rcard{width:250px;flex:none;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:11px 13px;position:relative}
.rcard.in{animation:cardin .6s cubic-bezier(.2,.9,.2,1)}
@keyframes cardin{0%{opacity:0;transform:translateX(50px) scale(.95)}100%{opacity:1;transform:none}}
.rcard.won{border-color:rgba(200,255,0,.45);box-shadow:0 0 24px rgba(200,255,0,.10)}
.rcard.lost{border-color:rgba(255,212,0,.28)}
.rcard .top{display:flex;align-items:center;gap:9px}
.rcard .tk{font-size:13px;font-weight:800}
.rcard .q{font-size:10.5px;color:var(--mute);margin-top:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rcard .bot{display:flex;align-items:baseline;margin-top:9px;font-family:'JetBrains Mono',monospace}
.rcard .lb{font-size:8.5px;color:var(--dim);letter-spacing:.12em}
.rcard .pay{margin-left:auto;font-size:15px;font-weight:800;font-variant-numeric:tabular-nums}
.rcard.won .pay{color:var(--acid)} .rcard.lost .pay{color:var(--yellow)}
.stamp{font-size:9px;font-weight:800;letter-spacing:.15em;padding:3px 8px;border-radius:5px;margin-left:auto}
.stamp.won{background:var(--acid);color:#0A0B08} .stamp.lost{background:rgba(255,212,0,.15);color:var(--yellow)}
/* footer */
#ft{display:flex;align-items:center;gap:14px;padding:0 16px;border-top:1px solid var(--line);
  font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.13em;color:var(--dim);text-transform:uppercase;overflow:hidden}
#ft>span{flex:none} #ft .fx{color:var(--acid);font-weight:800;letter-spacing:.22em}
#tick{flex:1;overflow:hidden;white-space:nowrap}
#tickin{display:inline-block;animation:scroll 50s linear infinite}
#tickin span{margin-right:56px} #tickin b{color:var(--acid)}
/* burst */
#burst{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;opacity:0;
  background:radial-gradient(700px 460px at 50% 50%,rgba(200,255,0,.20),rgba(0,0,0,.80))}
#burst.show{animation:burst 3.1s cubic-bezier(.2,.85,.2,1) forwards}
@keyframes burst{0%{opacity:0;transform:scale(1.1)}7%{opacity:1;transform:scale(1)}74%{opacity:1}100%{opacity:0}}
#burst .box{text-align:center;border:2px solid var(--acid);border-radius:20px;padding:30px 68px;background:rgba(5,6,4,.93);
  box-shadow:0 0 90px rgba(200,255,0,.4)}
#burst .big{font-size:104px;font-weight:800;letter-spacing:-.02em;color:var(--acid);line-height:1;text-shadow:0 0 40px rgba(200,255,0,.5)}
#burst .sub{font-family:'JetBrains Mono',monospace;font-size:18px;color:#fff;margin-top:14px;letter-spacing:.06em}
#burst .pay{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--mute);margin-top:9px}
#dbg{position:fixed;left:0;bottom:0;background:#000;color:var(--acid);font:11px monospace;padding:6px;z-index:99;white-space:pre}
"""

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>__NAME__ · prediction market on Robinhood Chain</title>
<style>__CSS__</style></head><body><div id="stage">

<div id="hd">
  <svg id="mark" viewBox="0 0 64 64">
    <path d="M8 46 L24 26 L36 36 L56 12" fill="none" stroke="#C8FF00" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M42 12 L56 12 L56 26" fill="none" stroke="#FFD400" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="8" cy="46" r="4.5" fill="#C8FF00"/>
  </svg>
  <div>
    <div id="brand">__BRAND_HTML__</div>
    <div id="tagline">bet on meme caps · robinhood chain</div>
  </div>
  <div class="chip real"><i></i>LIVE CHAIN DATA · BLOCK <b id="blk">0</b> · <b id="curves">0</b> CURVES TRADED</div>
  <div id="hud">
    <div class="hb"><div class="k">Chain volume 1h</div><div class="v acid" id="h_vol">$0</div></div>
    <div class="hb"><div class="k">Top cap</div><div class="v" id="h_cap">$0</div></div>
    <div class="hb"><div class="k">Markets open</div><div class="v" id="h_mk">0</div></div>
    <div class="hb"><div class="k">Settled today</div><div class="v yellow" id="h_res">0</div></div>
    <div class="hb"><div class="k">Your P&amp;L</div><div class="v acid" id="h_pnl">$0</div></div>
    <span class="live">LIVE</span>
  </div>
</div>

<div id="strip"><div id="stripin"></div></div>

<div id="main">
  <div class="col">
    <div class="pan" style="flex:1.1">
      <div class="ph"><span class="dot"></span><span class="t">Fresh on the curve</span><span class="src chain">CHAIN</span>
        <span class="m" id="m_launch">newest tokens</span></div>
      <div class="pb"><div id="launches"></div></div>
    </div>
    <div class="pan" style="flex:1">
      <div class="ph"><span class="t">Forecasters</span><span class="src demo">PREVIEW</span><span class="m">7d</span></div>
      <div class="pb"><div id="leader" style="display:flex;flex-direction:column;height:100%"></div></div>
    </div>
    <div class="pan" style="flex:.92">
      <div class="ph"><span class="t">Your book</span><span class="src demo">PREVIEW</span><span class="m">connect wallet</span></div>
      <div class="pb"><div id="positions"></div></div>
    </div>
  </div>

  <div class="pan">
    <div class="ph"><span class="dot"></span><span class="t">Live markets</span><span class="src chain">CAPS FROM CHAIN</span>
      <span class="m" id="m_board">every token on the launchpad gets a market on its cap</span></div>
    <div class="pb"><div id="board">
      <div id="boardhead">
        <span>token</span><span>market</span><span>cap / target</span><span>curve tape</span>
        <span>odds</span><span>yes</span><span>no</span><span>chain volume</span>
      </div>
      <div id="rows"></div>
    </div></div>
  </div>

  <div class="col">
    <div class="pan" style="flex:.95">
      <div class="ph"><span class="dot"></span><span class="t">Focus</span><span class="src chain">CHAIN</span>
        <span class="m" id="m_focus">—</span></div>
      <div class="pb"><div id="focuswrap"><canvas id="focus"></canvas></div></div>
    </div>
    <div class="pan" style="flex:1.05">
      <div class="ph"><span class="t">Order book</span><span class="src demo">PREVIEW</span><span class="m" id="m_dom">yes shares</span></div>
      <div class="pb" style="display:flex;flex-direction:column"><div id="dom"></div></div>
    </div>
    <div class="pan" style="flex:1">
      <div class="ph"><span class="dot"></span><span class="t">Trades</span><span class="src demo">PREVIEW</span><span class="m">last fills</span></div>
      <div class="pb"><div id="tape"></div></div>
    </div>
  </div>
</div>

<div id="res">
  <div id="reshead"><div class="t">Settled</div><div class="m" id="m_res">cap read off the chain at the deadline</div></div>
  <div id="rescards"></div>
</div>

<div id="ft">
  <span class="fx">__NAME__</span>
  <div id="tick"><div id="tickin"></div></div>
  <span id="clock">00:00</span>
</div>

<div id="burst"><div class="box"><div class="big" id="b_big">RESOLVED YES</div>
  <div class="sub" id="b_sub">—</div><div class="pay" id="b_pay">—</div></div></div>
</div>

<script>
/* ---- brand: one place to swap when the name lands ---- */
const NAME='__NAME__';
const SNAP=__SNAP__;
/* ------------------------------------------------------ */
const $=id=>document.getElementById(id);
const R=(a,b)=>a+Math.random()*(b-a), RI=(a,b)=>Math.floor(R(a,b+1)), pick=a=>a[RI(0,a.length-1)];
const pad2=n=>String(n).padStart(2,'0'), fmt=n=>Math.round(n).toLocaleString('en-US');
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const usd=n=>n>=1e6?'$'+(n/1e6).toFixed(2)+'M':(n>=1e3?'$'+(n/1e3).toFixed(n>=1e5?0:1)+'K':'$'+n.toFixed(0));
const money=n=>(n<0?'-$':'$')+fmt(Math.abs(n));
window.__err=null; window.onerror=m=>{window.__err=m};
function fit(){const s=$('stage'),k=Math.min(innerWidth/1920,innerHeight/1080);
  s.style.transform='translate('+Math.round((innerWidth-1920*k)/2)+'px,'+Math.round((innerHeight-1080*k)/2)+'px) scale('+k+')'}
addEventListener('resize',fit); fit();

const FX=SNAP.eth_usd||0, CYCLE=66000;
const t0=performance.now(); const now=()=>performance.now()-t0;
const cyclePos=()=>(now()%CYCLE)/CYCLE;
function hueOf(sym){let h=0;for(let i=0;i<sym.length;i++)h=(h*31+sym.charCodeAt(i))%360;return h}
function avatar(t,sm){
  const cls='av'+(sm?' sm':'');
  if(t.logo)return '<span class="'+cls+'"><img src="'+t.logo+'" alt="'+t.sym+'"></span>';
  const h=hueOf(t.sym);
  return '<span class="'+cls+'" style="background:linear-gradient(140deg,hsl('+(60+h%40)+',100%,60%),hsl('+(40+h%30)+',100%,50%))">'+
    t.sym.slice(0,3).toUpperCase()+'</span>';
}
/* nice round target above a cap */
function niceAbove(v){
  const e=Math.pow(10,Math.floor(Math.log10(v)));
  for(const m of [1,1.5,2,2.5,3,4,5,7.5,10,15,20])if(m*e>v*1.06)return m*e;
  return e*20;
}

/* ---------- markets built on the real tokens ---------- */
/* one misdecoded fill can put a cap at 1e17, so every path is trimmed around its median */
function sane(path){
  const s=path.slice().sort((a,b)=>a-b), med=s[s.length>>1];
  if(!(med>0))return [];
  return path.filter(v=>v>med/6&&v<med*6);
}
const TOKENS=[];
SNAP.tokens.forEach(t=>{
  if(!t.symbol||!t.path||t.path.length<25)return;
  const clean=sane(t.path); if(clean.length<20)return;
  const fx=t.unit==='ETH'?FX:1, caps=clean.map(p=>p*1e9*fx);
  const lastCap=caps[caps.length-1];
  /* a whole token can decode wrong when its quote leg flips units, drop it rather than print $10B */
  if(!(lastCap>3e3&&lastCap<8e7))return;
  const sym=t.symbol.toUpperCase().slice(0,9);
  const dup=TOKENS.find(x=>x.sym===sym);
  if(dup){ if(t.vol_usd>dup.vol)Object.assign(dup,{caps:caps,vol:t.vol_usd,trades:t.trades,curve:t.curve,
      logo:t.logo||dup.logo,name:(t.meta&&t.meta.long_name)||dup.name}); return }
  TOKENS.push({sym:sym, name:(t.meta&&t.meta.long_name)||t.name||t.symbol, curve:t.curve, token:t.token,
               caps:caps, vol:t.vol_usd, trades:t.trades, unit:t.unit, logo:t.logo||null,
               post:(t.meta&&t.meta.post)||null, blurb:(t.meta&&t.meta.blurb)||null,
               firstBlock:t.first_block, lastBlock:t.last_block});
});
let markets=[], hero=null, heroPhase='wait', settled=0, yourPnl=0, seq=0;
function mkMarket(t,heroFlag){
  const caps=t.caps, i0=heroFlag?0:RI(0,Math.max(0,caps.length-40));
  const m={id:++seq, t:t, sym:t.sym, i:i0, caps:caps, cap:caps[i0], hero:!!heroFlag,
           born:now(), life:heroFlag?60000:R(30000,110000), status:'live', vol:t.vol, trades:t.trades,
           yes:50, el:null, hist:[]};
  if(heroFlag){
    /* the target is a level this token's own tape actually reaches, so the crossing is real */
    const mx=Math.max.apply(null,caps), st=caps[0];
    m.target=niceAbove(st+(mx-st)*0.45);
    if(m.target>=mx||m.target<=st)m.target=niceAbove(st*1.02);
  } else {
    m.target=niceAbove(m.cap*R(1.05,1.8));
  }
  m.kind=m.target>m.cap?'cross':'hold';
  m.yes=priceOdds(m); for(let k=0;k<40;k++)m.hist.push(m.yes);
  markets.push(m); return m;
}
function priceOdds(m){
  const ratio=m.cap/m.target, left=clamp(1-(now()-m.born)/m.life,0,1);
  let fair=100/(1+Math.exp(-(ratio-.80)*6.2));
  const need=Math.max(0,(m.target-m.cap)/m.target);
  fair*=clamp(1-need*(1-left)*1.4,.25,1);
  return clamp(fair,2,98);
}
function questionOf(m){
  const H=new Date(Date.now()+Math.max(0,m.life-(now()-m.born))).toISOString().slice(11,16);
  return m.kind==='cross'
    ? 'Will <b>$'+m.sym+'</b> <em>cross '+usd(m.target)+' cap before '+H+' UTC</em>'
    : 'Will <b>$'+m.sym+'</b> <em>hold '+usd(m.target)+' cap till '+H+' UTC</em>';
}
function timeLeft(m){return Math.max(0,(m.life-(now()-m.born))/1000)}
function fmtLeft(m){const s=timeLeft(m);return s>=60?Math.floor(s/60)+'m '+pad2(Math.floor(s%60))+'s':Math.floor(s)+'s'}

/* ---------- board ---------- */
function sparkSVG(m){
  const a=m.caps.slice(Math.max(0,m.i-46),m.i+1); if(a.length<3)return '<svg class="spark"></svg>';
  const lo=Math.min.apply(null,a),hi=Math.max.apply(null,a),n=a.length;
  let d=''; a.forEach((v,i)=>{const x=96*i/(n-1),y=24-22*(v-lo)/((hi-lo)||1);d+=(i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1)});
  const up=a[n-1]>=a[0];
  return '<svg class="spark" viewBox="0 0 96 26"><path d="'+d+'" fill="none" stroke="'+(up?'#C8FF00':'#FFA800')+'" stroke-width="1.6"/></svg>';
}
function rowHTML(m){
  const no=100-Math.round(m.yes);
  return '<div class="mk">'+avatar(m.t)+'<div><div class="tk">$'+m.sym+(m.hero?' <span class="tag">NEW</span>':'')+'</div>'+
      '<div class="sub">'+(m.t.name||m.t.curve.slice(0,10)+'…')+'</div></div></div>'+
    '<div class="q">'+questionOf(m)+'</div>'+
    '<div class="capw"><b>'+usd(m.cap)+'</b> / '+usd(m.target)+
      '<div class="bar"><i style="width:'+clamp(m.cap/m.target*100,2,100)+'%"></i></div></div>'+
    '<div>'+sparkSVG(m)+'</div>'+
    '<div class="odds"><div class="track"><div class="y" style="width:'+Math.round(m.yes)+'%"></div>'+
      '<div class="n" style="width:'+no+'%"></div></div><span class="pct">'+Math.round(m.yes)+'%</span></div>'+
    '<div class="pill y">'+Math.round(m.yes)+'c</div>'+
    '<div class="pill n">'+no+'c</div>'+
    '<div class="num">'+usd(m.vol)+'<s>'+fmt(m.trades)+' fills · '+fmtLeft(m)+'</s></div>';
}
function renderBoard(){
  const box=$('rows');
  markets.forEach(m=>{ if(m.el)return;
    m.el=document.createElement('div'); m.el.className='brow new'+(m.hero?' hero':'');
    m.el.innerHTML=rowHTML(m);
    if(m.hero)box.insertBefore(m.el,box.firstChild); else box.appendChild(m.el);
  });
  $('h_mk').textContent=markets.filter(m=>m.status==='live').length;
}
function paintBoard(){
  markets.forEach(m=>{
    if(!m.el)return; const c=m.el.children, no=100-Math.round(m.yes);
    c[1].innerHTML=questionOf(m);
    c[2].innerHTML='<b>'+usd(m.cap)+'</b> / '+usd(m.target)+
      '<div class="bar"><i style="width:'+clamp(m.cap/m.target*100,2,100)+'%"></i></div>';
    c[3].innerHTML=sparkSVG(m);
    const tr=c[4].firstChild; tr.children[0].style.width=Math.round(m.yes)+'%'; tr.children[1].style.width=no+'%';
    c[4].lastChild.textContent=Math.round(m.yes)+'%';
    c[5].textContent=Math.round(m.yes)+'c'; c[6].textContent=no+'c';
    c[7].innerHTML=usd(m.vol)+'<s>'+fmt(m.trades)+' fills · '+fmtLeft(m)+'</s>';
  });
}

/* ---------- feeds ---------- */
function feedRow(box,html,cls,max){
  const d=document.createElement('div'); d.className=cls+' new'; d.innerHTML=html;
  box.insertBefore(d,box.firstChild); while(box.children.length>max)box.removeChild(box.lastChild);
}
function pushLaunch(m){
  feedRow($('launches'), avatar(m.t,true)+'<span class="tk">$'+m.sym+'</span><span>'+usd(m.cap)+'</span>'+
    '<span class="r">market '+Math.round(m.yes)+'c</span>','frow',8);
}
function pushSettled(m,won,pay){
  const box=$('rescards'), c=document.createElement('div');
  c.className='rcard in '+(won?'won':'lost');
  c.innerHTML='<div class="top">'+avatar(m.t,true)+'<span class="tk">$'+m.sym+'</span>'+
    '<span class="stamp '+(won?'won':'lost')+'">'+(won?'WON':'LOST')+'</span></div>'+
    '<div class="q">'+questionOf(m).replace(/<[^>]+>/g,'')+'</div>'+
    '<div class="bot"><span class="lb">PAYOUT</span><span class="pay">'+(won?'+':'-')+usd(pay)+'</span></div>';
  box.insertBefore(c,box.firstChild); while(box.children.length>6)box.removeChild(box.lastChild);
  $('h_res').textContent=settled;
}
const WALLETS=['0x7f2a','0xbe10','0x33d9','0xa41c','0x0f8e','0xc7b2','0x91da'];
const LB=WALLETS.map((w,i)=>({w:w,pnl:R(5000,54000)*(1-i*.09),wr:R(53,76),h:RI(40,90)}));
LB.push({w:'you',pnl:0,wr:62,h:70,me:true});
function paintLeader(){
  LB.forEach(x=>{ x.me?x.pnl=yourPnl:x.pnl+=R(-160,210) });
  const s=LB.slice().sort((a,b)=>b.pnl-a.pnl), box=$('leader'); box.innerHTML='';
  s.forEach((x,i)=>{const d=document.createElement('div'); d.className='lrow'+(x.me?' me':'');
    d.innerHTML='<span class="rk">'+(i+1)+'</span>'+
      '<span class="av sm" style="width:20px;height:20px;font-size:7px;background:linear-gradient(140deg,hsl('+x.h+',100%,60%),hsl('+(x.h-18)+',100%,50%))">'+
        (x.me?'YOU':x.w.slice(2,4).toUpperCase())+'</span>'+
      '<span class="w">'+(x.me?'your wallet':x.w+'…')+'</span>'+
      '<span class="wr">'+x.wr.toFixed(0)+'%</span>'+
      '<span class="pnl" style="color:'+(x.pnl>=0?'var(--acid)':'var(--red)')+'">'+money(x.pnl)+'</span>';
    box.appendChild(d)});
}
let POS=[];
function paintPositions(){
  POS=POS.filter(p=>p.m&&p.m.status==='live');
  while(POS.length<5){const m=pick(markets.filter(x=>x.status==='live')); if(!m)break;
    POS.push({m:m,yes:Math.random()<.7,entry:clamp(Math.round(m.yes)+RI(-9,9),3,96),size:RI(2,24)*100})}
  const box=$('positions'); box.innerHTML='';
  POS.forEach(p=>{
    const cur=p.yes?p.m.yes:100-p.m.yes, pnl=(cur-p.entry)/100*p.size;
    const d=document.createElement('div'); d.className='prow';
    d.innerHTML='<span class="av sm" style="width:16px;height:16px;border-radius:5px;font-size:6px;background:linear-gradient(140deg,hsl('+(60+hueOf(p.m.sym)%40)+',100%,60%),hsl('+(40+hueOf(p.m.sym)%30)+',100%,50%))">'+p.m.sym.slice(0,2)+'</span>'+
      '<span class="tk">$'+p.m.sym+'</span><span class="sd '+(p.yes?'y':'n')+'">'+(p.yes?'YES':'NO')+'</span>'+
      '<span>'+p.entry+'c</span><span class="r '+(pnl>=0?'up':'down')+'">'+money(pnl)+'</span>';
    box.appendChild(d)});
}
let bookB=[],bookA=[];
function seedBook(){bookB=[];bookA=[];for(let i=0;i<6;i++){bookB.push(R(.5,3.8));bookA.push(R(.5,3.8))}}
function paintBook(){
  const m=hero||markets[0]; if(!m)return;
  const mid=clamp(Math.round(m.yes),8,92);
  $('m_dom').textContent='$'+m.sym+' · yes shares';
  for(let i=0;i<6;i++){bookA[i]=clamp(bookA[i]+R(-.45,.45),.25,4.4);bookB[i]=clamp(bookB[i]+R(-.45,.45),.25,4.4)}
  const mx=Math.max.apply(null,bookA.concat(bookB));
  let h='';
  for(let i=5;i>=0;i--)h+='<div class="drow a"><span class="fill" style="width:'+(bookA[i]/mx*84)+'%"></span>'+
    '<span class="px">'+(mid+1+i)+'c</span><span class="sz">'+(bookA[i]*1000).toFixed(0)+'</span></div>';
  h+='<div id="spread"><span>best bid / ask</span><b>'+mid+'c</b><span>'+(Math.random()<.5?'1c':'2c')+' wide</span></div>';
  for(let i=0;i<6;i++)h+='<div class="drow b"><span class="fill" style="width:'+(bookB[i]/mx*84)+'%"></span>'+
    '<span class="px">'+(mid-1-i)+'c</span><span class="sz">'+(bookB[i]*1000).toFixed(0)+'</span></div>';
  $('dom').innerHTML=h;
}
function pushTrade(){
  const m=(hero&&Math.random()<.6)?hero:pick(markets); if(!m)return;
  const yes=Math.random()<(m.yes/100*.7+.18), px=clamp(Math.round(yes?m.yes:100-m.yes)+RI(-1,1),1,99), sz=RI(2,90)*25;
  feedRow($('tape'),'<span>'+new Date().toISOString().slice(14,19)+'</span>'+
    '<span class="side '+(yes?'y':'n')+'">'+(yes?'YES':'NO')+'</span>'+
    '<span class="px">'+px+'c</span><span>$'+m.sym+'</span>'+
    '<span class="r">'+fmt(sz)+'</span>','trow',10);
  if(m.el){m.el.classList.remove('flash');void m.el.offsetWidth;m.el.classList.add('flash')}
}

/* ---------- focus canvas: the token's own tape ---------- */
const fc=$('focus'), fx2=fc.getContext('2d'); const dpr=Math.max(1,devicePixelRatio||1);
let fw=0,fh=0;
function drawFocus(){
  const r=fc.getBoundingClientRect(); fw=r.width; fh=r.height;
  fc.width=fw*dpr; fc.height=fh*dpr; fx2.setTransform(dpr,0,0,dpr,0,0);
  fx2.clearRect(0,0,fw,fh);
  const m=hero||markets[0]; if(!m){requestAnimationFrame(drawFocus);return}
  const L=8,Rr=fw-58,T=30,B=fh-44,H=B-T,W=Rr-L;
  const seen=m.caps.slice(0,m.i+1), win=seen.slice(-90);
  const hi=Math.max(m.target*1.05,...win), lo=Math.min(...win)*.985;
  const Y=v=>B-H*clamp((v-lo)/((hi-lo)||1),0,1);
  fx2.fillStyle='#5C6250';fx2.font='9px "JetBrains Mono",monospace';fx2.textAlign='left';
  fx2.fillText('$'+m.sym+' CAP FROM THE CURVE TAPE',L,14);
  fx2.textAlign='right';fx2.fillStyle='#fff';fx2.font='700 11px "JetBrains Mono",monospace';
  fx2.fillText(usd(m.cap),fw-6,14);
  fx2.strokeStyle='#161A11';fx2.lineWidth=1;
  for(let k=0;k<=3;k++){const y=T+H*k/3;fx2.beginPath();fx2.moveTo(L,y);fx2.lineTo(Rr,y);fx2.stroke()}
  const ty=Y(m.target);
  fx2.setLineDash([5,4]);fx2.strokeStyle='#FFD400';fx2.lineWidth=1.4;
  fx2.beginPath();fx2.moveTo(L,ty);fx2.lineTo(fw-6,ty);fx2.stroke();fx2.setLineDash([]);
  fx2.fillStyle='#FFD400';fx2.font='700 9px "JetBrains Mono",monospace';fx2.textAlign='left';
  fx2.fillText('TARGET '+usd(m.target),L+3,ty-5);
  if(win.length>2){
    const n=win.length;
    fx2.beginPath();
    win.forEach((v,i)=>{const x=L+W*i/(n-1),y=Y(v);i?fx2.lineTo(x,y):fx2.moveTo(x,y)});
    fx2.lineTo(L+W,B);fx2.lineTo(L,B);fx2.closePath();
    const g=fx2.createLinearGradient(0,T,0,B);
    g.addColorStop(0,'rgba(200,255,0,.28)');g.addColorStop(1,'rgba(200,255,0,0)');
    fx2.fillStyle=g;fx2.fill();
    fx2.beginPath();
    win.forEach((v,i)=>{const x=L+W*i/(n-1),y=Y(v);i?fx2.lineTo(x,y):fx2.moveTo(x,y)});
    fx2.strokeStyle='#C8FF00';fx2.lineWidth=2.2;fx2.stroke();
    const lx=L+W,ly=Y(win[n-1]);
    fx2.beginPath();fx2.arc(lx,ly,4,0,7);fx2.fillStyle='#C8FF00';fx2.fill();
    fx2.beginPath();fx2.arc(lx,ly,4+4*(1+Math.sin(now()/170))/2,0,7);
    fx2.strokeStyle='rgba(200,255,0,.55)';fx2.lineWidth=1.3;fx2.stroke();
  }
  const pT=B+14;
  fx2.fillStyle='#5C6250';fx2.font='9px "JetBrains Mono",monospace';fx2.textAlign='left';
  fx2.fillText('YES',L,pT+9);
  const px0=L+30,pw=Rr-px0;
  fx2.fillStyle='#14180E';fx2.fillRect(px0,pT,pw,11);
  fx2.fillStyle='#C8FF00';fx2.fillRect(px0,pT,pw*m.yes/100,11);
  fx2.fillStyle='#fff';fx2.font='700 12px "JetBrains Mono",monospace';fx2.textAlign='right';
  fx2.fillText(Math.round(m.yes)+'c',fw-6,pT+10);
  if(m.hist.length>2){
    const hT=pT+18,hH=fh-hT-4;
    fx2.beginPath();
    m.hist.forEach((v,i)=>{const x=L+W*i/(m.hist.length-1),y=hT+hH-hH*v/100;i?fx2.lineTo(x,y):fx2.moveTo(x,y)});
    fx2.strokeStyle='rgba(255,255,255,.45)';fx2.lineWidth=1.2;fx2.stroke();
  }
  requestAnimationFrame(drawFocus);
}

/* ---------- cycle ---------- */
function settle(m,won){
  m.status='settled'; settled++;
  const pay=Math.round(R(2600,11000));
  yourPnl+=won?pay*.4:-pay*.16;
  pushSettled(m,won,pay);
  if(m.hero){
    $('b_big').textContent=won?'RESOLVED YES':'RESOLVED NO';
    $('b_sub').textContent='$'+m.sym+' crossed '+usd(m.target)+' · last print '+usd(m.cap);
    $('b_pay').textContent=fmt(RI(210,980))+' wallets paid · '+usd(RI(70000,260000))+' settled on chain';
    const b=$('burst'); b.classList.remove('show'); void b.offsetWidth; b.classList.add('show');
  }
  if(m.el){const el=m.el,id=m.id; el.classList.add('out');
    setTimeout(()=>{ if(el.parentNode)el.parentNode.removeChild(el);
      markets=markets.filter(x=>x.id!==id);
      if(markets.length<12){const t=pick(TOKENS),n=mkMarket(t,false);pushLaunch(n);renderBoard()} },800)}
}
function startCycle(){
  markets.forEach(m=>{if(m.el&&m.el.parentNode)m.el.parentNode.removeChild(m.el)});
  markets=[]; hero=null; heroPhase='wait'; $('rows').innerHTML='';
  const pool=TOKENS.slice();
  for(let i=0;i<11&&pool.length;i++)mkMarket(pool.splice(RI(0,pool.length-1),1)[0],false);
  renderBoard();
}
function tick(){
  const p=cyclePos();
  if(p<.02&&heroPhase==='done')startCycle();
  if(heroPhase==='wait'&&p>.05){
    /* the hero is the token whose own tape climbs hardest inside the window */
    const best=TOKENS.slice().sort((a,b)=>
      (Math.max.apply(null,b.caps)/b.caps[0])-(Math.max.apply(null,a.caps)/a.caps[0]))[0];
    /* the hero must not double a row that is already on the board */
    markets.filter(m=>m.t===best).forEach(m=>{
      if(m.el&&m.el.parentNode)m.el.parentNode.removeChild(m.el);
      markets=markets.filter(x=>x!==m);
    });
    hero=mkMarket(best,true); heroPhase='live';
    pushLaunch(hero); renderBoard();
    $('m_focus').textContent='$'+hero.sym+' · target '+usd(hero.target);
  }
  markets.forEach(m=>{
    if(m.status!=='live')return;
    /* replay the token's own fills */
    const span=m.hero?.80:1.6, step=m.caps.length/(CYCLE*span/60);
    m.i=Math.min(m.caps.length-1,m.i+step);
    m.cap=m.caps[Math.floor(m.i)];
    m.yes+=(priceOdds(m)-m.yes)*.12+R(-.35,.35); m.yes=clamp(m.yes,2,98);
    m.hist.push(m.yes); if(m.hist.length>60)m.hist.shift();
    m.vol+=R(0,420);
    if(m.hero&&m.kind==='cross'&&m.cap>=m.target){ settle(m,true); heroPhase='done'; return }
    if(timeLeft(m)<=0) settle(m,m.kind==='cross'?m.cap>=m.target:m.cap>=m.target);
  });
  paintBoard();
  $('blk').textContent=fmt(SNAP.chain.head_block+Math.floor(now()/101));
  $('curves').textContent=fmt(SNAP.curves_seen);
  $('h_vol').textContent=usd(SNAP.tokens.reduce((s,t)=>s+t.vol_usd,0));
  $('h_cap').textContent=usd(Math.max.apply(null,TOKENS.map(t=>t.caps[t.caps.length-1])));
  const pl=$('h_pnl'); pl.textContent=money(yourPnl); pl.className='v '+(yourPnl>=0?'acid':'red');
  const s=Math.floor(now()/1000); $('clock').textContent=pad2(Math.floor(s/60))+':'+pad2(s%60);
}
function paintStrip(){
  const one=TOKENS.slice(0,12).map(t=>{
    const a=t.caps[0],b=t.caps[t.caps.length-1],ch=(b/a-1)*100;
    return '<span><b>$'+t.sym+'</b> '+usd(b)+' <i class="'+(ch>=0?'u':'d')+'">'+(ch>=0?'▲':'▼')+Math.abs(ch).toFixed(1)+'%</i></span>';
  }).join('');
  $('stripin').innerHTML=one+one;
}
$('tickin').innerHTML=[
 '<b>CAPS, VOLUMES AND PRICE PATHS</b> read from robinhood chain · '+SNAP.curves_seen+' curves traded in the scanned window',
 '<b>SNAPSHOT</b> '+SNAP.generated_at+' · head block '+SNAP.chain.head_block.toLocaleString('en-US')+' · chain id '+SNAP.chain.id,
 '<b>MARKETS</b> a target is a round cap above the token · yes and no shares are priced in cents and add up to a dollar',
 '<b>RESOLUTION</b> the cap at the deadline is read off the curve, nobody votes on it',
 '<b>PREVIEW</b> odds, order book and payouts on this sheet are a product preview, not live trading'
].map(s=>'<span>'+s+'</span>').join('').repeat(2);

startCycle(); seedBook(); paintLeader(); paintPositions(); paintStrip(); drawFocus();
for(let i=0;i<8;i++)pushLaunch(markets[i%markets.length]);
/* the settled rail is never empty on frame one: the session already closed a few */
(function(){ for(let i=0;i<4;i++){ const t=pick(TOKENS); if(!t)break;
  const caps=t.caps, last=caps[caps.length-1], won=(i%2===0);
  const m={t:t,sym:t.sym,target:niceAbove(caps[0]),cap:last,kind:'cross',born:now()-60000,life:60000};
  settled++; pushSettled(m,won,Math.round(R(2600,9800))); } })();
setInterval(tick,60);
setInterval(pushTrade,300);
setInterval(paintBook,420);
setInterval(paintPositions,1100);
setInterval(paintLeader,2800);

if(new URLSearchParams(location.search).get('debug')){setTimeout(()=>{const d=document.createElement('pre');d.id='dbg';
  d.textContent=['err='+window.__err,'tokens='+TOKENS.length,'markets='+markets.length,
   'hero='+(hero?hero.sym:'-')+' '+heroPhase,'settled='+settled,'rows='+$('rows').children.length].join('\n');
  document.body.appendChild(d)},4000)}
</script></body></html>"""

NAME = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "PREDLY"
out = D / "board.html"
split = max(2, len(NAME) - 2)
brand_html = NAME[:split] + "<b>" + NAME[split:] + "</b>"
html = (HTML.replace("__BRAND_HTML__", brand_html)
            .replace("__CSS__", CSS)
            .replace("__SNAP__", json.dumps(SNAP, ensure_ascii=False))
            .replace("__NAME__", NAME))
out.write_text(html, encoding="utf-8")
print(f"written {out} ({len(html):,} bytes) · {len(SNAP['tokens'])} tokens from block {SNAP['chain']['head_block']:,}")

if "--shot" in sys.argv:
    ms = sys.argv[sys.argv.index("--shot") + 1] if len(sys.argv) > sys.argv.index("--shot") + 1 else "40000"
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    png = D.parent / "assets" / "board.png"
    subprocess.run([edge, "--headless=new", "--disable-gpu", f"--screenshot={png}",
                    "--window-size=1920,1080", f"--virtual-time-budget={ms}",
                    "--hide-scrollbars", out.as_uri()], check=False)
    print("shot ->", png)
