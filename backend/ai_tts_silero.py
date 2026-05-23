"""Локальный Silero TTS (опционально: pip install torch)."""

from __future__ import annotations

import io
import wave

_silero_model = None
_silero_speakers: list[str] | None = None


def silero_available() -> bool:
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def _get_model():
    global _silero_model, _silero_speakers
    if _silero_model is not None:
        return _silero_model, _silero_speakers or []
    import torch

    model, speakers = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker="v4_ru",
    )
    _silero_model = model
    _silero_speakers = list(speakers)
    return model, _silero_speakers


def synthesize_wav(text: str, speaker: str = "xenia", speed: float = 1.0) -> bytes:
    model, speakers = _get_model()
    sp = speaker if speaker in speakers else "xenia"
    audio = model.apply_tts(text=text.strip(), speaker=sp, sample_rate=48000)
    if hasattr(audio, "numpy"):
        import numpy as np

        samples = (audio.numpy() * 32767).astype("int16")
    else:
        import numpy as np

        samples = (np.asarray(audio) * 32767).astype("int16")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()


def wav_to_mp3(wav_bytes: bytes) -> bytes:
    try:
        from pydub import AudioSegment
    except ImportError as e:
        raise RuntimeError(
            "Для Silero→MP3 установи pydub и ffmpeg: pip install pydub"
        ) from e
    seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))
    out = io.BytesIO()
    seg.export(out, format="mp3", bitrate="128k")
    return out.getvalue()
