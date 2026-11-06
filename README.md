# thread-to-video

**English** | [Tiếng Việt](README.vi.md)

Turn a **Threads** post into a vertical **9:16** "top comments" video for TikTok / Reels / Shorts:
scrape the post and its comments → filter spam → Vietnamese AI voice-over → Threads-style cards over gameplay footage → cat memes, sound effects, zoom punches → MP4.

- Scrapes the original post, comments, avatars and **attached images**; scrolls the page to load more comments; filters spam (phone numbers, links, job ads, follow-for-follow, tag-only replies).
- Voice: `vi-VN-HoaiMyNeural` / `NamMinhNeural` (Edge TTS, free), with a pronunciation dictionary `lexicon.json` (Vietnamese slang and abbreviations, `3h` → "3 giờ", `logistics` → "lô-gi-stíc"…).
- Big hook title in the first seconds, text revealed in sync with the voice, cards and memes slide in, zoom punch + shake on punchlines, whoosh transitions, progress bar, music that ducks under the voice, loudness normalised to -14 LUFS, cover image.
- Ships with a **Claude Code skill**: the AI picks the best comments, writes the hook, chooses memes / sounds / punch points, and renders.

> The voice, lexicon, spam filter and skill are tuned for **Vietnamese** content. Other languages work with a different `--voice` and your own `lexicon.json`.

## Install

Requires **Python 3.10+** (tested on 3.14), **FFmpeg** with libx264, macOS (tested) or Linux.

```bash
git clone https://github.com/Gressi-177/thread-to-video.git
cd thread-to-video
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python t2v.py assets          # downloads music, Minecraft background, 36 cat memes, 56 sound effects (~100MB)
```

- macOS: `brew install ffmpeg python`. Ubuntu: `sudo apt install ffmpeg python3-venv fonts-noto-color-emoji` (an emoji font is needed for emoji on cards).
- Optional: `.venv/bin/pip install -r requirements-whisper.txt` for `transcribe` (Whisper transcription, to check the voice-over).
- Optional: `.venv/bin/python t2v.py login` opens a separate browser; log into Threads, then close the window. Without logging in it still works, but only ~7–13 comments per post are reachable.

## Usage

### With Claude Code (recommended)

Open this folder in [Claude Code](https://claude.com/claude-code) and send a link:

```
make a video from this thread https://www.threads.com/@user/post/XXXX
```

The skill in `.claude/skills/thread-to-video` guides the AI to: pick 3–4 comments with a story arc and a punchline, write the hook, match cat memes and sounds to the emotion, render, check frames and the voice-over, and write a ready-to-post caption `post.txt`.

### By hand (CLI)

```bash
.venv/bin/python t2v.py scrape "https://www.threads.com/@user/post/XXXX" -n 4    # -> out/XXXX/project.json
.venv/bin/python t2v.py info out/XXXX/project.json                              # scenes, spam, estimated length
# edit out/XXXX/project.json: pick scenes, fix the spoken text, add hook / memes / sfx (see SKILL.md)
.venv/bin/python t2v.py render out/XXXX/project.json \
    --bg assets/bg/minecraft-parkour.mp4 --bgm assets/music/sleepy-cat.mp3 --watermark "Page: ..."
```

Outputs `out/XXXX/video.mp4` + `video_cover.jpg`. Common options: `--only N --preview` (quick render of one scene), `--rate +55%`, `--voice vi-VN-NamMinhNeural`, `--progress none`, `--quality 720`. All options: `t2v.py render -h`.

Example `project.json` (full reference in [SKILL.md](.claude/skills/thread-to-video/SKILL.md)):

```jsonc
{"hook": {"text": "POV: *logistics* people watching the website at 3am 😭", "dur": 2.6},
 "scenes": [
  {"type": "card", "user": "...", "display": "original text on the card", "tts": "text to speak",
   "memes": [{"file": "cat-confused-question-marks.webp", "at": "end", "dur": 1.6, "pos": "bc", "w": 720,
              "sound": "windows-xp-error.mp3", "punch": true}],
   "sfx": [{"file": "whoosh.mp3", "at": "start", "vol": 0.5}]}
 ]}
```

`*word*` in the hook is highlighted in yellow. `memes[].at` / `sfx[].at`: `"start"`, `"end"` or seconds. `punch: true` adds a zoom punch + shake.

## Commands

| Command | What it does |
|---|---|
| `scrape <link>` | Scrape post + comments + images → `out/<code>/project.json` |
| `info <project>` | Summary of scenes, spam, estimated length |
| `render <project>` | Render MP4 + cover image |
| `memes` | List the meme library |
| `assets` | Download media listed in `assets/manifest.json` |
| `login` | Log into Threads once (stored in `.profile/`, never committed) |
| `transcribe <mp4>` | Transcribe with Whisper |

## Notes

- **Copyright:** the repo only contains code and a *list of sources*; media is downloaded to your machine. Memes (theselfishmeme.co.uk) and sounds (myinstants.com) have **no stated license**, so you are responsible for how you use them. The Minecraft background is **CC BY**: credit "Gameplay: Orbital - No Copyright Gameplay (CC BY)". Details: [assets/CREDITS.md](assets/CREDITS.md).
- **Other people's content:** credit the Threads author; don't use this to shame private individuals.
- Edge TTS and Threads' page data are **unofficial** and can change at any time. TTS fails randomly; the tool retries and caches what is already done.
- Homebrew FFmpeg on macOS may lack `drawtext`; the tool draws all text with HTML/Playwright, so it isn't needed.

## License

Code: [MIT](LICENSE). Does not cover media downloaded by `assets` (each source has its own license).
