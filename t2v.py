#!/usr/bin/env .venv/bin/python
"""Threads post -> 9:16 video.
  scrape <url>      -> out/<code>/project.json (scenes = original post + spam-filtered comments, candidates = all comments)
  info <project>    -> summary table (spam, estimated length, memes) for reviewing/editing
  memes [dir]       -> list the meme library
  render <project>  -> MP4 (--only N / --preview for a quick look)
  transcribe <mp4>  -> transcribe with Whisper (check the voice-over / a reference video)
  assets            -> download music/backgrounds/memes/sounds listed in assets/manifest.json
  login             -> log into Threads once (separate browser) to scrape more comments
"""
import argparse, asyncio, base64, hashlib, html, json, math, random, re, subprocess, sys, time, urllib.request
from pathlib import Path

REPLY_KEYS = ("direct_replies", "self_thread", "pinned_replies")
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+")
IMG = (".png", ".jpg", ".jpeg", ".webp")
CPS = 14  # ~chars/second of vi-VN-HoaiMy at +20%, only used for estimates
SPAM = [  # (regex, reason) applied to comments only, never to the original post.
    # The patterns are Vietnamese on purpose (the tool targets Vietnamese Threads): job/ad/follow-bait keywords.
    (r"(?:\+?84|0)[\s.]?\d(?:[\s.]?\d){8,9}", "phone number"),
    (r"https?://|www\.|\b\w+\.(?:com|vn|online|net|me|vip)\b", "link"),
    (r"tuyển|\bctv\b|cộng tác viên|việc làm|job onl|nhận job|\bib\b|inbox|zalo|telegram|kiếm tiền|hoa hồng|"
     r"bán tài khoản|\bfl\b|follow|spotify|capcut|netflix|canva|\bjob\b|rải đơn|kiếm công|idol live", "ad / follow-bait"),
]


LEXICON = Path(__file__).with_name("lexicon.json")  # slang/abbrev/hard words -> how they should be spoken
# Number/abbreviation rules for Vietnamese speech (e.g. "3h" -> "3 giờ" = "3 o'clock", "5tr" -> "5 triệu" = "5 million")
RULES = [(r"=+\)+|:+\)+|:v\b|:\(+", " "), (r"(\d+)h(\d+)", r"\1 giờ \2"), (r"(\d+)h\b", r"\1 giờ"),
         (r"(\d+)/(\d+)", r"\1 trên \2"), (r"(\d+)tr\b", r"\1 triệu"), (r"(\d+)[mM]\b", r"\1 triệu"), (r"(\d+)k\b", r"\1 nghìn")]


def speak(t):
    """Final text sent to TTS: clean + number rules + lexicon (whole words, any case)."""
    t = tts_clean(t)
    for rx, to in RULES:
        t = re.sub(rx, to, t)
    lex = json.loads(LEXICON.read_text()) if LEXICON.exists() else {}
    for w, to in lex.items():
        t = re.sub(rf"(?<!\w){re.escape(w)}(?!\w)", to, t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


def tts_clean(t):  # TTS reads emoji/URLs/hashtags badly; display text stays untouched
    t = re.sub(r"https?://\S+|#\S+", " ", t)
    return re.sub(r"\s+", " ", EMOJI.sub(" ", t)).strip()


def spam_reason(text, seen):
    low = text.lower()
    for rx, why in SPAM:
        if re.search(rx, low):
            return why
    if re.search(r"@[\w.]", text) and len(re.sub(r"@[\w.]+", "", text).strip()) < 25:
        return "tag only"
    if len(text.strip()) < 3:
        return "too short"
    if len(text) > 500:
        return "too long"
    if low in seen:
        return "duplicate"
    seen.add(low)
    return None


def ago(ts):
    s = max(0, time.time() - (ts or 0))
    for sec, u in ((604800, "w"), (86400, "d"), (3600, "h"), (60, "m")):
        if s >= sec:
            return f"{int(s // sec)}{u}"
    return "1m"


def posts(o, in_reply=False):
    """Yield (is_reply, post) for every Threads post dict in the embedded SSR JSON."""
    if isinstance(o, dict):
        if {"code", "like_count", "caption", "user"} <= o.keys() and o["caption"]:
            yield in_reply, o
        for k, v in o.items():
            yield from posts(v, in_reply or k in REPLY_KEYS)
    elif isinstance(o, list):
        for v in o:
            yield from posts(v, in_reply)


PROFILE = Path(__file__).with_name(".profile")  # Playwright-managed browser profile; holds the Threads login from `login`


async def fetch_page(url, scrolls=0):
    """Page HTML + extra posts Threads loads over GraphQL while scrolling (more replies, esp. when logged in)."""
    from playwright.async_api import async_playwright
    net = []

    async def on_resp(r):
        if "/graphql" in r.url:
            try:
                net.extend(p for _, p in posts(await r.json()))
            except Exception:
                pass  # non-JSON / unrelated responses
    async with async_playwright() as p:
        if PROFILE.exists():
            ctx = await p.chromium.launch_persistent_context(str(PROFILE), locale="vi-VN", viewport={"width": 1200, "height": 1800})
        else:
            ctx = await (await p.chromium.launch()).new_context(locale="vi-VN", viewport={"width": 1200, "height": 1800})
        pg = await ctx.new_page()
        pg.on("response", on_resp)
        await pg.goto(url, wait_until="domcontentloaded")
        await pg.wait_for_selector('script[type="application/json"]', state="attached")
        await pg.wait_for_timeout(3000)
        for _ in range(scrolls):
            await pg.mouse.wheel(0, 3000)
            await pg.wait_for_timeout(1200)
        final, content = pg.url, await pg.content()
        await ctx.close()
    return final, content, net


def cmd_login(a):
    """Open a visible Playwright browser so the user logs into Threads once; session is kept in .profile/."""
    async def go():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            ctx = await p.chromium.launch_persistent_context(str(PROFILE), headless=False, locale="vi-VN")
            pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await pg.goto("https://www.threads.com/login")
            print("Log into Threads in the window that just opened, then CLOSE the browser window.")
            await ctx.wait_for_event("close", timeout=0)
    asyncio.run(go())
    print(f"OK: session saved to {PROFILE}")


def make_scene(p, avatar_dir):
    u, info = p["user"], p["text_post_app_info"]
    av = avatar_dir / f"{u['username']}.jpg"
    if not av.exists() and u.get("profile_pic_url"):
        try:
            req = urllib.request.Request(u["profile_pic_url"], headers={"User-Agent": "Mozilla/5.0"})
            av.write_bytes(urllib.request.urlopen(req, timeout=20).read())
        except Exception:
            pass  # card falls back to a plain circle
    imgs = []  # attached photos (carousel or single; for videos this is the poster frame)
    for k, c in enumerate((p.get("carousel_media") or [p])[:4]):
        cand = (c.get("image_versions2") or {}).get("candidates") or []
        if cand:
            f = avatar_dir.parent / "media" / f"{p['code']}_{k}.jpg"
            f.parent.mkdir(exist_ok=True)
            try:
                if not f.exists():
                    req = urllib.request.Request(cand[0]["url"], headers={"User-Agent": "Mozilla/5.0"})
                    f.write_bytes(urllib.request.urlopen(req, timeout=30).read())
                imgs.append(str(f))
            except Exception:
                pass
    text = p["caption"]["text"].strip()
    return {"images": imgs, "type": "card", "user": u["username"], "avatar": str(av) if av.exists() else None,
            "time": ago(p.get("taken_at")), "display": text, "tts": tts_clean(text), "extra": "",
            "memes": [], "likes": p["like_count"], "replies": info.get("direct_reply_count") or 0,
            "reposts": info.get("repost_count") or 0}


def cmd_scrape(a):
    final, content, net = asyncio.run(fetch_page(a.url, a.scroll))
    m = re.search(r"/post/([\w-]+)", final)
    assert m, f"Could not resolve the post link: {final}"
    code = m.group(1)
    found = {}
    for s in re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', content, re.S):
        if "like_count" in s:
            for is_reply, p in posts(json.loads(s)):
                found.setdefault(p["code"], (is_reply, p))
    for p in net:  # replies loaded while scrolling (related posts are not replies, so they're skipped)
        if (p.get("text_post_app_info") or {}).get("is_reply"):
            found.setdefault(p["code"], (True, p))
    assert code in found, "Original post not found (Threads may have changed its page data format)"
    out = Path(a.out or f"out/{code}"); (out / "avatars").mkdir(parents=True, exist_ok=True)
    replies = sorted((p for c, (r, p) in found.items() if r and c != code), key=lambda p: -p["like_count"])
    seen, cands = set(), []
    for p in replies:
        sc = make_scene(p, out / "avatars")
        sc["spam"] = None if a.keep_spam else spam_reason(sc["display"], seen)
        cands.append(sc)
    picked = [c for c in cands if not c["spam"]][:a.n]
    proj = {"url": final, "scenes": [make_scene(found[code][1], out / "avatars"), *({**c} for c in picked)],
            "candidates": cands}
    (out / "project.json").write_text(json.dumps(proj, ensure_ascii=False, indent=2))
    print(f"OK: original post + {len(picked)}/{len(cands)} comments ({sum(1 for c in cands if c['spam'])} spam dropped) -> {out/'project.json'}")


def norm_scene(s):
    """Accept old project.json: 'meme' -> memes[]; fill defaults."""
    s.setdefault("type", "card")
    s.setdefault("memes", [])
    if s.get("meme"):
        s["memes"] = [{"file": s["meme"], "at": "end", "dur": 2}] + s["memes"]
    return s


def cmd_info(a):
    P = json.loads(Path(a.project).read_text())
    tot = 0
    for i, s in enumerate(map(norm_scene, P["scenes"])):
        n = len(s.get("tts", "") + s.get("extra", ""))
        est = n / CPS + 0.4 + sum(m.get("dur", 1.5) for m in s["memes"] if m.get("at") == "end") if s["type"] == "card" \
            else max(s.get("dur", 2.5), len(s.get("tts", "")) / CPS)
        tot += est
        print(f"#{i} {s['type']:5} {s.get('user', s.get('file', '')):22.22} ♡{s.get('likes', '-'):>5} ~{est:4.1f}s "
              f"memes={len(s['memes'])} | {(s.get('display') or s.get('tts') or '')[:50]!r}")
    print(f"Estimated total ≈ {tot:.0f}s")
    for c in P.get("candidates", []):
        if c.get("spam"):
            print(f"  [spam: {c['spam']}] {c['user']}: {c['display'][:50]!r}")


def probe(f, *args):
    r = subprocess.run(["ffprobe", "-v", "error", *args, "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    return r.stdout.strip()


def cmd_memes(a):
    d = Path(a.dir)
    idx = json.loads((d / "index.json").read_text()) if (d / "index.json").exists() else {}
    for f in sorted(d.glob("*")):
        if f.suffix.lower() in IMG + (".gif", ".mp4", ".mov", ".webm"):
            wh = probe(f, "-select_streams", "v:0", "-show_entries", "stream=width,height")
            du = probe(f, "-show_entries", "format=duration")
            du = du if du.replace(".", "").isdigit() else 0  # still images report N/A
            au = "audio" if probe(f, "-select_streams", "a", "-show_entries", "stream=codec_type") else "mute"
            print(f"{f}  {wh}  {float(du or 0):.1f}s  {au}  tag={idx.get(f.name, '?')}")


# ---------------------------------------------------------------- render

def card_html(s, text, fs):
    av = '<div style="width:76px;height:76px;border-radius:50%;background:#ccc"></div>'
    if s.get("avatar") and Path(s["avatar"]).exists():
        b64 = base64.b64encode(Path(s["avatar"]).read_bytes()).decode()
        av = f'<img src="data:image/jpeg;base64,{b64}" style="width:76px;height:76px;border-radius:50%;object-fit:cover">'
    img = ""
    if s.get("show_image", True) and s.get("images") and Path(s["images"][0]).exists():
        b64 = base64.b64encode(Path(s["images"][0]).read_bytes()).decode()
        img = (f'<img src="data:image/jpeg;base64,{b64}" style="display:block;margin-top:18px;width:100%;'
               f'max-height:{s.get("image_h", 640)}px;object-fit:contain;background:#f2f2f2;border-radius:18px">')
    return f"""<body style="margin:0;background:transparent"><div id=c style="width:920px;box-sizing:border-box;
padding:30px 36px;border-radius:30px;background:#fff;color:#101010;font:{fs}px/1.35 -apple-system,'Helvetica Neue',Arial,sans-serif">
<div style="display:flex;align-items:center;gap:18px;margin-bottom:16px">{av}<b style="font-size:34px">{html.escape(s['user'])}</b>
<span style="font-size:30px;color:#999">{html.escape(s.get('time') or '')}</span><span style="margin-left:auto;font-size:34px;color:#999">···</span></div>
<div style="white-space:pre-wrap;word-break:break-word">{html.escape(text)}</div>{img}
<div style="margin-top:22px;color:#666;font-size:30px;letter-spacing:1px">♡ {s['likes']}&emsp;💬 {s['replies']}&emsp;⟲ {s['reposts']}&emsp;➤</div></div></body>"""


def font_size(text):  # Threads-like: short text big, shrinks as it grows
    n = len(text)
    return 60 if n < 30 else 48 if n < 80 else 42 if n < 160 else 36 if n < 320 else 30


def reveal_steps(display, max_steps=6):
    """Cumulative texts for line-by-line reveal; single step if text is short/one line."""
    parts = [l for l in display.split("\n") if l.strip()]
    if len(parts) < 2:
        parts = [p for p in re.split(r"(?<=[.!?…])\s+", display.strip()) if p]
    if len(display) < 40 or len(parts) < 2:
        return [display]
    size = math.ceil(len(parts) / max_steps)
    parts = ["\n".join(parts[i:i + size]) for i in range(0, len(parts), size)]
    return ["\n".join(parts[:k]) for k in range(1, len(parts) + 1)]


async def make_pngs(jobs):  # jobs: [(html, out_png)] -> heights
    from playwright.async_api import async_playwright
    hs = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        for h, out in jobs:
            await pg.set_content(h)
            loc = pg.locator("#c")
            await loc.screenshot(path=out, omit_background=True)
            hs.append((await loc.bounding_box())["height"])
        await b.close()
    return hs


async def make_tts(jobs, voice, rate, pitch):  # jobs: [(text, out_mp3)]
    import edge_tts
    for text, out in jobs:
        if Path(out).exists() and Path(out).stat().st_size > 0:
            continue  # cache hit (a failed save leaves an empty file - never trust that)
        tmp = Path(str(out) + ".part")
        for attempt in range(15):  # Edge TTS randomly returns NoAudioReceived, sometimes for a minute+
            try:
                await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(tmp))
                tmp.replace(out)
                break
            except edge_tts.exceptions.NoAudioReceived:
                tmp.unlink(missing_ok=True)
                if attempt == 14:
                    raise
                await asyncio.sleep(min(2 + attempt * 1.5, 15))


def run(*cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{cmd[0]} failed:\n{r.stderr[-1500:]}")
    return r.stdout


def dur(f):
    return float(probe(f, "-show_entries", "format=duration"))


def cmd_render(a):
    pj = Path(a.project); w = pj.parent; (w / "tts").mkdir(exist_ok=True)
    P = json.loads(pj.read_text())
    scenes = [norm_scene(s) for s in P["scenes"]]
    hook = P.get("hook")  # {"text": "POV: *logistics* people at 3am 😭", "dur": 2.5} - big title over the first seconds
    assert scenes, "project.json has no scenes"
    mm = Path(a.memes_dir)

    def media(f):  # meme paths: absolute, relative to cwd, or relative to memes dir
        for c in (Path(f), mm / f):
            if c.exists():
                return str(c)
        sys.exit(f"Meme/media not found: {f}")

    def snd(f):  # sound effects: absolute, relative to cwd, or in the sounds dir
        for c in (Path(f), Path(a.sounds_dir) / f):
            if c.exists():
                return str(c)
        sys.exit(f"Sound not found: {f}")

    # phase 1: PNGs (card steps, watermark, gradient) in one browser session
    jobs, plan = [], {}
    for i, s in enumerate(scenes):
        if s["type"] != "card":
            continue
        shown = s["display"][:a.max_chars] + ("…" if len(s["display"]) > a.max_chars else "")
        steps = reveal_steps(shown) if s.get("reveal", True) else [shown]
        plan[i] = {"first": len(jobs), "steps": steps}
        for k, t in enumerate(steps):
            jobs.append((card_html(s, t, font_size(t)), str(w / f"card{i}_{k}.png")))
    n_cards = len(jobs)
    wm = (f"""<div id=c style="display:inline-block;padding:10px 24px;font:bold 42px -apple-system,Arial,sans-serif;
color:#fff;background:#0007;border-radius:16px">{html.escape(a.watermark)}</div>""" if a.watermark
          else '<div id=c style="width:2px;height:2px"></div>')  # no watermark: invisible 2px placeholder
    jobs.append((f'<body style="margin:0;background:transparent">{wm}</body>', str(w / "wm.png")))
    if a.grad:
        jobs.append((f"""<body style="margin:0;background:transparent"><div id=c style="width:1080px;height:520px;
background:linear-gradient(to top,{a.grad}f0 0%,{a.grad}00 100%)"></div></body>""", str(w / "grad.png")))
    if hook:  # *word* = yellow highlight; thick black outline like TikTok titles
        t = re.sub(r"\*(.+?)\*", r'<span style="color:#ffd400">\1</span>', html.escape(hook["text"]))
        jobs.append((f"""<body style="margin:0;background:transparent"><div id=c style="width:1000px;text-align:center;
font:900 76px/1.15 -apple-system,'Helvetica Neue',Arial,sans-serif;color:#fff;-webkit-text-stroke:11px #000;paint-order:stroke fill">{t}</div></body>""",
                     str(w / "hook.png")))
    heights = asyncio.run(make_pngs(jobs))
    hook_h = heights[-1] if hook else 0

    # phase 2: TTS (cached by text hash)
    def tts_path(text):
        key = hashlib.sha1(f"{a.voice}|{a.rate}|{a.pitch}|{text}".encode()).hexdigest()[:12]
        return str(w / "tts" / f"{key}.mp3")
    tts_jobs = {}
    for i, s in enumerate(scenes):
        text = speak(" ".join(filter(None, [s.get("tts", ""), s.get("extra", "")])))
        s["_tts"] = text and tts_path(text)
        if text:
            tts_jobs[s["_tts"]] = text
    asyncio.run(make_tts([(t, p) for p, t in tts_jobs.items()], a.voice, a.rate, a.pitch))

    # phase 3: one clip per scene
    fast = ["-preset", "ultrafast", "-crf", "30"] if a.preview else ["-preset", "veryfast", "-crf", "20"]
    bg = ["-f", "lavfi", "-i", "color=c=0x1b1b2f:s=1080x1920:r=30"] if not a.bg else None
    bgf = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[b];"
    t0 = 0.0
    if a.bg:  # start each video at a different (but repeatable) point of the gameplay so videos don't look identical
        span = max(0.0, dur(a.bg) - 60)
        t0 = random.Random(str(pj.resolve())).uniform(0, span) if a.bg_start == "random" else float(a.bg_start)
    clips = []
    for i, s in enumerate(scenes):
        if a.only is not None and i != a.only:
            continue
        ins = list(bg or ["-stream_loop", "-1", "-ss", f"{t0:.2f}", "-i", a.bg])  # copy: += below must not mutate bg
        n, f, cur = 1, bgf, "b"
        sfx = []  # [{"file","at"(sec),"vol","dur"}] sound effects mixed over the scene audio
        punches = []  # times (sec) of zoom-punch + shake, from sfx/memes marked "punch": true
        voice = dur(s["_tts"]) if s["_tts"] else 0.0

        def sfx_len(file, cap):  # seconds a sound plays: its natural length, capped (default 5s)
            return min(dur(snd(file)), cap or 5.0)

        def add(path, loop):  # append an input, return its index
            nonlocal n
            ins.extend((["-loop", "1"] if loop == "img" else ["-stream_loop", "-1"] if loop == "vid" else []) + ["-i", path])
            n += 1
            return n - 1

        def overlay(idx, x, y, a0, b0, scale):
            nonlocal f, cur
            f += (f"[{idx}:v]format=rgba,{scale},fade=t=in:st={a0:.2f}:d=0.15:alpha=1[m{idx}];[{cur}][m{idx}]"
                  f"overlay=x='{x}':y='({y})+max(0,{a0:.2f}+0.2-t)/0.2*90':enable='between(t,{a0:.2f},{b0:.2f})'[v{idx}];")
            cur = f"v{idx}"

        if s["type"] == "card":
            p = plan[i]; hmax = heights[p["first"] + len(p["steps"]) - 1]
            top = max(40, int(1920 * a.card_y - hmax / 2))
            if hook and i == 0:  # tall cards (with images) must not slide under the hook title
                top = min(max(top, 60 + hook_h + 24), max(40, 1900 - hmax))
            bottom = top + hmax
            total = voice + 0.4 + sum(m.get("dur", 1.5) for m in s["memes"] if m.get("at") == "end")
            t_end, need = voice + 0.4, 0.0  # pre-pass: when each sound starts/ends, so the scene never cuts it off
            for m in s["memes"]:
                st = t_end if m.get("at", "end") == "end" else 0.0 if m["at"] == "start" else float(m["at"])
                t_end += m.get("dur", 1.5) if m.get("at", "end") == "end" else 0
                if m.get("sound"):
                    need = max(need, st + sfx_len(m["sound"], m.get("sound_dur")))
            for x in s.get("sfx", []):
                at = x.get("at", "start")
                at = 0.0 if at == "start" else voice if at == "end" else float(at)
                sfx.append({**x, "at": at, "dur": sfx_len(x["file"], x.get("dur"))})
                need = max(need, at + sfx[-1]["dur"])
                if x.get("punch"):
                    punches.append(at)
            total = max(total, need)
            tot_chars = len(p["steps"][-1]) or 1
            for k, st in enumerate(p["steps"]):  # reveal time ∝ characters already shown
                a0 = 0.0 if k == 0 else voice * len(p["steps"][k - 1]) / tot_chars
                b0 = total if k == len(p["steps"]) - 1 else voice * len(st) / tot_chars
                idx = add(str(w / f"card{i}_{k}.png"), "img")
                if k == 0:  # pop-in: slide up + fade
                    f += (f"[{idx}:v]format=rgba,fade=t=in:st=0:d=0.15:alpha=1[cf{idx}];[{cur}][cf{idx}]"
                          f"overlay=x='(W-w)/2':y='{top}+max(0,0.2-t)/0.2*80':enable='between(t,{a0:.2f},{b0:.2f})'[c{idx}];")
                else:
                    f += f"[{cur}][{idx}:v]overlay=(W-w)/2:{top}:enable='between(t,{a0:.2f},{b0:.2f})'[c{idx}];"
                cur = f"c{idx}"
            end_t = voice + 0.4
            for m in s["memes"]:
                d = m.get("dur", 1.5); at = m.get("at", "end")
                if at == "end":
                    a0, b0, end_t = end_t, end_t + d, end_t + d
                else:
                    a0 = 0.0 if at == "start" else float(at); b0 = min(a0 + d, total)
                if m.get("sound"):
                    sl = sfx_len(m["sound"], m.get("sound_dur"))
                    sfx.append({"file": m["sound"], "at": a0, "vol": m.get("vol", 0.8), "dur": sl})
                    b0 = min(max(b0, a0 + sl), total)
                if m.get("punch"):
                    punches.append(a0)
                pos = m.get("pos", "br")
                x = {"bl": "60", "br": "W-w-60"}.get(pos, "(W-w)/2")
                y = {"bc": f"{bottom}+30", "center": "(H-h)/2"}.get(pos, f"{bottom}-h*0.35")
                src = media(m["file"])
                overlay(add(src, "img" if Path(src).suffix.lower() in IMG else "vid"), x, y, a0, b0, f"scale={m.get('w', 640)}:-2")
            if s["_tts"]:
                f += f"[{add(s['_tts'], None)}:a]apad=whole_dur={total:.2f}[a]"
            else:
                ins.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]); n += 1
                f += f"[{n - 1}:a]anull[a]"
        else:  # media scene: full-frame image/clip (chat screenshot, reaction video...)
            src = media(s["file"]); is_img = Path(src).suffix.lower() in IMG
            has_a = bool(probe(src, "-select_streams", "a", "-show_entries", "stream=codec_type"))
            total = max(s.get("dur", 2.5 if is_img else min(dur(src), 5.0)), voice + 0.4 if voice else 0)
            for x in s.get("sfx", []):
                at = x.get("at", "start")
                at = 0.0 if at == "start" else max(0.0, total - 1) if at == "end" else float(at)
                sfx.append({**x, "at": at, "dur": sfx_len(x["file"], x.get("dur"))})
                total = max(total, at + sfx[-1]["dur"])
                if x.get("punch"):
                    punches.append(at)
            overlay(add(src, "img" if is_img else "vid"), "(W-w)/2", "(H-h)/2", 0, total,
                    "scale=w=1000:h=1100:force_original_aspect_ratio=decrease")
            if voice:
                aidx = add(s["_tts"], None); f += f"[{aidx}:a]apad=whole_dur={total:.2f}[a]"
            elif has_a and not is_img:
                f += f"[{n - 1}:a]apad=whole_dur={total:.2f}[a]"
            else:
                ins.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]); n += 1
                f += f"[{n - 1}:a]anull[a]"
        if sfx:  # rename the voice chain output to [a0], then amix delayed effects on top
            f = f[:-3] + "[a0]"
            labels = ""
            for k, x in enumerate(sfx):
                ms = int(x["at"] * 1000)
                d = x["dur"]
                f += (f";[{add(snd(x['file']), None)}:a]atrim=0:{d:.2f},afade=t=out:st={max(0, d - 0.15):.2f}:d=0.15,"
                      f"adelay={ms}|{ms},volume={x.get('vol', 0.8)}[x{k}]")
                labels += f"[x{k}]"
            f += f";[a0]{labels}amix=inputs={len(sfx) + 1}:duration=first:normalize=0[a]"
        if hook and i == 0:
            hy = max(40, min(150, (top if s["type"] == "card" else 400) - hook_h - 30))
            hidx = add(str(w / "hook.png"), "img")
            f += (f";[{hidx}:v]format=rgba,fade=t=in:st=0:d=0.15:alpha=1,fade=t=out:st={hook.get('dur', 2.5) - 0.2:.2f}:d=0.2:alpha=1[hk];"
                  f"[{cur}][hk]overlay=x='(W-w)/2':y='{hy}+max(0,0.2-t)/0.2*60':enable='lt(t,{hook.get('dur', 2.5):.2f})'[hko]")
            cur = "hko"
        if punches:  # zoom punch (12% → decays) + short horizontal shake
            z = "+".join(f"if(gte(t,{p:.2f}),0.12*exp(-(t-{p:.2f})*7),0)" for p in punches)
            sh = "+".join(f"if(between(t,{p:.2f},{p + 0.3:.2f}),14*sin((t-{p:.2f})*95),0)" for p in punches)
            f += (f";[{cur}]scale=w='trunc(1080*(1+{z})/2)*2':h=-2:eval=frame,"
                  f"crop=1080:1920:x='(iw-1080)/2+{sh}':y='(ih-1920)/2'[pz]")
            cur = "pz"
        f += f";[{cur}]null[v]"
        out = w / f"scene{i}.mp4"
        run("ffmpeg", "-y", *ins, "-filter_complex", f, "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
            "-c:v", "libx264", *fast, "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", out)
        clips.append(out); t0 += total
    if a.only is not None:
        print(f"OK: {clips[0]} ({dur(clips[0]):.1f}s)"); return

    (w / "list.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
    run("ffmpeg", "-y", "-f", "concat", "-i", w / "list.txt", "-c", "copy", w / "joined.mp4")

    ins = ["-i", w / "joined.mp4", "-i", w / "wm.png"]; n = 2; cur = "0:v"; f = ""
    if a.grad:
        ins += ["-i", w / "grad.png"]; f += "[0:v][2:v]overlay=0:H-h[g];"; cur = "g"; n = 3
    if a.progress != "none":  # thin bar filling across the top: viewers see how much is left
        ins += ["-f", "lavfi", "-i", f"color=c={a.progress}:s=1080x12:r=30"]
        f += f"[{cur}][{n}:v]overlay=x='-w+w*t/{t0:.2f}':y=0:shortest=1[pg];"; cur = "pg"; n += 1
    f += f"[{cur}][1:v]overlay=(W-w)/2:H-h-90"
    q = 540 if a.preview else a.quality
    f += (f",scale={q}:-2" if q != 1080 else "") + "[v];"
    if a.bgm:  # music ducks under the voice, then loudness-normalised
        ins += ["-stream_loop", "-1", "-i", a.bgm]
        f += (f"[{n}:a]volume={a.bgm_vol}[bm];[0:a]asplit=2[s1][s2];[bm][s1]sidechaincompress=threshold=0.02:ratio=10:attack=20:release=400[bd];"
              f"[s2][bd]amix=inputs=2:duration=first:normalize=0,loudnorm=I={a.lufs}:TP=-1.5:LRA=11[a]")
    else:
        f += f"[0:a]loudnorm=I={a.lufs}:TP=-1.5:LRA=11[a]"
    out = a.out or str(w / "video.mp4")
    run("ffmpeg", "-y", *ins, "-filter_complex", f, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
        *fast, "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", out)
    got = lufs(out)  # loudnorm in one pass lands ~1-2 LU off; correct with a plain gain + limiter
    if abs(got - a.lufs) > 0.5:
        tmp = str(Path(out).with_suffix(".tmp.mp4"))
        run("ffmpeg", "-y", "-i", out, "-c:v", "copy", "-af", f"volume={a.lufs - got:.2f}dB,alimiter=limit=0.95:level=disabled",
            "-c:a", "aac", "-ar", "44100", tmp)
        Path(tmp).replace(out)
    cover = Path(out).with_name(Path(out).stem + "_cover.jpg")
    run("ffmpeg", "-y", "-ss", "1.0", "-i", out, "-frames:v", "1", "-q:v", "3", cover)
    print(f"OK: {out} ({dur(out):.1f}s, {lufs(out):.1f} LUFS) + {cover.name}")


def lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def cmd_assets(a):
    """Download media listed in assets/manifest.json (media files are not stored in the repo)."""
    root = Path(__file__).parent
    M = json.loads((root / "assets" / "manifest.json").read_text())
    ok = fail = 0
    for kind in ("music", "sounds", "memes", "bg"):
        if kind == "bg" and a.no_bg:
            continue
        for it in M[kind]:
            f = root / it["file"]
            if f.exists() and f.stat().st_size > 0 and not a.force:
                continue
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_name("_dl_" + f.name)
            try:
                if "youtube" in it:  # CC-licensed gameplay: download a section, shrink to 720p, no audio
                    print(f"... downloading {f.name} from YouTube (a few minutes)")
                    subprocess.run([sys.executable, "-m", "yt_dlp", "-q", "--no-warnings", "-f", "bv*[height<=1920][ext=mp4]/bv*",
                                    "--download-sections", f"*{it['section']}", "--force-keyframes-at-cuts", "-o", str(tmp),
                                    f"https://www.youtube.com/watch?v={it['youtube']}"], check=True)
                    run("ffmpeg", "-y", "-i", tmp, "-an", "-vf", "scale=720:-2", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "25", "-pix_fmt", "yuv420p", f)
                else:
                    req = urllib.request.Request(it["url"], headers={"User-Agent": "Mozilla/5.0"})
                    tmp.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                    if kind == "sounds":  # trim leading silence so the effect hits exactly when the meme appears
                        run("ffmpeg", "-y", "-i", tmp, "-af", "silenceremove=start_periods=1:start_threshold=-45dB",
                            "-ar", "44100", "-b:a", "192k", f)
                    else:
                        tmp.replace(f)
                ok += 1
            except Exception as e:
                fail += 1
                print(f"ERROR {it['file']}: {e}")
            finally:
                tmp.unlink(missing_ok=True)
    print(f"OK: downloaded {ok} files, {fail} errors. Sources and licenses: assets/CREDITS.md")


def cmd_transcribe(a):
    import numpy as np
    from faster_whisper import WhisperModel
    # decode with ffmpeg: faster-whisper's own decoder (PyAV) breaks on this Python
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.file, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    segs, info = WhisperModel(a.model, compute_type="int8").transcribe(np.frombuffer(pcm, np.float32), language="vi", vad_filter=True)
    for s in segs:
        print(f"[{s.start:6.1f}-{s.end:6.1f}] {s.text.strip()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(required=True)
    s = sub.add_parser("scrape"); s.set_defaults(fn=cmd_scrape)
    s.add_argument("url"); s.add_argument("-n", type=int, default=4, help="number of comments to pick automatically (edit later)")
    s.add_argument("-o", "--out", help="output folder"); s.add_argument("--keep-spam", action="store_true")
    s.add_argument("--scroll", type=int, default=8, help="scroll count to load more comments (0 = no scrolling)")
    s = sub.add_parser("login"); s.set_defaults(fn=cmd_login)
    s = sub.add_parser("assets", help="download music/backgrounds/memes/sounds"); s.set_defaults(fn=cmd_assets)
    s.add_argument("--force", action="store_true", help="re-download files that already exist"); s.add_argument("--no-bg", action="store_true", help="skip background videos (large)")
    s = sub.add_parser("info"); s.set_defaults(fn=cmd_info); s.add_argument("project")
    s = sub.add_parser("memes"); s.set_defaults(fn=cmd_memes); s.add_argument("dir", nargs="?", default="memes")
    s = sub.add_parser("transcribe"); s.set_defaults(fn=cmd_transcribe)
    s.add_argument("file"); s.add_argument("--model", default="small")
    r = sub.add_parser("render"); r.set_defaults(fn=cmd_render)
    r.add_argument("project"); r.add_argument("--bg", help="background video (mp4)"); r.add_argument("--bgm", help="background music")
    r.add_argument("--bgm-vol", type=float, default=0.25, help="music volume (ducks automatically under the voice)")
    r.add_argument("--watermark"); r.add_argument("--memes-dir", default="memes"); r.add_argument("--sounds-dir", default="sounds")
    r.add_argument("--voice", default="vi-VN-HoaiMyNeural"); r.add_argument("--rate", default="+55%"); r.add_argument("--pitch", default="-4Hz", help="e.g. -6Hz: lower, flatter, deadpan voice")
    r.add_argument("--card-y", type=float, default=0.36, help="vertical centre of the card (0 = top, 1 = bottom)")
    r.add_argument("--grad", help="colour of a gradient fading in at the bottom, e.g. #ff8a00"); r.add_argument("--max-chars", type=int, default=600)
    r.add_argument("--bg-start", default="random", help="start second of the background, or 'random' (stable per project)")
    r.add_argument("--progress", default="0xFFD400", help="colour of the progress bar at the top, 'none' to disable")
    r.add_argument("--quality", type=int, choices=[540, 720, 1080], default=1080); r.add_argument("--lufs", type=float, default=-14)
    r.add_argument("--only", type=int, help="render only scene N (quick look)"); r.add_argument("--preview", action="store_true", help="fast, 540p")
    r.add_argument("-o", "--out", help="file mp4 ra")
    a = ap.parse_args(); a.fn(a)
