# thread-to-video

[English](README.md) | **Tiếng Việt**

Biến một bài **Threads** thành video dọc **9:16** kiểu "top comment" cho TikTok / Reels / Shorts:
cào bài + comment → lọc spam → giọng đọc AI tiếng Việt → thẻ giống giao diện Threads chạy trên nền gameplay → meme mèo, sound effect, zoom nhấn → MP4.

- Cào bài gốc, comment, avatar, **ảnh đính kèm**; tự cuộn trang để lấy thêm comment; lọc spam (số điện thoại, link, tuyển dụng, xin follow, chỉ tag bạn).
- Giọng đọc `vi-VN-HoaiMyNeural` / `NamMinhNeural` (Edge TTS, miễn phí), từ điển phát âm `lexicon.json` (k→không, 3h→3 giờ, logistics→lô-gi-stíc…).
- Hook chữ to ở giây đầu, chữ hiện dần theo giọng, thẻ/meme trượt lên, zoom giật + rung ở punchline, whoosh chuyển cảnh, thanh tiến trình, nhạc nền tự hạ khi có giọng, chuẩn hoá âm lượng -14 LUFS, ảnh bìa.
- Kèm **skill cho Claude Code**: AI tự chọn comment hay, viết hook, chọn meme/âm/chỗ nhấn và render.

## Cài đặt

Cần: **Python 3.10+** (đã test 3.14), **FFmpeg** có libx264, macOS (đã test) hoặc Linux.

```bash
git clone https://github.com/Gressi-177/thread-to-video.git
cd thread-to-video
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python t2v.py assets          # tải nhạc, nền Minecraft, 36 meme mèo, 56 sound effect (~100MB, vài phút)
```

- macOS: `brew install ffmpeg python`. Ubuntu: `sudo apt install ffmpeg python3-venv fonts-noto-color-emoji` (cần font emoji để thẻ hiện emoji).
- Tuỳ chọn: `.venv/bin/pip install -r requirements-whisper.txt` để dùng `transcribe` (Whisper chép lời, kiểm tra giọng đọc).
- Tuỳ chọn: `.venv/bin/python t2v.py login` - mở trình duyệt riêng, bạn tự đăng nhập Threads rồi đóng cửa sổ. Không đăng nhập vẫn chạy được nhưng chỉ lấy được ~7–13 comment/bài.

## Cách dùng

### Với Claude Code (khuyên dùng)

Mở thư mục này bằng [Claude Code](https://claude.com/claude-code) rồi gửi link:

```
làm video từ thread này https://www.threads.com/@user/post/XXXX
```

Skill `.claude/skills/thread-to-video` hướng dẫn AI: chọn 3–4 comment có mạch và punchline, viết hook, chọn meme mèo + âm khớp cảm xúc, render, kiểm tra frame và giọng đọc, viết sẵn caption `post.txt`.

### Dùng tay (CLI)

```bash
.venv/bin/python t2v.py scrape "https://www.threads.com/@user/post/XXXX" -n 4    # -> out/XXXX/project.json
.venv/bin/python t2v.py info out/XXXX/project.json                              # xem cảnh, spam, độ dài ước tính
# sửa out/XXXX/project.json: chọn cảnh, sửa chữ đọc, thêm hook / meme / sfx (xem SKILL.md)
.venv/bin/python t2v.py render out/XXXX/project.json \
    --bg assets/bg/minecraft-parkour.mp4 --bgm assets/music/sleepy-cat.mp3 --watermark "Fanpage: ..."
```

Ra `out/XXXX/video.mp4` + `video_cover.jpg`. Tuỳ chọn hay dùng: `--only N --preview` (xem nhanh 1 cảnh), `--rate +55%`, `--voice vi-VN-NamMinhNeural`, `--progress none`, `--quality 720`. Xem tất cả: `t2v.py render -h`.

Ví dụ `project.json` (đầy đủ trong [SKILL.md](.claude/skills/thread-to-video/SKILL.md)):

```jsonc
{"hook": {"text": "POV: dân *logistics* canh web lúc 3h sáng 😭", "dur": 2.6},
 "scenes": [
  {"type": "card", "user": "...", "display": "chữ gốc trên thẻ", "tts": "chữ đọc",
   "memes": [{"file": "cat-confused-question-marks.webp", "at": "end", "dur": 1.6, "pos": "bc", "w": 720,
              "sound": "windows-xp-error.mp3", "punch": true}],
   "sfx": [{"file": "whoosh.mp3", "at": "start", "vol": 0.5}]}
 ]}
```

## Lệnh

| Lệnh | Việc |
|---|---|
| `scrape <link>` | Cào bài + comment + ảnh → `out/<mã>/project.json` |
| `info <project>` | Tóm tắt cảnh, spam, độ dài ước tính |
| `render <project>` | Xuất MP4 + ảnh bìa |
| `memes` | Liệt kê kho meme |
| `assets` | Tải tài nguyên theo `assets/manifest.json` |
| `login` | Đăng nhập Threads 1 lần (lưu ở `.profile/`, không bao giờ commit) |
| `transcribe <mp4>` | Chép lời bằng Whisper |

## Lưu ý

- **Bản quyền:** repo chỉ chứa code và *danh sách nguồn*; media được tải về máy bạn. Meme (theselfishmeme.co.uk) và sound (myinstants.com) **không rõ giấy phép** - bạn tự chịu trách nhiệm khi đăng. Nền Minecraft là **CC BY**: ghi "Gameplay: Orbital - No Copyright Gameplay (CC BY)". Chi tiết: [assets/CREDITS.md](assets/CREDITS.md).
- **Nội dung người khác:** ghi nguồn tác giả Threads; không dùng để bêu riếu người thường.
- Edge TTS và cấu trúc dữ liệu Threads là **không chính thức** - có thể đổi bất cứ lúc nào. TTS hay lỗi ngẫu nhiên; tool tự thử lại và cache phần đã đọc.
- FFmpeg trên macOS (Homebrew) có thể không có `drawtext` - tool vẽ mọi chữ bằng HTML/Playwright nên không cần.

## Giấy phép

Code: [MIT](LICENSE). Không áp dụng cho media tải bằng `assets` (mỗi nguồn có giấy phép riêng).
