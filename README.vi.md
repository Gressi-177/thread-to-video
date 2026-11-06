# thread-to-video

[English](README.md) | **Tiếng Việt**

Biến một bài **Threads** thành video dọc **9:16** kiểu "top comment" cho TikTok / Reels / Shorts:
cào bài + comment → lọc spam → giọng đọc AI tiếng Việt → thẻ giống giao diện Threads chạy trên nền gameplay → meme mèo, sound effect, zoom nhấn → MP4.

- Cào bài gốc, comment, avatar, **ảnh đính kèm**; tự cuộn trang để lấy thêm comment; lọc spam (số điện thoại, link, tuyển dụng, xin follow, chỉ tag bạn).
- Giọng đọc `vi-VN-HoaiMyNeural` / `NamMinhNeural` (Edge TTS, miễn phí), từ điển phát âm `lexicon.json` (k→không, 3h→3 giờ, logistics→lô-gi-stíc…).
- Hook chữ to ở giây đầu, chữ hiện dần theo giọng, thẻ/meme trượt lên, zoom giật + rung ở punchline, whoosh chuyển cảnh, thanh tiến trình, nhạc nền tự hạ khi có giọng, chuẩn hoá âm lượng -14 LUFS, ảnh bìa.
- Kèm **skill cho Claude Code**: AI tự chọn comment hay, viết hook, chọn meme/âm/chỗ nhấn và render.

## Cài đặt

Cần: **Python 3.10+** (đã test 3.14), **FFmpeg** có libx264, macOS (đã test) hoặc Linux (`brew install ffmpeg` / `sudo apt install ffmpeg fonts-noto-color-emoji`; cần font emoji để thẻ hiện emoji).

### Dạng skill (một lệnh)

```bash
npx skills add Gressi-177/thread-to-video --skill thread-to-video
```

Lệnh này chép thư mục skill tự đủ (`SKILL.md` + CLI + dữ liệu) vào thư mục skill của agent (Claude Code: `.claude/skills/`, thêm `-g` thì vào `~/.claude/skills/`). Sau đó nhờ agent làm video từ một link Threads; lần đầu skill tự chạy `t2v.py setup` (tạo môi trường Python riêng, cài Chromium, tải ~100MB nhạc/nền/meme/âm vào `~/.thread-to-video/`). Cách thủ công: chép `skills/thread-to-video` vào `~/.claude/skills/`.

### Dạng CLI thuần

```bash
git clone https://github.com/Gressi-177/thread-to-video.git
python3 thread-to-video/skills/thread-to-video/t2v.py setup     # một lần, vài phút
```

- Tuỳ chọn: `t2v.py setup --whisper` thêm Whisper cho lệnh `transcribe` (kiểm tra giọng đọc).
- Tuỳ chọn: `t2v.py login` mở trình duyệt riêng, bạn tự đăng nhập Threads rồi đóng cửa sổ. Không đăng nhập vẫn chạy được nhưng chỉ lấy được ~7–13 comment/bài.
- Dữ liệu nặng nằm ở `~/.thread-to-video/` (đổi bằng biến `T2V_HOME`); video và file làm việc nằm ở `./out/` trong thư mục bạn đang chạy.

## Cách dùng

### Với AI agent (khuyên dùng)

Mở một thư mục bất kỳ bằng [Claude Code](https://claude.com/claude-code) (hoặc agent khác hỗ trợ skill) rồi gửi link:

```
làm video từ thread này https://www.threads.com/@user/post/XXXX
```

Skill ([SKILL.md](skills/thread-to-video/SKILL.md)) hướng dẫn AI: chọn 3–4 comment có mạch và punchline, viết hook, chọn meme mèo + âm khớp cảm xúc, render, kiểm tra frame và giọng đọc, viết sẵn caption `post.txt`.

### Dùng tay (CLI)

Dưới đây `t2v` là `python3 thread-to-video/skills/thread-to-video/t2v.py`.

```bash
t2v scrape "https://www.threads.com/@user/post/XXXX" -n 4    # -> out/XXXX/project.json
t2v info out/XXXX/project.json                              # xem cảnh, spam, độ dài ước tính
# sửa out/XXXX/project.json: chọn cảnh, sửa chữ đọc, thêm hook / meme / sfx (xem SKILL.md)
t2v render out/XXXX/project.json --watermark "Fanpage: ..."  # mặc định nền Minecraft + nhạc sleepy-cat
```

Ra `out/XXXX/video.mp4` + `video_cover.jpg`. Tuỳ chọn hay dùng: `--only N --preview` (xem nhanh 1 cảnh), `--rate +55%`, `--voice vi-VN-NamMinhNeural`, `--bg FILE|none`, `--bgm FILE|none`, `--progress none`, `--quality 720`. Xem tất cả: `t2v render -h`. Xem kho có gì: `t2v memes`, `t2v sounds`.

Ví dụ `project.json` (đầy đủ trong [SKILL.md](skills/thread-to-video/SKILL.md)):

```jsonc
{"hook": {"text": "POV: dân *logistics* canh web lúc 3h sáng 😭", "dur": 2.6},
 "scenes": [
  {"type": "card", "user": "...", "display": "chữ gốc trên thẻ", "tts": "chữ đọc",
   "memes": [{"file": "cat-confused-question-marks.webp", "at": "end", "dur": 1.6, "pos": "bc", "w": 720,
              "sound": "windows-xp-error.mp3", "punch": true}],
   "sfx": [{"file": "whoosh.mp3", "at": "start", "vol": 0.5}]}
 ]}
```

`*từ*` trong hook được tô vàng. `memes[].at` / `sfx[].at`: `"start"`, `"end"` hoặc số giây. `punch: true` = zoom giật + rung.

## Lệnh

| Lệnh | Việc |
|---|---|
| `scrape <link>` | Cào bài + comment + ảnh → `out/<mã>/project.json` |
| `info <project>` | Tóm tắt cảnh, spam, độ dài ước tính |
| `render <project>` | Xuất MP4 + ảnh bìa |
| `memes` | Liệt kê kho meme |
| `setup` | Cài một lần: môi trường Python, Chromium, media |
| `memes` / `sounds` | Liệt kê kho meme / âm thanh kèm mô tả |
| `assets` | Tải tài nguyên theo `manifest.json` |
| `login` | Đăng nhập Threads 1 lần (lưu ở `~/.thread-to-video/.profile/`, không nằm trong repo) |
| `transcribe <mp4>` | Chép lời bằng Whisper |

## Lưu ý

- **Bản quyền:** repo chứa code, *danh sách nguồn* và 39 video meme ngắn trong `assets/memes/` (không rõ giấy phép, sưu tầm trên mạng); phần media còn lại được tải về máy bạn. Meme (theselfishmeme.co.uk) và sound (myinstants.com) **không rõ giấy phép** - bạn tự chịu trách nhiệm khi đăng. Nền Minecraft là **CC BY**: ghi "Gameplay: Orbital - No Copyright Gameplay (CC BY)". Chi tiết: [CREDITS.md](skills/thread-to-video/CREDITS.md).
- **Nội dung người khác:** ghi nguồn tác giả Threads; không dùng để bêu riếu người thường.
- Edge TTS và cấu trúc dữ liệu Threads là **không chính thức** - có thể đổi bất cứ lúc nào. TTS hay lỗi ngẫu nhiên; tool tự thử lại và cache phần đã đọc.
- FFmpeg trên macOS (Homebrew) có thể không có `drawtext` - tool vẽ mọi chữ bằng HTML/Playwright nên không cần.

## Giấy phép

Code: [MIT](LICENSE). Không áp dụng cho media tải bằng `assets` (mỗi nguồn có giấy phép riêng).
