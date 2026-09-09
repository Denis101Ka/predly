"""Fill data/snapshot-latest.json with each token's launch metadata and its real logo.

Runs on the snapshot fetch_chain.py already wrote, so it costs two RPC calls per token
instead of another full log scan. The launch image lives in the creation transaction,
usually as an ipfs uri, and is thumbnailed to 96 px so board.html stays one file.

  python fetch_logos.py [pace_seconds] [--refresh]
"""
import base64, io, json, pathlib, re, sys, time, urllib.request

RPC = "https://rpc.mainnet.chain.robinhood.com"
TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x" + "0" * 64
GATEWAYS = ["https://gateway.pinata.cloud/ipfs/", "https://4everland.io/ipfs/",
            "https://ipfs.io/ipfs/", "https://dweb.link/ipfs/"]
SOCIAL = ("x.com", "twitter.com", "t.me", "youtube.com", "discord.gg", "instagram.com")

D = pathlib.Path(__file__).resolve().parent
SNAP = D.parent / "data" / "snapshot-latest.json"
LOGOS = D.parent / "data" / "logos"
PACE = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else 0.45


def rpc(method, params, tries=6):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": "board/0.1"})
    for i in range(tries):
        try:
            out = json.load(urllib.request.urlopen(req, timeout=60))
            time.sleep(PACE)
            if "error" in out:
                raise RuntimeError(out["error"])
            return out["result"]
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep((6.0 if "429" in str(e) else 1.5) * (i + 1))


def birth_log(token, first_block):
    """the mint: one Transfer out of the zero address, emitted when the launchpad creates the token"""
    for span in (200_000, 900_000, 4_000_000):
        try:
            r = rpc("eth_getLogs", [{"address": token, "topics": [TR, ZERO],
                                     "fromBlock": hex(max(0, first_block - span)),
                                     "toBlock": hex(first_block + 10)}], tries=3)
            if r:
                return r[0]
        except Exception as e:
            print("    logs:", str(e)[:60])
    return None


def strings_in(hexinput):
    raw = bytes.fromhex(hexinput[2:] if hexinput.startswith("0x") else hexinput)
    return [m.decode("utf-8", "ignore") for m in re.findall(rb"[\x20-\x7e]{6,}", raw)]


def readable(v):
    return bool(v) and sum(c.isalnum() or c == " " for c in v) / len(v) > .75


def creation_meta(token, first_block):
    lg = birth_log(token, first_block)
    if not lg:
        return {}
    tx = rpc("eth_getTransactionByHash", [lg["transactionHash"]], tries=3)
    out = {"birth_block": int(lg["blockNumber"], 16), "birth_tx": lg["transactionHash"],
           "launchpad": tx.get("to")}
    ipfs, links, socials, plain = [], [], [], []
    for s in strings_in(tx.get("input", "0x")):
        s = s.strip()
        j = s.find("ipfs://")
        if j >= 0:
            ipfs.append(s[j + 7:].split()[0].strip("/"))
            continue
        i = s.find("http")
        if i >= 0:
            u = s[i:].split()[0]
            (socials if any(d in u for d in SOCIAL) else links).append(u)
            continue
        if 2 < len(s) < 60 and readable(s):
            plain.append(s)
    if plain:
        out["long_name"] = plain[0]
    if len(plain) > 1:
        out["blurb"] = max(plain[1:], key=len)[:120]
    if socials:
        out["post"] = socials[0]
    if links:
        out["site"] = links[0]
    if ipfs:
        out["logo_cid"] = ipfs[0]
    elif links:
        out["logo_url"] = links[0]
    return out


def http_get(url, cap=3_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    r = urllib.request.urlopen(req, timeout=30)
    return (r.headers.get("Content-Type") or "").split(";")[0], r.read(cap)


def thumb(blob, box=96):
    """a 96 px square png · a 400 kB launch image has no business inside the sheet"""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(blob))
        if getattr(im, "is_animated", False):
            im.seek(0)
        im = im.convert("RGBA")
        w, h = im.size
        side = min(w, h)
        im = im.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
        im = im.resize((box, box), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        return buf.getvalue()
    except Exception as e:
        print("    thumb failed:", str(e)[:60])
        return None


def fetch_logo(meta, key):
    LOGOS.mkdir(exist_ok=True)
    cache, mime = LOGOS / (key + ".bin"), LOGOS / (key + ".type")
    if cache.exists() and mime.exists():
        return "data:" + mime.read_text().strip() + ";base64," + base64.b64encode(cache.read_bytes()).decode()
    urls = []
    if meta.get("logo_cid"):
        urls += [g + meta["logo_cid"] for g in GATEWAYS]
    if meta.get("logo_url"):
        urls.append(meta["logo_url"])
    seen = set()
    while urls:
        u = urls.pop(0)
        if u in seen:
            continue
        seen.add(u)
        try:
            ct, blob = http_get(u)
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
            small = thumb(blob)
            if not small:
                continue
            cache.write_bytes(small)
            mime.write_text("image/png")
            return "data:image/png;base64," + base64.b64encode(small).decode()
    return None


def main():
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    force = "--refresh" in sys.argv
    got = 0
    for t in snap["tokens"]:
        sym = t.get("symbol") or (t.get("token") or t["curve"])[:10]
        if not t.get("token"):
            print("  %12s  no token address" % sym)
            continue
        meta = t.get("meta") or {}
        if force or not (meta.get("logo_cid") or meta.get("logo_url")) or not readable(meta.get("long_name")):
            try:
                meta = creation_meta(t["token"], t["first_block"]) or meta
            except Exception as e:
                print("  %12s  meta failed: %s" % (sym, str(e)[:50]))
        t["meta"] = meta
        logo = t.get("logo")
        if force or not logo or len(logo) > 60_000:
            logo = fetch_logo(meta, re.sub(r"[^A-Za-z0-9_-]", "_", sym)[:14])
            t["logo"] = logo
        if logo:
            got += 1
        print("  %12s  %-26s logo %s %4d kB" % (sym, str(meta.get("long_name", ""))[:26],
                                                "yes" if logo else "no ", len(logo or "") // 1024))
    snap["logos_at"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    SNAP.write_text(json.dumps(snap, indent=1), encoding="utf-8")
    print("\n%d/%d logos, snapshot %s bytes" % (got, len(snap["tokens"]), f"{SNAP.stat().st_size:,}"))


if __name__ == "__main__":
    main()
