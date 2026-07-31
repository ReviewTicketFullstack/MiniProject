#!/usr/bin/env python3
"""회의 음성 녹음 → Gemini/OpenAI Whisper/로컬 Whisper 전사. 표준 라이브러리만 사용
(로컬 전사만 예외적으로 faster-whisper 패키지 필요).

흐름: ffmpeg로 mono 16kHz mp3 추출 → (25MB 초과 시 시간 균등 분할) → 업로드/로컬 추론
→ 텍스트를 이어붙여 표준출력으로 반환. 실패는 SystemExit 메시지로 안내.
provider 우선순위: GEMINI_API_KEY 있으면 Gemini → 없고 OPENAI_API_KEY 있으면 Whisper API
→ 둘 다 없으면 로컬 Whisper(faster-whisper, 계정/과금 불필요, 대신 느리고 정확도 낮음)로 폴백.

watch 플러그인의 whisper.py를 OpenAI 전용으로 슬림화해 적응.
"""
from __future__ import annotations

import base64
import io
import json
import math
import mimetypes
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_gemini_key, load_openai_key  # noqa: E402

# anaconda 환경 등에서 torch/ctranslate2가 OpenMP 런타임을 중복 로드해 죽는 문제 회피.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

OPENAI_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_MODEL = "whisper-1"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
GEMINI_PROMPT = "이 오디오를 그대로 받아써줘. 화자 구분이나 요약 없이 실제로 말한 내용만 이어서 적어줘."
MAX_UPLOAD_BYTES = 24 * 1024 * 1024  # 25MB 한도 아래 여유

MAX_ATTEMPTS = 4
MAX_429_RETRIES = 2
RETRY_BASE_DELAY = 2.0

LOCAL_WHISPER_MODEL = "medium"  # small은 다화자 한국어 회의에서 오류가 너무 많아 medium 사용
_local_model = None


def _require(tool: str) -> None:
    if shutil.which(tool) is None:
        raise SystemExit(f"{tool} 가 설치되어 있지 않습니다. 음성 기능을 쓰려면 ffmpeg를 설치하세요.")


def extract_audio(source: str, out_path: Path) -> Path:
    """mono 16kHz 64kbps mp3 추출 — 분당 약 480kB."""
    _require("ffmpeg")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(Path(source).resolve()),
        "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-b:a", "64k",
        str(out_path.resolve()),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg 오디오 추출 실패: {result.stderr.strip()}")
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise SystemExit("ffmpeg가 오디오를 만들지 못했습니다 — 오디오 트랙이 없을 수 있습니다.")
    return out_path


def audio_duration(audio_path: Path) -> float:
    _require("ffprobe")
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format",
         str(audio_path.resolve())],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"ffprobe 실패: {result.stderr.strip()}")
    fmt = json.loads(result.stdout or "{}").get("format", {})
    return float(fmt.get("duration") or 0.0)


def plan_chunks(total_seconds: float, total_bytes: int) -> list[tuple[float, float]]:
    if total_bytes <= MAX_UPLOAD_BYTES or total_seconds <= 0:
        return [(0.0, total_seconds)]
    n = math.ceil(total_bytes / MAX_UPLOAD_BYTES)
    chunk = total_seconds / n
    plan = []
    for i in range(n):
        offset = i * chunk
        duration = (total_seconds - offset) if i == n - 1 else chunk
        plan.append((round(offset, 3), round(duration, 3)))
    return plan


def split_audio(full_audio: Path, work_dir: Path, plan: list[tuple[float, float]]) -> list[Path]:
    _require("ffmpeg")
    work_dir.mkdir(parents=True, exist_ok=True)
    chunks = []
    for i, (offset, duration) in enumerate(plan):
        out_path = work_dir / f"chunk_{i:03d}.mp3"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{offset:.3f}", "-i", str(full_audio.resolve()),
            "-t", f"{duration:.3f}", "-c", "copy", str(out_path.resolve()),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
            raise SystemExit(f"오디오 청크 {i + 1} 분할 실패: {result.stderr.strip()}")
        chunks.append(out_path)
    return chunks


def _build_multipart(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = f"----MinutelyBoundary{uuid.uuid4().hex}"
    eol = b"\r\n"
    buf = io.BytesIO()
    for name, value in fields.items():
        buf.write(f"--{boundary}".encode()); buf.write(eol)
        buf.write(f'Content-Disposition: form-data; name="{name}"'.encode()); buf.write(eol)
        buf.write(eol)
        buf.write(str(value).encode()); buf.write(eol)
    mimetype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    buf.write(f"--{boundary}".encode()); buf.write(eol)
    buf.write(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode())
    buf.write(eol)
    buf.write(f"Content-Type: {mimetype}".encode()); buf.write(eol)
    buf.write(eol)
    buf.write(file_path.read_bytes()); buf.write(eol)
    buf.write(f"--{boundary}--".encode()); buf.write(eol)
    return buf.getvalue(), boundary


def _read_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read()
        return f" — {body.decode('utf-8', errors='replace')[:400]}" if body else ""
    except Exception:
        return ""


def _post_whisper(api_key: str, audio_path: Path) -> dict:
    fields = {"model": OPENAI_MODEL, "response_format": "verbose_json", "temperature": "0"}
    body, boundary = _build_multipart(fields, audio_path)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "minutely-skill/0.1 (+claude-code; python-urllib)",
    }
    context = ssl.create_default_context()
    rate_limit_hits = 0
    last_exc = None
    last_detail = ""
    for attempt in range(MAX_ATTEMPTS):
        request = Request(OPENAI_ENDPOINT, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=300, context=context) as response:
                payload = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = _read_error_body(exc)
            last_exc, last_detail = exc, detail
            if 400 <= exc.code < 500 and exc.code != 429:
                raise SystemExit(f"Whisper 요청 실패: {exc}{detail}")
            if exc.code == 429:
                rate_limit_hits += 1
                if rate_limit_hits >= MAX_429_RETRIES:
                    raise SystemExit(f"Whisper 요청 실패(429): {exc}{detail}")
                delay = RETRY_BASE_DELAY * (2 ** attempt) + 1
            else:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
            if attempt < MAX_ATTEMPTS - 1:
                print(f"[minutely] whisper HTTP {exc.code} — {delay:.1f}s 후 재시도", file=sys.stderr)
                time.sleep(delay)
            continue
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError) as exc:
            last_exc, last_detail = exc, ""
            if attempt < MAX_ATTEMPTS - 1:
                delay = RETRY_BASE_DELAY * (attempt + 1)
                print(f"[minutely] whisper 네트워크 오류 — {delay:.1f}s 후 재시도", file=sys.stderr)
                time.sleep(delay)
            continue
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Whisper 응답이 JSON이 아님: {exc}: {payload[:200]}")
    raise SystemExit(f"Whisper 요청이 {MAX_ATTEMPTS}회 모두 실패: {last_exc}{last_detail}")


def _post_gemini(api_key: str, audio_path: Path) -> str:
    # extract_audio/split_audio는 항상 mp3로 인코딩한다 — mimetypes.guess_type의 "audio/mpeg"는
    # Gemini가 인식하지 못해 오디오를 조용히 무시하므로 "audio/mp3"로 고정한다.
    body = json.dumps({
        "contents": [{
            "parts": [
                {"text": GEMINI_PROMPT},
                {"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(audio_path.read_bytes()).decode()}},
            ]
        }]
    }).encode()
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    context = ssl.create_default_context()
    rate_limit_hits = 0
    last_exc = None
    last_detail = ""
    for attempt in range(MAX_ATTEMPTS):
        request = Request(GEMINI_ENDPOINT, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=300, context=context) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            detail = _read_error_body(exc)
            last_exc, last_detail = exc, detail
            if 400 <= exc.code < 500 and exc.code != 429:
                raise SystemExit(f"Gemini 요청 실패: {exc}{detail}")
            if exc.code == 429:
                rate_limit_hits += 1
                if rate_limit_hits >= MAX_429_RETRIES:
                    raise SystemExit(f"Gemini 요청 실패(429): {exc}{detail}")
                delay = RETRY_BASE_DELAY * (2 ** attempt) + 1
            else:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
            if attempt < MAX_ATTEMPTS - 1:
                print(f"[minutely] gemini HTTP {exc.code} — {delay:.1f}s 후 재시도", file=sys.stderr)
                time.sleep(delay)
            continue
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError) as exc:
            last_exc, last_detail = exc, ""
            if attempt < MAX_ATTEMPTS - 1:
                delay = RETRY_BASE_DELAY * (attempt + 1)
                print(f"[minutely] gemini 네트워크 오류 — {delay:.1f}s 후 재시도", file=sys.stderr)
                time.sleep(delay)
            continue
        try:
            parts = payload["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError) as exc:
            raise SystemExit(f"Gemini 응답 형식이 예상과 다름: {exc}: {json.dumps(payload)[:200]}")
    raise SystemExit(f"Gemini 요청이 {MAX_ATTEMPTS}회 모두 실패: {last_exc}{last_detail}")


def _load_local_model():
    global _local_model
    if _local_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise SystemExit(
                "로컬 Whisper 폴백을 쓰려면 faster-whisper 설치가 필요합니다: pip install faster-whisper"
            )
        print(f"[minutely] 로컬 Whisper({LOCAL_WHISPER_MODEL}) 모델 로드 중…", file=sys.stderr)
        _local_model = WhisperModel(LOCAL_WHISPER_MODEL, device="cpu", compute_type="int8")
    return _local_model


def _post_local(audio_path: Path) -> str:
    model = _load_local_model()
    segments, _info = model.transcribe(str(audio_path), language="ko", beam_size=5)
    return " ".join(seg.text.strip() for seg in segments if seg.text.strip())


def _segments_text(data: dict) -> str:
    segs = data.get("segments") or []
    parts = [(s.get("text") or "").strip() for s in segs]
    parts = [p for p in parts if p]
    if parts:
        return " ".join(parts)
    return (data.get("text") or "").strip()


def transcribe(source: str, work_dir: Path) -> str:
    gemini_key = load_gemini_key()
    openai_key = load_openai_key()
    if gemini_key:
        provider, api_key = "gemini", gemini_key
    elif openai_key:
        provider, api_key = "openai", openai_key
    else:
        provider, api_key = "local", None
        print(
            "[minutely] GEMINI_API_KEY/OPENAI_API_KEY 없음 — 로컬 Whisper(faster-whisper)로 폴백"
            " (계정·과금 불필요, 대신 느리고 정확도 낮음)",
            file=sys.stderr,
        )

    def _post(chunk: Path) -> str:
        if provider == "gemini":
            return _post_gemini(api_key, chunk)
        if provider == "openai":
            return _segments_text(_post_whisper(api_key, chunk))
        return _post_local(chunk)

    audio = extract_audio(source, work_dir / "audio.mp3")
    size = audio.stat().st_size
    if size <= MAX_UPLOAD_BYTES:
        print(f"[minutely] 오디오 {size/1024:.0f}kB — {provider} 업로드…", file=sys.stderr)
        return _post(audio)

    duration = audio_duration(audio)
    plan = plan_chunks(duration, size)
    print(f"[minutely] {size/(1024*1024):.0f}MB — {len(plan)}개 청크로 분할 전사({provider})…", file=sys.stderr)
    chunks = split_audio(audio, work_dir / "chunks", plan)
    texts = []
    failures = 0
    for i, chunk in enumerate(chunks):
        try:
            texts.append(_post(chunk))
        except SystemExit as exc:
            failures += 1
            print(f"[minutely] 청크 {i+1}/{len(chunks)} 실패 — 건너뜀 ({exc})", file=sys.stderr)
    if failures == len(chunks):
        raise SystemExit("모든 오디오 청크 전사에 실패했습니다.")
    return " ".join(t for t in texts if t)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: transcribe.py <녹음파일경로>", file=sys.stderr)
        return 2
    source = argv[0]
    if not Path(source).exists():
        raise SystemExit(f"파일을 찾을 수 없습니다: {source}")
    work_dir = Path(".minutely") / "audio"
    text = transcribe(source, work_dir)
    if not text:
        raise SystemExit("전사 결과가 비었습니다.")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
