"""Pull the busiest live tokens off Robinhood Chain into data/snapshot-latest.json.

Nothing here is invented. Every token in the snapshot traded on the launchpad curve
inside the scanned window, the price is the executed ratio of quote to tokens out of
the curve event, and the cap is that price times the fixed 1e9 supply.
"""
import json, pathlib, sys, time, urllib.request

RPC = "https://rpc.mainnet.chain.robinhood.com"
BUY = "0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455"
SELL = "0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df"
POOL = "0x52e65b17fb6e5ba00ed806f37afcd2daa50271ca"      # eth/usdg, slot0 for the fx rate
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "snapshot-latest.json"

WINDOW = int(sys.argv[1]) if len(sys.argv) > 1 else 90_000   # blocks back, 101 ms each
CHUNK = 2_500
TOP = 14


def rpc(method, params, tries=5):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": "board/0.1"})
    for i in range(tries):
        try:
            out = json.load(urllib.request.urlopen(req, timeout=60))
            time.sleep(0.06)                      # the public rpc rate limits hard
            if "error" in out:
                raise RuntimeError(out["error"])
            return out["result"]
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep((4.0 if "429" in str(e) else 1.2) * (i + 1))
    return None


def word(data, i):
    h = data[2:]
    return int(h[i * 64:(i + 1) * 64] or "0", 16)


def price_of(log):
    """word0 quote, word1 tokens on a buy, swapped on a sell. the ratio is the fill."""
    is_buy = log["topics"][0] == BUY
    w0, w1 = word(log["data"], 0), word(log["data"], 1)
    quote_raw, tok_raw = (w0, w1) if is_buy else (w1, w0)
    if tok_raw == 0:
        return None
    usdg = quote_raw < 10 ** 12
    q = quote_raw / (1e6 if usdg else 1e18)
    t = tok_raw / 1e18
    if not (q > 0 and t > 0):
        return None
    if (q > 2e6) if usdg else (q > 200):
        return None                                   # quote token misread, drop the fill
    return {"buy": is_buy, "price": q / t, "quote": q, "tokens": t,
            "unit": "USDG" if usdg else "ETH", "block": int(log["blockNumber"], 16)}


def call(to, selector):
    try:
        return rpc("eth_call", [{"to": to, "data": selector}, "latest"])
    except Exception:
        return None


def decode_string(hexstr):
    if not hexstr or len(hexstr) < 130:
        return None
    try:
        n = int(hexstr[2 + 64:2 + 128], 16)
        raw = bytes.fromhex(hexstr[2 + 128:2 + 128 + n * 2])
        s = raw.decode("utf-8", "ignore").strip()
        return s if s and all(31 < ord(c) < 127 for c in s) else None
    except Exception:
        return None


def eth_usd():
    r = call(POOL, "0x3850c7bd")                      # slot0
    if not r:
        return None
    sq = int(r[2:66], 16) / 2 ** 96
    return sq * sq * 1e12



TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x" + "0" * 64
LOGOS = pathlib.Path(__file__).resolve().parent.parent / "data" / "logos"


def birth_of(token, first_block):
    """the mint log: a Transfer out of the zero address, one per launchpad token"""
    for span in (300_000, 1_500_000, 6_000_000):
        try:
            r = rpc("eth_getLogs", [{"address": token, "topics": [TR, ZERO],
                                     "fromBlock": hex(max(0, first_block - span)),
                                     "toBlock": hex(first_block + 10)}], tries=2)
            if r:
                return r[0]
        except Exception:
            continue
    return None


def strings_in(hexinput):
    import re
    raw = bytes.fromhex(hexinput[2:]) if hexinput.startswith("0x") else bytes.fromhex(hexinput)
    return [m.decode("utf-8", "ignore") for m in re.findall(rb"[ -~]{6,}", raw)]


def creation_meta(token, first_block):
    """name, logo and the post the launch pointed at, straight out of the creation tx"""
    lg = birth_of(token, first_block)
    if not lg:
        return {}
    try:
        tx = rpc("eth_getTransactionByHash", [lg["transactionHash"]], tries=2)
    except Exception:
        return {}
    out = {"birth_block": int(lg["blockNumber"], 16), "birth_tx": lg["transactionHash"],
           "launchpad": tx.get("to")}
    ipfs, links, socials = [], [], []
    SOCIAL = ("x.com", "twitter.com", "t.me", "youtube.com", "discord.gg", "instagram.com")
    for s0 in strings_in(tx.get("input", "0x")):
        s0 = s0.strip()
        j = s0.find("ipfs://")
        if j >= 0:
            ipfs.append(s0[j + 7:].split()[0].strip("/"))
            continue
        i = s0.find("http")
        if i >= 0:
            u = s0[i:].split()[0]
            (socials if any(d in u for d in SOCIAL) else links).append(u)
            continue
        if 2 < len(s0) < 42 and "long_name" not in out and not s0.startswith("0x"):
            out["long_name"] = s0
    if socials:
        out["post"] = socials[0]
    if ipfs:
        out["logo_cid"] = ipfs[0]
    elif links:
        out["logo_url"] = links[0]
    if links:
        out["site"] = links[0]
    return out


GATEWAYS = ["https://ipfs.io/ipfs/", "https://cloudflare-ipfs.com/ipfs/", "https://dweb.link/ipfs/"]


def _get(url, cap=400_000):
    import urllib.error
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=25)
    ct = (r.headers.get("Content-Type") or "").split(";")[0]
    return ct, r.read(cap)


def fetch_logo(meta, key):
    """launch image, cached on disk, returned as a data uri · ipfs first, then any plain link"""
    import base64
    LOGOS.mkdir(exist_ok=True)
    cache, mime = LOGOS / (key + ".bin"), LOGOS / (key + ".type")
    if cache.exists() and mime.exists():
        return "data:" + mime.read_text().strip() + ";base64," + base64.b64encode(cache.read_bytes()).decode()

    urls = []
    if meta.get("logo_cid"):
        urls += [g + meta["logo_cid"] for g in GATEWAYS]
    if meta.get("logo_url"):
        urls.append(meta["logo_url"])

    for u in urls:
        try:
            ct, blob = _get(u)
        except Exception:
            continue
        if ct.startswith("application/json") or blob[:1] == b"{":
            try:
                img = json.loads(blob.decode("utf-8", "ignore")).get("image", "")
                if img.startswith("ipfs://"):
                    urls += [g + img[7:].strip("/") for g in GATEWAYS]
                elif img.startswith("http"):
                    urls.append(img)
            except Exception:
                pass
            continue
        if ct.startswith("image") and len(blob) > 200:
            cache.write_bytes(blob)
            mime.write_text(ct)
            return "data:" + ct + ";base64," + base64.b64encode(blob).decode()
    return None


def main():
    head = int(rpc("eth_blockNumber", []), 16)
    start = head - WINDOW
    print(f"head {head:,} · scanning {WINDOW:,} blocks back to {start:,}")

    curves, calls = {}, 0
    frm = start
    while frm <= head:
        to = min(frm + CHUNK - 1, head)
        try:
            logs = rpc("eth_getLogs", [{"fromBlock": hex(frm), "toBlock": hex(to),
                                        "topics": [[BUY, SELL]]}])
            calls += 1
        except Exception as e:
            print("  chunk failed, halving:", str(e)[:80])
            if CHUNK > 500:
                to = frm + 499
                logs = rpc("eth_getLogs", [{"fromBlock": hex(frm), "toBlock": hex(to),
                                            "topics": [[BUY, SELL]]}])
            else:
                logs = []
        for lg in logs:
            tr = price_of(lg)
            if not tr:
                continue
            c = curves.setdefault(lg["address"].lower(),
                                  {"curve": lg["address"].lower(), "trades": 0, "vol_eth": 0.0,
                                   "vol_usdg": 0.0, "first": None, "last": None, "unit": tr["unit"],
                                   "first_block": tr["block"], "last_block": tr["block"], "path": []})
            c["trades"] += 1
            c["unit"] = tr["unit"]
            if tr["unit"] == "ETH":
                c["vol_eth"] += tr["quote"]
            else:
                c["vol_usdg"] += tr["quote"]
            if c["first"] is None:
                c["first"] = tr["price"]
            c["last"] = tr["price"]
            c["last_block"] = max(c["last_block"], tr["block"])
            c["first_block"] = min(c["first_block"], tr["block"])
            c["path"].append(round(tr["price"], 18))
        print(f"  {frm:,}-{to:,}  logs {len(logs):>5}  curves {len(curves):>4}")
        frm = to + 1

    px = eth_usd() or 0
    for c in curves.values():
        c["vol_usd"] = c["vol_eth"] * px + c["vol_usdg"]

    # a curve with nine fills and a six figure "volume" is a misread quote, not a live meme
    live = [c for c in curves.values()
            if c["trades"] >= 40 and 4_000 <= (c["last"] or 0) * 1e9 * (px if c["unit"] == "ETH" else 1) <= 8e7]
    ranked = sorted(live, key=lambda c: (c["vol_usd"], c["trades"]), reverse=True)[:TOP]
    print(f"\n{len(curves)} curves traded · resolving the top {len(ranked)}")

    out = []
    for c in ranked:
        tok = None
        r = call(c["curve"], "0xfc0c546a")            # token()
        if r and len(r) >= 66:
            a = "0x" + r[26:66].lower()
            if a != "0x" + "0" * 40:
                tok = a
        sym = name = None
        if tok:
            sym = decode_string(call(tok, "0x95d89b41"))     # symbol()
            name = decode_string(call(tok, "0x06fdde03"))    # name()
        try:
            meta = creation_meta(tok, c["first_block"]) if tok else {}
        except Exception as e:
            print("   meta failed:", str(e)[:60]); meta = {}
        try:
            logo = fetch_logo(meta, (sym or tok or c["curve"])[:14].replace("/", "_").replace(" ", "_"))
        except Exception as e:
            print("   logo failed:", str(e)[:60]); logo = None
        cap_quote = (c["last"] or 0) * 1e9
        c.update({"meta": meta, "logo": logo,
                  "token": tok, "symbol": sym, "name": name,
                  "cap_quote": cap_quote,
                  "cap_usd": cap_quote * px if c["unit"] == "ETH" else cap_quote,
                  "path": c["path"][-160:]})
        out.append(c)
        print(f"  {sym or (tok or c['curve'])[:10]:>12}  trades {c['trades']:>4}  "
              f"vol ${c['vol_usd']:>10,.0f}  cap ${c['cap_usd']:>12,.0f}  "
              f"logo {'yes' if logo else 'no ':>3}  {meta.get('long_name','')[:22]}")

    snap = {"generated_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
            "chain": {"name": "Robinhood Chain", "id": 4663, "rpc": RPC,
                      "head_block": head, "scanned_blocks": WINDOW, "block_ms": 101},
            "eth_usd": round(px, 2), "rpc_calls": calls,
            "curves_seen": len(curves), "tokens": out}
    OUT.write_text(json.dumps(snap, indent=1), encoding="utf-8")
    print(f"\nwritten {OUT}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
