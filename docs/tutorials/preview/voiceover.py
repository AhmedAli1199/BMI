"""Adds the voiceover to a recorded tutorial video and makes the finished MP4.

    python docs/tutorials/preview/voiceover.py docs/tutorials/01-making-a-booking [--voice Kore] [--redo]

1. Reads final.timeline.json (or preview.timeline.json) written by the video's preview.mjs - when each step starts.
2. Makes one voice clip per step with Gemini text-to-speech (GEMINI_API_KEY; model GEMINI_TTS_MODEL), saved as
   voice/step-NN.wav. A clip is only made again when the step's words change, or with --redo. To use another voice
   tool, put your own step-NN.wav files in voice/ and delete the matching step-NN.txt - they're used as they are.
3. Warns when a clip is longer than its step (give that step more seconds in the blueprint, then record again).
4. Puts each clip at its step's start and writes final.mp4 (H.264 + AAC) and final.srt (subtitles for YouTube etc.).

Needs ffmpeg (on the PATH, or `pip install imageio-ffmpeg`) and, for the voice, `pip install google-genai`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

LEAD = 0.4   # seconds after a step starts before its line is spoken
STYLE = ("Read this as a calm, clear tutorial narrator with a neutral British English accent, at a steady pace, "
         "warm but not salesy:")


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg isn't installed. Install it (brew install ffmpeg / apt install ffmpeg) or run: pip install imageio-ffmpeg")


def seconds(wav: Path) -> float:
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def speak(text: str, out: Path, voice: str, model: str) -> None:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("The voice needs the Google library: pip install google-genai")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("Set GEMINI_API_KEY to make the voice (or put your own step-NN.wav files in the voice folder).")
    client = genai.Client(api_key=key)
    r = client.models.generate_content(
        model=model, contents=f"{STYLE} {text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))))
    pcm = r.candidates[0].content.parts[0].inline_data.data   # 16-bit mono PCM at 24 kHz
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Add the voiceover to a recorded tutorial video.")
    ap.add_argument("folder", help="the video's folder, e.g. docs/tutorials/01-making-a-booking")
    ap.add_argument("--voice", default=os.environ.get("TUTORIAL_VOICE", "Kore"), help="Gemini voice name")
    ap.add_argument("--model", default=os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"))
    ap.add_argument("--redo", action="store_true", help="make every clip again")
    a = ap.parse_args()

    folder = Path(a.folder)
    tl_file = next((folder / f for f in ("final.timeline.json", "preview.timeline.json") if (folder / f).exists()), None)
    if not tl_file:
        sys.exit(f"No timeline in {folder}. Record the video first: node {folder}/preview.mjs --final")
    tl = json.loads(tl_file.read_text())
    video = folder / tl["video"]
    voice_dir = folder / "voice"
    voice_dir.mkdir(exist_ok=True)

    trim = tl["steps"][0]["start"] if tl["steps"] else 0   # drop the page loading before the first step
    clips, srt, problems = [], [], []
    for s in tl["steps"]:
        if not s["voiceover"]:
            continue
        n = f"{s['step']:02d}"
        wav, txt = voice_dir / f"step-{n}.wav", voice_dir / f"step-{n}.txt"
        same = txt.exists() and txt.read_text() == s["voiceover"]
        if a.redo or not wav.exists() or (txt.exists() and not same):
            print(f"  voice for step {n}…")
            speak(s["voiceover"], wav, a.voice, a.model)
            txt.write_text(s["voiceover"])
        length = seconds(wav)
        room = s["secs"] - LEAD - 0.2
        if length > room:
            problems.append(f"step {n} ({s['title']}): the voice is {length:.1f}s but the step leaves {room:.1f}s - "
                            f"give it {int(length - room + 1)}s more in the blueprint and record again")
        start = s["start"] - trim + LEAD
        clips.append((wav, start))
        srt.append(f"{len(srt) + 1}\n{srt_time(start)} --> {srt_time(start + length)}\n{s['voiceover']}\n")

    out = folder / "final.mp4"
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{trim:.3f}", "-i", str(video)]
    for wav, _ in clips:
        cmd += ["-i", str(wav)]
    delays = "".join(f"[{i + 1}:a]aresample=48000,adelay={int(t * 1000)}:all=1[a{i}];" for i, (_, t) in enumerate(clips))
    mix = "".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0:duration=longest[voice]"
    cmd += ["-filter_complex", delays + mix, "-map", "0:v", "-map", "[voice]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    (folder / "final.srt").write_text("\n".join(srt))
    print(f"Done: {out} and {folder / 'final.srt'}")
    for p in problems:
        print("  ! " + p)


if __name__ == "__main__":
    main()
