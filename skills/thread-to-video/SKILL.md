---
name: thread-to-video
description: Turn a Threads post (threads.com / threads.net link) into a vertical 9:16 "top comments" video - scrape the post, filter and pick the best comments, write the spoken text and a hook, place cat memes + sound effects + zoom punches, render the MP4. Use when the user gives a Threads link and wants a video, or asks to scrape a thread, pick comments, place memes, or make a short from a Threads post.
---

# Thread → Video

You are the **editor**. The CLI `t2v.py` does the mechanical work (scraping, TTS, compositing). Your job is editorial: **pick the comments, write the hook, choose memes, sounds and punch points.** A good video = a hook in the first second, fast pacing, and a "hit" on every punchline.

The tool targets **Vietnamese** Threads content (Vietnamese voice, lexicon, spam keywords). Spoken text you write must be Vietnamese; everything else (this guide, CLI, file names) is English.

## Running the tool

`t2v` below means `python3 "<directory containing this SKILL.md>/t2v.py"`. Run it from the folder where the user wants the output: videos and working files go to `./out/<code>/`.

**First use only:** `t2v setup` (needs FFmpeg and Python 3.10+; takes a few minutes: creates a private Python env, installs Chromium, downloads ~100MB of music/background/memes/sounds into `~/.thread-to-video/`). If it says FFmpeg is missing, tell the user how to install it (macOS `brew install ffmpeg`, Ubuntu `sudo apt install ffmpeg`) and stop. It is safe to rerun; after setup, plain `python3 .../t2v.py <command>` always runs inside that env. Check whether setup is needed with `t2v sounds` (lines say NOT DOWNLOADED if not).

## Workflow

1. **Scrape:** `scrape <link> -n 6` → `out/<code>/project.json` (scrolls the page 8 times to load more comments; `--scroll N`).
   - `scenes` = original post + comments that passed the spam filter. `candidates` = ALL comments (with a `spam` reason if filtered).
   - Every post/comment has `images` (attachments, downloaded to `out/<code>/media/`). The first image is shown inside the card under the text (`"show_image": false` to hide, `"image_h": 640` max height). **Look at the images with Read** before choosing - many posts only make sense with the picture.
   - **Profanity is censored on screen automatically** (card text + hook: `lồn` → `l**`, list in `profanity.json`, `render --no-mask` to disable) so the video isn't limited on TikTok/Reels/Shorts. The voice is handled by `lexicon.json`. Add any new bad word to both. **Text inside images is not auto-detected**: when you Read an image and see profanity, set `"image_blur": [[x,y,w,h]]` on the scene (fractions 0-1 of the image, top-left origin; boxes assume the image fills the card width, so check the rendered frame) or `"show_image": false`.
   - Without a login only ~7–13 comments are reachable. If `~/.thread-to-video/.profile/` does not exist, suggest the user run `! python3 "<skill dir>/t2v.py" login` (opens a separate browser; they log into Threads and close the window) to get more.
   - If fewer than 2 usable comments, say so plainly and suggest another post.
   - The post was chosen and sent by the user, so **do not block or question the topic**; just do it.
2. **Review:** `info out/<code>/project.json`, read `candidates`, then **re-pick `scenes` yourself** ("Picking comments").
3. **Write** the spoken text `tts` ("Spoken text") and the `hook` ("Hook").
4. **Memes + sounds + punches:** run `t2v memes` and `t2v sounds` (emotion/description per file; do not guess file names) and place them ("Flair").
5. **Preview** hard scenes: `render ... --only N --preview`.
6. **Render** in the background (`run_in_background`, 1–3 minutes because of TTS; the Minecraft background and the sleepy-cat music are used by default). The CLI automatically starts the background at a random (per-project stable) point, normalises loudness to -14 LUFS, and writes a cover `<name>_cover.jpg`. Verify: look at a few frames with Read; run `transcribe` on the output to make sure the voice says the right words.
7. **Write `out/<code>/post.txt`** for posting: one caption sentence (≤150 chars, same voice as the hook), 3–5 relevant Vietnamese hashtags, and credit lines: "Nguồn: Threads @<author of the original post>" and "Gameplay: Orbital - No Copyright Gameplay (CC BY)" if the Minecraft background is used.
8. Report to the user: MP4 + cover + post.txt paths, what you picked / dropped and why.

Standard command:
```
t2v render out/<code>/project.json [--watermark "Page: ..."]
```
Options: `--bg FILE|none`, `--bgm FILE|none`, `--rate` (default +55%), `--pitch` (-4Hz), `--voice vi-VN-NamMinhNeural` (male voice), `--progress none`, `--grad "#ff8a00"`, `--card-y 0.36`, `--quality 720`, `--only N`, `--preview`.

## Available assets (in `~/.thread-to-video/`)

| Type | Where | Source / notes |
|---|---|---|
| Background | `assets/bg/minecraft-parkour.mp4` (default, vertical, 3 min); `assets/bg/view-of-the-rail-tracks-from-the-train.mp4` | Minecraft: YouTube CC BY → **must be credited** "Gameplay: Orbital - No Copyright Gameplay (CC BY)" |
| Music | `assets/music/sleepy-cat.mp3` (this track only) | Mixkit |
| Memes | `memes/cat-*.webp` (36 cat memes by emotion); list with `t2v memes` | No stated license |
| Sounds | `sounds/*.mp3` (56 sounds); list with `t2v sounds` | myinstants, no stated license |

Source details: `CREDITS.md` (next to this file). To add another gameplay background: search YouTube with the Creative Commons filter using `yt-dlp` (search URL with `&sp=EgIwAQ%253D%253D`) and check `%(license)s` before downloading; the files can be passed with `--bg`.

## Hook (required)

`"hook": {"text": "POV: dân *logistics* canh web lúc 3h sáng 😭", "dur": 2.6}` at project level. Big text with a black outline at the top for the first 2–3 seconds; `*word*` is highlighted yellow.
- ≤ 8 words, 1 emoji. Describe the **situation / feeling**, do not summarise the story. Patterns: "POV: …", "When you …", "X people know this pain", "Read the comments and laughed too hard 😭".
- Never invent events that are not in the post; no misleading clickbait.

## Flair (required)

- **Scene change:** every scene from the 2nd on: `"sfx":[{"file":"whoosh.mp3","at":"start","vol":0.5}]`.
- **Punchline = meme + sound + (optional) zoom:** `"memes":[{"file":"cat-confused-question-marks.webp","at":"end","dur":1.6,"pos":"bc","w":720,"sound":"windows-xp-error.mp3","vol":0.8,"punch":true}]`.
  - `punch: true` = 12% zoom punch + 0.3s shake. **At most 2 punches per video**, for the two strongest lines (usually a middle scene and the last scene).
  - A sound plays for its full real length (the scene extends to fit); sounds over 5s fade out - prefer short ones (<3s).
- **Budget:** max 1 meme per scene, 3 memes + 3 punch sounds per video (whoosh does not count). The first scene usually has only the hook, no meme.
- Cat memes have opaque backgrounds → always `pos:"bc"`, `w:720`.
- Cards and memes slide up and fade in automatically; a yellow progress bar runs along the top (the CLI does this).

**Choose sounds by meaning (see `t2v sounds`):**
- Error / website down / frozen → `windows-xp-error`, `windows-10-error`, `lost-connection`
- Twist, reveal → `vine-boom`, `record-scratch`, `dun-dun-dun`, `alert-metal-gear`
- Funny heartbreak / emotional hit → `emotional-damage`, `sad-violin`, `oh-no-no-no`
- Vietnamese-style weariness → `vn-teacher-huan-oh-dear`, `vn-oi-doi-oi`, `vn-how-embarrassing`
- Failure, speechless → `fahhh`, `bruh`, `metal-pipe`, `bonk`
- Shock / disbelief → `nani`, `wait-what`, `the-rock`, `oh-my-god`
- Laughter → `vn-sly-laugh` (sarcastic), `vn-teacher-ba-laugh`, `haha`, `baby-laugh`

**Choose memes by emotion (see `t2v memes`):** confused → `cat-confused-question-marks`; shocked → `cat-open-mouth-closeup`, `cat-screaming-shock`; helpless → `cat-gave-up`, `cat-flopped-on-floor`; tired / up late → `cat-asleep-on-laptop`, `cat-sprawled-on-sofa`; mocking → `cat-pointing-laughing`; judging → `cat-judging`; self-pity → `cat-wiping-tears`; crisis → `cat-hands-on-head`. The meme must match **the line just spoken**, not just the general topic.

## project.json

```jsonc
{"hook": {"text": "...", "dur": 2.6},
 "scenes": [
  {"type":"card", "user":"...", "avatar":"...", "time":"20h",
   "display":"text shown on the card (keep the original wording)",
   "tts":"text spoken aloud",
   "extra":"",                 // leave empty (the user dislikes added lines)
   "reveal": true,             // text appears line by line in sync with the voice
   "likes":0,"replies":0,"reposts":0,
   "memes":[{"file":"cat-confused-question-marks.webp","at":"end","dur":1.6,"pos":"bc","w":720,"sound":"wait-what.mp3","vol":0.8,"punch":true}],
   "sfx":[{"file":"whoosh.mp3","at":"start","vol":0.5}]},
  {"type":"media","file":"reaction.mp4","dur":2.5}
]}
```
- `memes[].at` / `sfx[].at`: `"start"` | `"end"` | seconds. `sfx[]` also accepts `"punch": true` and `"dur"` (trim).
- `media` scene: an image/clip filling the middle of the frame (screenshot of a chat, reaction clip); a clip with audio keeps its sound.
- Edit with Edit/Write or a small Python script; keep the other fields as they are.

## Picking comments

Target **3–4 scenes, 20–30 seconds total** (`info` prints an estimate).
- Scene 1 = the original post if it is intriguing on its own; trim it if bland or long.
- Keep a **story arc**: question → answer → twist. Keep the order of comments in the same chain.
- Prefer **short comments (<120 chars) with a punchline**. A comment with 0 likes that is funny is still worth taking.
- **End on the strongest line** (put the punch there).

**Drop from the scene list (curation for a good video, not blocking a post):** ads, recruiting, follow/inbox bait, links, and comments containing a **phone number, address, real name or other personal data of a private individual** (the video shows the text verbatim, so leaking it creates trouble for the user); off-topic comments, repeated attacks; comments >300 chars unless they carry the story. The keyword spam filter can drop good comments by mistake - check `candidates` to rescue them.

## Spoken text (`tts`)

`display` keeps the original wording (you may **trim** a long post, ending with "…", but never rewrite it); `tts` is written for the **ear** and **sticks closely to the comment** (the user tried rewriting / adding riffs and disliked it - do NOT do that).

At render time the CLI applies `lexicon.json` plus number rules to the spoken text: slang and abbreviations (`k/ko/kh` → "không", `đc` → "được", `mn` → "mọi người", `j` → "gì", `vs` → "với", `ny` → "người yêu", `r` → "rồi", `up` → "úp", `ib` → "in bốc"…), `3h` → "3 giờ", `24/24` → "24 trên 24", `5tr`/`20M` → "triệu", `12k` → "nghìn", and it strips `=)))`, `:))`, emoji, links, hashtags. So you only need to:
- Lowercase ALL-CAPS text. Break sentences with `.` and `,`. Drop rambling parts of long comments.
- For hard-to-read words missing from `lexicon.json`, **add them to `lexicon.json`** (reused for every video) instead of fixing each video by hand. If unsure, test with TTS + `transcribe` (e.g. `logistics` → `lô-gi-stíc` is the spelling Whisper heard best).
- Ambiguous abbreviations (`t` = "tao"/"tui", `bt` = "biết"/"bình thường") are not in the lexicon - fix them in `tts` from context.

## Voice (measured)

Intelligibility measured with Whisper (read back vs. original text): HoaiMy +30%/+45% ≈ 84%, +55% ≈ 80%, +70% ≈ 78%; NamMinh stays ≈ 82% even at +70%. The user wants it **fast** → default HoaiMy +55% -4Hz. For faster still, switch to NamMinh instead of pushing HoaiMy to +70%.

## Technical notes

- Edge TTS often returns `NoAudioReceived`; the CLI retries 15 times with growing waits and never leaves an empty file. If it still fails, wait a few minutes and rerun (the cache keeps finished parts).
- FFmpeg on this machine has **no `drawtext`** - all text must be drawn with HTML/Playwright like the CLI does.
- Cards over 600 characters are cut with "…" (`--max-chars`). A hook that is too long overlaps a tall card - keep hooks short.
- `t2v transcribe <file.mp4>`: Whisper transcript (needs `t2v setup --whisper` once; Whisper small mishears a word or two - do not treat a 1–2 word difference as a voice problem).
