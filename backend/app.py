import os
import uuid
import json
import time
import threading
import subprocess
import shutil
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
WORK_DIR = DATA_DIR / "work"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v else default


def _first_existing_cmd(candidates: list[str], fallback: str) -> str:
    for c in candidates:
        if shutil.which(c):
            return c
    return fallback


# Homebrew 的 whisper-cpp 包通常提供 whisper-cli/whisper-server 等命令
WHISPER_BIN = os.environ.get("WHISPER_BIN") or _first_existing_cmd(
    ["whisper-cli", "whisper-cpp", "main"], "whisper-cli"
)
FFMPEG_BIN = os.environ.get("FFMPEG_BIN") or _first_existing_cmd(["ffmpeg"], "ffmpeg")
WHISPER_MODEL = _env("WHISPER_MODEL", str(ROOT_DIR / "models" / "ggml-small.bin"))
WHISPER_LANGUAGE = _env("WHISPER_LANGUAGE", "zh")
WHISPER_THREADS = int(_env("WHISPER_THREADS", str(min(8, os.cpu_count() or 4))))

# 允许更大文件（1小时音频可能很大）
MAX_CONTENT_LENGTH_MB = int(_env("MAX_CONTENT_LENGTH_MB", "1024"))  # 1GB


app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH_MB * 1024 * 1024


_jobs_lock = threading.Lock()
_jobs: dict[str, dict] = {}


def _set_job(job_id: str, **kwargs):
    with _jobs_lock:
        job = _jobs.get(job_id, {})
        job.update(kwargs)
        _jobs[job_id] = job


def _get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        out_lines: list[str] = []
        assert p.stdout is not None
        for line in p.stdout:
            out_lines.append(line)
        rc = p.wait()
        return rc, "".join(out_lines)
    except FileNotFoundError as e:
        return 127, f"找不到命令：{e}\ncmd={cmd}\n"


def _run_stream(
    cmd: list[str],
    cwd: Path | None = None,
    on_line=None,
    max_capture_lines: int = 5000,
) -> tuple[int, str]:
    """
    流式读取子进程输出，用于实时更新进度/日志。
    返回 (exit_code, captured_output)；captured_output 会被截断到 max_capture_lines 行。
    """
    try:
        p = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
    except FileNotFoundError as e:
        return 127, f"找不到命令：{e}\ncmd={cmd}\n"

    out_lines: list[str] = []
    assert p.stdout is not None
    for line in p.stdout:
        if on_line:
            try:
                on_line(line)
            except Exception:
                pass
        out_lines.append(line)
        if len(out_lines) > max_capture_lines:
            out_lines = out_lines[-max_capture_lines:]
    rc = p.wait()
    return rc, "".join(out_lines)


def _to_wav_16k_mono(src: Path, dst: Path) -> tuple[bool, str]:
    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i",
        str(src),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    rc, out = _run(cmd)
    return rc == 0, out


def _whisper_transcribe(wav_path: Path, out_prefix: Path) -> tuple[bool, str]:
    # whisper.cpp 常见参数：-m 模型 -f 输入 -l 语言 -otxt 输出文本 -of 输出前缀
    cmd = [
        WHISPER_BIN,
        "-t",
        str(WHISPER_THREADS),
        "-m",
        WHISPER_MODEL,
        "-l",
        WHISPER_LANGUAGE,
        "-f",
        str(wav_path),
        "-pp",
        "-otxt",
        "-of",
        str(out_prefix),
    ]
    # 运行中实时抓进度：尽量兼容不同输出格式
    progress_re = re.compile(r"progress\\s*=\\s*(\\d+)%", re.IGNORECASE)
    any_percent_re = re.compile(r"(\\d{1,3})%")
    log_tail: list[str] = []
    last_progress: int | None = None

    def on_line(line: str):
        nonlocal last_progress, log_tail
        s = line.strip()
        if not s:
            return

        log_tail.append(s)
        if len(log_tail) > 80:
            log_tail = log_tail[-80:]

        m = progress_re.search(s)
        if m:
            try:
                last_progress = int(m.group(1))
            except Exception:
                pass
        else:
            # 兜底：行里出现 xx% 就取一个
            m2 = any_percent_re.search(s)
            if m2:
                try:
                    v = int(m2.group(1))
                    if 0 <= v <= 100:
                        last_progress = v if last_progress is None else max(last_progress, v)
                except Exception:
                    pass

        # out_prefix.name == job_id（调用者传入 WORK_DIR/job_id）
        if last_progress is not None:
            _set_job(
                str(out_prefix.name),
                progress=last_progress,
                message=f"转写中… {last_progress}%",
                log_tail=log_tail,
            )
        else:
            _set_job(str(out_prefix.name), log_tail=log_tail)

    rc, out = _run_stream(cmd, cwd=ROOT_DIR, on_line=on_line)
    return rc == 0, out


def _worker(job_id: str, src_path: Path):
    _set_job(job_id, status="running", message="开始处理音频…", started_at=time.time())
    try:
        if not Path(WHISPER_MODEL).exists():
            _set_job(
                job_id,
                status="error",
                message=f"模型文件不存在：{WHISPER_MODEL}（请下载 ggml 模型并放到 models/ 目录）",
            )
            return

        wav_path = WORK_DIR / f"{job_id}.wav"
        _set_job(job_id, message="转码中（ffmpeg）…", progress=0)
        ok, ffmpeg_log = _to_wav_16k_mono(src_path, wav_path)
        if not ok:
            _set_job(job_id, status="error", message="ffmpeg 转换失败（请确认已安装 ffmpeg）", log=ffmpeg_log)
            return

        _set_job(job_id, status="running", message="开始转写（Whisper）…", progress=0)
        out_prefix = WORK_DIR / f"{job_id}"
        ok, whisper_log = _whisper_transcribe(wav_path, out_prefix)
        if not ok:
            _set_job(job_id, status="error", message="Whisper 转写失败（请确认 whisper 可执行文件可用）", log=whisper_log)
            return

        txt_path = WORK_DIR / f"{job_id}.txt"
        if not txt_path.exists():
            # 有的版本会生成 out_prefix + ".txt"
            alt = Path(str(out_prefix) + ".txt")
            if alt.exists():
                txt_path = alt

        text = txt_path.read_text(encoding="utf-8", errors="ignore") if txt_path.exists() else ""
        _set_job(job_id, status="done", message="完成", text=text, finished_at=time.time(), log=whisper_log)
    except Exception as e:
        _set_job(job_id, status="error", message=f"服务异常：{e}")


@app.get("/")
def index():
    return send_from_directory(str(ROOT_DIR), "index.html")


@app.get("/README.md")
def readme():
    return send_from_directory(str(ROOT_DIR), "README.md")


@app.post("/api/transcribe")
def transcribe():
    if not Path(WHISPER_MODEL).exists():
        return (
            jsonify(
                {
                    "error": f"模型文件不存在：{WHISPER_MODEL}。请下载 ggml 模型并放到项目根目录 models/ 下（例如 models/ggml-small.bin）。"
                }
            ),
            400,
        )
    if "file" not in request.files:
        return jsonify({"error": "缺少文件字段 file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "文件名为空"}), 400

    job_id = uuid.uuid4().hex
    suffix = Path(f.filename).suffix or ".audio"
    src_path = UPLOAD_DIR / f"{job_id}{suffix}"
    f.save(str(src_path))

    _set_job(job_id, status="queued", message="已接收，排队中…", created_at=time.time())
    t = threading.Thread(target=_worker, args=(job_id, src_path), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.get("/api/jobs/<job_id>")
def job(job_id: str):
    j = _get_job(job_id)
    if not j:
        return jsonify({"error": "job 不存在"}), 404
    # 只返回必要字段，避免日志过大
    resp = {
        "job_id": job_id,
        "status": j.get("status"),
        "message": j.get("message"),
        "progress": j.get("progress"),
        "text": j.get("text", ""),
        "log_tail": j.get("log_tail", []),
    }
    return jsonify(resp)


@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "whisper_bin": WHISPER_BIN,
            "whisper_bin_path": shutil.which(WHISPER_BIN) if WHISPER_BIN else None,
            "ffmpeg_bin": FFMPEG_BIN,
            "ffmpeg_bin_path": shutil.which(FFMPEG_BIN) if FFMPEG_BIN else None,
            "model": WHISPER_MODEL,
            "model_exists": Path(WHISPER_MODEL).exists(),
            "language": WHISPER_LANGUAGE,
            "max_mb": MAX_CONTENT_LENGTH_MB,
        }
    )


if __name__ == "__main__":
    # 绑定 127.0.0.1：只在本机使用
    port = int(_env("PORT", "8000"))
    app.run(host="127.0.0.1", port=port, debug=True, threaded=True)

