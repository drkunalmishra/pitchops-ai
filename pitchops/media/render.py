"""P7 renderer: Cloud TTS narration + Ken Burns photo motion + Pillow-drawn captions/cards, composed with FFmpeg.

Works without Veo (free preview / fallback ladder level 1). A plan's shots render in order; Veo shots are represented
by a slate (avatar) or photo motion of their first frame (hero clips) until real clips exist.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

BRAND = "PitchOps Demo Realty"
PERMIT = "DEMO-PERMIT"
NAVY, TEAL, WHITE = (7, 18, 38), (45, 212, 191), (240, 245, 250)
SIZES = {"16x9": {"final": (1920, 1080), "preview": (960, 540)},
         "9x16": {"final": (1080, 1920), "preview": (540, 960)}}
FPS = 30


def font(px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=px)


def _wrap(text: str, width_px: int, px: int) -> list[str]:
    return textwrap.wrap(text, max(12, int(width_px / (px * 0.55))))


def card(path: Path, size: tuple[int, int], title: str, lines: list[str], badge: str | None = None,
         bg: Image.Image | None = None) -> Path:
    w, h = size
    img = bg.convert("RGB").resize(size) if bg else Image.new("RGB", size, NAVY)
    if not bg:  # vertical gradient
        top, bot = NAVY, (18, 40, 77)
        d0 = ImageDraw.Draw(img)
        for y in range(h):
            k = y / h
            d0.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3)))
    d = ImageDraw.Draw(img, "RGBA")
    if bg:
        d.rectangle([0, 0, w, h], fill=(7, 18, 38, 150))
    tp, bp = max(28, w // 22), max(18, w // 42)
    y = int(h * 0.30)
    for ln in _wrap(title, int(w * 0.84), tp):
        d.text((w // 2, y), ln, font=font(tp), fill=WHITE, anchor="mm")
        y += int(tp * 1.25)
    y += bp
    for line in lines:
        for ln in _wrap(line, int(w * 0.8), bp):
            d.text((w // 2, y), ln, font=font(bp), fill=(200, 215, 230), anchor="mm")
            y += int(bp * 1.35)
    if badge:
        d.rounded_rectangle([20, 20, 20 + int(bp * 0.62 * len(badge)) + 24, 20 + bp + 16], radius=8, fill=(*TEAL, 230))
        d.text((32, 28), badge, font=font(bp), fill=NAVY)
    d.text((w // 2, h - bp * 2), f"{BRAND} · {PERMIT}", font=font(int(bp * 0.8)), fill=TEAL, anchor="mm")
    img.save(path)
    return path


def caption(path: Path, size: tuple[int, int], text: str, lower_third: str | None = None,
            fact: str | None = None) -> Path:
    """Transparent overlay: caption box near the bottom safe area, optional lower-third and fact card."""
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    px = max(16, w // 40)
    lines = _wrap(text, int(w * 0.86), px)[:3]
    box_h = int(len(lines) * px * 1.3 + px)
    y0 = int(h * 0.86) - box_h
    d.rounded_rectangle([int(w * 0.05), y0, int(w * 0.95), y0 + box_h], radius=12, fill=(7, 18, 38, 190))
    for i, ln in enumerate(lines):
        d.text((w // 2, y0 + px * 0.6 + i * px * 1.3 + px * 0.5), ln, font=font(px), fill=WHITE, anchor="mm")
    if lower_third:
        d.rounded_rectangle([int(w * 0.04), int(h * 0.05), int(w * 0.04) + int(px * 0.6 * len(lower_third)) + 30,
                             int(h * 0.05) + int(px * 1.6)], radius=8, fill=(45, 212, 191, 220))
        d.text((int(w * 0.04) + 15, int(h * 0.05) + int(px * 0.3)), lower_third, font=font(px), fill=NAVY)
    if fact:
        fy = int(h * 0.05) + int(px * 2.2)
        d.rounded_rectangle([int(w * 0.04), fy, int(w * 0.04) + int(px * 0.55 * len(fact)) + 30, fy + int(px * 1.5)],
                            radius=8, fill=(255, 255, 255, 215))
        d.text((int(w * 0.04) + 15, fy + int(px * 0.25)), fact, font=font(int(px * 0.9)), fill=NAVY)
    img.save(path)
    return path


def run(args: list[str]) -> None:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-600:]}")


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


@lru_cache(maxsize=1)
def _tts_client() -> Any:
    """One REST client per process: gRPC channels stall when the process also forks ffmpeg subprocesses."""
    from google.cloud import texttospeech as T

    return T.TextToSpeechClient(transport="rest")


def tts(text: str, voice: str, cache: Path) -> Path:
    """Cloud TTS (Neural2) MP3, cached by text+voice hash. Counted by the caller for FinOps (characters)."""
    from google.cloud import texttospeech as T

    p = cache / f"tts_{hashlib.sha1((voice + text).encode()).hexdigest()[:16]}.mp3"
    if not p.exists():
        c = _tts_client()
        res = c.synthesize_speech(input=T.SynthesisInput(text=text),
                                  voice=T.VoiceSelectionParams(language_code=voice[:5], name=voice),
                                  audio_config=T.AudioConfig(audio_encoding=T.AudioEncoding.MP3, speaking_rate=1.0))
        p.write_bytes(res.audio_content)
    return p


def silence(sec: float, path: Path) -> Path:
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{sec:.2f}", "-q:a", "9", str(path)])
    return path


def segment(out: Path, size: tuple[int, int], audio: Path, still: Path | None, overlay: Path | None,
            pad: float = 0.35, motion: int = 0, fixed: float | None = None) -> Path:
    """Video segment = (Ken Burns over a photo | static card) + optional overlay PNG + audio (+pad seconds);
    fixed= forces an exact length (audio padded or trimmed) — used for shots that stand in for 8 s Veo clips."""
    w, h = size
    dur = fixed if fixed else duration(audio) + pad
    frames = int(dur * FPS)
    inputs = ["-loop", "1", "-i", str(still)]
    if still and still.suffix != ".png":  # photo -> Ken Burns (alternate zoom-in / zoom-out per segment)
        z = "min(zoom+0.0009,1.12)" if motion % 2 == 0 else "if(eq(on,1),1.12,max(zoom-0.0009,1.0))"
        vf = (f"[0:v]scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
              f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={FPS}[bg]")
    else:
        vf = f"[0:v]scale={w}:{h},fps={FPS}[bg]"
    if overlay:
        inputs += ["-i", str(overlay)]
        vf += ";[bg][1:v]overlay=0:0[v]"
    else:
        vf += ";[bg]copy[v]"
    run(["ffmpeg", "-y", *inputs, "-i", str(audio), "-filter_complex", vf + f";[{2 if overlay else 1}:a]apad[a]",
         "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out)])
    return out


def clip_segment(out: Path, size: tuple[int, int], video: Path, keep_audio: bool, overlay: Path | None = None,
                 seconds: float | None = None) -> Path:
    """Normalise a Veo clip to the target size/fps; keep its dialogue audio or add silence (hero clips)."""
    w, h = size
    dur = seconds or duration(video)
    vf = f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}[bg]"
    inputs = ["-i", str(video)]
    if overlay:
        inputs += ["-i", str(overlay)]
        vf += ";[bg][1:v]overlay=0:0[v]"
    else:
        vf += ";[bg]copy[v]"
    if keep_audio:
        amap = ["-map", "0:a?"]
    else:
        inputs += ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
        amap = ["-map", f"{2 if overlay else 1}:a"]
    run(["ffmpeg", "-y", *inputs, "-filter_complex", vf, "-map", "[v]", *amap, "-t", f"{dur:.2f}", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100",
         "-ac", "2", str(out)])
    return out


def concat(parts: list[Path], out: Path, loudnorm: bool = True) -> Path:
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    af = ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"] if loudnorm else []
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), *af, "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-movflags", "+faststart", str(out)])
    return out


def qc(path: Path, fmt: str, max_sec: float) -> list[str]:
    """Automatic QC: duration, aspect ratio, audio present, no black frames > 0.5 s."""
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                                       str(path)], capture_output=True, text=True, check=True).stdout)
    errs: list[str] = []
    v = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
    if not any(s["codec_type"] == "audio" for s in probe["streams"]):
        errs.append("no audio")
    if v and (v["width"] > v["height"]) != (fmt == "16x9"):
        errs.append(f"aspect {v['width']}x{v['height']} does not match {fmt}")
    if float(probe["format"]["duration"]) > max_sec + 0.5:
        errs.append(f"duration {float(probe['format']['duration']):.1f}s > {max_sec}s")
    bd = subprocess.run(["ffmpeg", "-i", str(path), "-vf", "blackdetect=d=0.5:pix_th=0.05", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    if "black_start" in bd:
        errs.append("black frames > 0.5 s")
    return errs


def workdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="pitchops_render_"))
