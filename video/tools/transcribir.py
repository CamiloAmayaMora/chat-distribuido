"""Transcribe las grabaciones de video/voces/original/ con marcas de tiempo por palabra.
Escribe video/voces/transcripciones/SXX.json y un resumen en la consola.

    python video/tools/transcribir.py [S01 S02 ...]
"""
import json
import sys
from pathlib import Path

import subprocess

import numpy as np
from faster_whisper import WhisperModel

VIDEO = Path(__file__).resolve().parents[1]
SRC = VIDEO / "voces" / "original"
OUT = VIDEO / "voces" / "transcripciones"
OUT.mkdir(parents=True, exist_ok=True)
model = WhisperModel("small", device="cpu", compute_type="int8")
names = sys.argv[1:] or sorted(p.stem for p in SRC.glob("S*.wav"))
for n in names:
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(SRC / f"{n}.wav"), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, dtype=np.float32)
    segs, info = model.transcribe(audio, language="es", word_timestamps=True, vad_filter=False)
    words, text = [], []
    for s in segs:
        text.append(s.text.strip())
        for w in s.words or []:
            words.append({"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)})
    (OUT / f"{n}.json").write_text(json.dumps({"text": " ".join(text), "words": words}, ensure_ascii=False, indent=1), encoding="utf-8")
    first = words[0]["start"] if words else 0
    last = words[-1]["end"] if words else 0
    print(f"{n} [{first:.2f}-{last:.2f}s]: {' '.join(text)}", flush=True)
