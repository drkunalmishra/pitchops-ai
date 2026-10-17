"""Assemble the demo: title card → screen-recorded scenes (narrated) → finished-video clip → FinOps → end card,
with a quiet Lyria music bed (already generated, no new cost) ducked out under the clip. Output ≤ 4:00, 1080p.

  .venv/bin/python scripts/demo/mix.py   (from pitchops-ai/)
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from scenes import DATA, SCENES  # noqa: E402

W, H, FPS = 1920, 1080, 30
PAD, LEAD = 1.5, 0.35  # hold after narration; narration starts LEAD s into a scene
WORK = DATA / "work"
AUDIO = DATA / "audio"
VID = Path("/private/tmp/claude-501/-Users-mamtamishra-Desktop-Project-BigSell-PitchOPsAI/"
           "0ed26401-5975-47aa-8f54-6b0a9df801f4/scratchpad/deck/vid")
BUCKET = "gs://pitchops-ai-2026-pitchops/media/music"
OUT = DATA / "PitchOps_AI_demo.mp4"
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def sh(*a):
    subprocess.run([str(x) for x in a], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode())


def f(px, bold=False):
    for path, idx in [("/System/Library/Fonts/HelveticaNeue.ttc", 1 if bold else 0),
                      ("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0)]:
        try:
            return ImageFont.truetype(path, px, index=idx)
        except OSError:
            continue
    return ImageFont.load_default(size=px)


def card(path, title, sub, lines):
    img = Image.new("RGB", (W, H), (7, 18, 38))
    d = ImageDraw.Draw(img)
    for y in range(H):  # soft gradient
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(7 + 11 * k), int(18 + 22 * k), int(38 + 39 * k)))
    bar = [(66, 133, 244), (52, 168, 83), (251, 188, 4), (234, 67, 53)]
    for i, c in enumerate(bar):
        d.rectangle([W // 2 - 240 + i * 120, 300, W // 2 - 240 + (i + 1) * 120 - 8, 308], fill=c)
    d.text((W // 2, 420), title, font=f(110, True), fill=(240, 245, 250), anchor="mm")
    d.text((W // 2, 530), sub, font=f(44), fill=(45, 212, 191), anchor="mm")
    y = 650
    for ln in lines:
        d.text((W // 2, y), ln, font=f(36), fill=(200, 215, 230), anchor="mm")
        y += 58
    img.save(path)
    return path


def seg_audio(sid, total):
    """Narration placed at LEAD, padded with silence to the segment length."""
    a = AUDIO / f"{sid}.mp3"
    return ["-i", str(a)], (f"[1:a]adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad,atrim=0:{total:.3f},"
                            f"aformat=sample_rates=48000:channel_layouts=stereo[a]")


def build_rec(tl):
    """Frames with timestamps → constant-frame-rate video of the whole recording."""
    lst = WORK / "frames.txt"
    fr = tl["frames"]
    with lst.open("w") as fh:
        for i, (t, name) in enumerate(fr):
            nxt = fr[i + 1][0] if i + 1 < len(fr) else t + 1 / FPS
            fh.write(f"file '{DATA / 'rec' / 'frames' / name}'\nduration {max(nxt - t, 0.001):.4f}\n")
        fh.write(f"file '{DATA / 'rec' / 'frames' / fr[-1][1]}'\n")
    out = WORK / "rec_full.mp4"
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf",
       f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x07122a,"
       f"fps={FPS}", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out)
    t_first = fr[0][0]
    return out, t_first


def main():
    WORK.mkdir(exist_ok=True)
    tl = json.loads((DATA / "rec" / "timeline.json").read_text())
    marks = {m["id"]: m for m in tl["scenes"]}
    rec, t_first = build_rec(tl)
    segs, clip_windows, t = [], [], 0.0
    for s in SCENES:
        out = WORK / f"{s['id']}.mp4"
        if s["kind"] == "card":
            total = dur(AUDIO / f"{s['id']}.mp3") + LEAD + PAD + 0.6
            if s["id"] == "s00_title":
                png = card(WORK / "title.png", "PitchOps AI", "Team SellItR8  ·  AI Builder Cup 2026",
                           ["From brokers' public videos to an evidence-rated persona playbook",
                            "and a compliant AI sales pitch, in minutes."])
            else:
                png = card(WORK / "end.png", "PitchOps AI", "pitchops-ai-2026.web.app",
                           ["github.com/drkunalmishra/pitchops-ai",
                            "Firebase Hosting & Auth · Firestore · Cloud Run · Gemini on Vertex AI",
                            "Team SellItR8 — Kunal Mishra · Manjeet Malwan"])
            ai, af = seg_audio(s["id"], total)
            sh("ffmpeg", "-y", "-loop", "1", "-t", f"{total:.3f}", "-i", png, *ai, "-filter_complex",
               f"[0:v]fade=t=in:st=0:d=0.6,fade=t=out:st={total - 0.6:.3f}:d=0.6,format=yuv420p[v];{af}",
               "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", *ENC, out)
        elif s["kind"] == "rec":
            m = marks[s["id"]]
            st, total = m["start"] - t_first, m["end"] - m["start"]
            ai, af = seg_audio(s["id"], total)
            sh("ffmpeg", "-y", "-ss", f"{max(st, 0):.3f}", "-t", f"{total:.3f}", "-i", rec, *ai,
               "-filter_complex", f"[0:v]setpts=PTS-STARTPTS[v];{af}", "-map", "[v]", "-map", "[a]",
               "-t", f"{total:.3f}", *ENC, out)
        else:  # clip of a finished PitchOps video, with its own audio
            total = s["dur"]
            src = VID / s["file"]
            sh("ffmpeg", "-y", "-ss", s["ss"], "-t", total, "-i", src, "-filter_complex",
               f"[0:v]scale={W}:{H},fade=t=in:st=0:d=0.4,fade=t=out:st={total - 0.6}:d=0.6[v];"
               f"[0:a]afade=t=out:st={total - 1}:d=1,aformat=sample_rates=48000:channel_layouts=stereo[a]",
               "-map", "[v]", "-map", "[a]", "-t", total, *ENC, out)
            clip_windows.append((t, t + total))
        d = dur(out)
        segs.append(out)
        print(f"{s['id']:16s} {t:6.1f} → {t + d:6.1f}s")
        t += d
    # concat
    lst = WORK / "segs.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    body = WORK / "body.mp4"
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", body)
    total = dur(body)
    # music bed: three calm Lyria beds cross-faded, looped, quiet, muted under the clip
    beds = []
    for k in ("education_led", "developer_authority", "risk_reduction"):
        p = WORK / f"{k}.wav"
        if not p.exists():
            sh("gcloud", "storage", "cp", "-q", f"{BUCKET}/{k}.wav", p)
        beds.append(p)
    bed = WORK / "bed.wav"
    sh("ffmpeg", "-y", "-i", beds[0], "-i", beds[1], "-i", beds[2], "-filter_complex",
       "[0][1]acrossfade=d=3[x];[x][2]acrossfade=d=3,aformat=sample_rates=48000:channel_layouts=stereo[a]",
       "-map", "[a]", bed)
    mute = "+".join(f"between(t,{a - 0.5:.2f},{b + 0.3:.2f})" for a, b in clip_windows) or "0"
    sh("ffmpeg", "-y", "-i", body, "-stream_loop", "-1", "-i", bed, "-filter_complex",
       f"[1:a]atrim=0:{total:.3f},volume=0.13,volume=enable='{mute}':volume=0,"
       f"afade=t=in:d=1.5,afade=t=out:st={total - 2.5:.3f}:d=2.5[m];"
       f"[0:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]",
       "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
       "-movflags", "+faststart", OUT)
    print(f"\n{OUT}  {dur(OUT):.1f}s  ({dur(OUT) / 60:.2f} min)")
    if dur(OUT) > 240:
        print("⚠ over 4:00 — trim before submitting")


if __name__ == "__main__":
    main()
