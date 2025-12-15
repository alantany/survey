import os
import uuid
import json
import time
import threading
import subprocess
import shutil
import re
import urllib.request
import urllib.error
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file
from docx import Document


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
WORK_DIR = DATA_DIR / "work"
SURVEY_DIR = ROOT_DIR / "survey"
CONFIG_PATH = ROOT_DIR / "config.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)
SURVEY_DIR.mkdir(parents=True, exist_ok=True)


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


def _load_local_config() -> dict:
    """
    读取本地 config.json（被 .gitignore 忽略）或环境变量。
    - OPENROUTER_API_KEY
    - OPENROUTER_MODEL
    """
    cfg: dict = {}
    try:
        if CONFIG_PATH.exists():
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}

    api_key = (cfg.get("openrouter_api_key") if isinstance(cfg, dict) else None) or os.environ.get("OPENROUTER_API_KEY")
    model = (cfg.get("openrouter_model") if isinstance(cfg, dict) else None) or os.environ.get("OPENROUTER_MODEL") or "tngtech/deepseek-r1t2-chimera:free"
    return {"openrouter_api_key": (api_key or "").strip(), "openrouter_model": (model or "").strip()}


def _strip_code_fence(s: str) -> str:
    """
    去掉常见的 ```json ... ``` 包裹，便于解析 JSON。
    """
    t = (s or "").strip()
    if t.startswith("```"):
        # ```json\n...\n``` 或 ```\n...\n```
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
        t = t.strip()
    return t

def _safe_basename(name: str) -> str:
    """
    生成一个适合做文件名的 basename（尽量保留中文/英文/数字/_/-，其他替换为 _）
    """
    base = Path(name).stem.strip() or "audio"
    base = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", base)
    return base[:80] or "audio"


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

        # 额外：在 survey/ 目录落一份结果，方便你在“访谈材料目录”直接看到输出
        original_name = (_get_job(job_id) or {}).get("original_filename") or f"{job_id}{src_path.suffix}"
        out_name = f"{_safe_basename(original_name)}_{job_id}.txt"
        (SURVEY_DIR / out_name).write_text(text, encoding="utf-8")
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

    _set_job(
        job_id,
        status="queued",
        message="已接收，排队中…",
        created_at=time.time(),
        original_filename=f.filename,
    )
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


@app.get("/api/jobs/<job_id>/download")
def download_job_text(job_id: str):
    """
    下载转写文本（.txt）。优先使用内存里的 text；否则读取 data/work/<job_id>.txt
    """
    j = _get_job(job_id)
    if j and j.get("text"):
        tmp = WORK_DIR / f"{job_id}.txt"
        tmp.write_text(j.get("text", ""), encoding="utf-8")
        return send_file(
            str(tmp),
            mimetype="text/plain; charset=utf-8",
            as_attachment=True,
            download_name=f"{job_id}.txt",
        )

    txt_path = WORK_DIR / f"{job_id}.txt"
    if not txt_path.exists():
        alt = WORK_DIR / f"{job_id}.txt"
        if not alt.exists():
            return jsonify({"error": "转写文本不存在或任务未完成"}), 404
        txt_path = alt

    return send_file(
        str(txt_path),
        mimetype="text/plain; charset=utf-8",
        as_attachment=True,
        download_name=f"{job_id}.txt",
    )


def _extract_questions_from_docx(docx_path: Path) -> list[dict]:
    """
    从 docx 里提取“编号清晰”的问题。
    输出: [{id: '1', text: '...'}, ...]
    """
    doc = Document(str(docx_path))
    questions: list[dict] = []

    # 常见编号：1. / 1、/ 1) / （1）/ 1）/ Q1 / Q1:
    q_re = re.compile(r"^(?:Q\\s*)?(\\d{1,3})\\s*(?:[\\.、:：\\)）]|（\\1）)\\s*(.+)$", re.IGNORECASE)

    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if not t:
            continue
        m = q_re.match(t)
        if not m:
            continue
        qid = m.group(1).strip()
        qtext = m.group(2).strip()
        if qtext:
            questions.append({"id": qid, "text": qtext})

    return questions


def _extract_full_text_from_docx(docx_path: Path) -> str:
    doc = Document(str(docx_path))
    lines: list[str] = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            lines.append(t)
    return "\n".join(lines)


def _build_qa_prompt(transcript: str, questions_text: str) -> str:
    # 目标：输出“人类可读、可二次加工”的纯文本（用户已验证效果好）
    return f"""你是一个严谨的定性研究助理。现在有两份文本：

【问题模板 questions】：
{questions_text}

【采访转写 transcript】：
{transcript}

任务：
1) 识别并区分“采访者/受访者”的说话段落（转写里没有显式标记，请你根据语气、问句/追问、承接关系推断；不确定就标记为 unknown）。
2) 按照 questions 的题号，把 transcript 中“受访者的回答内容”匹配到对应问题下。
3) 你需要输出**纯文本**，格式必须严格按下面模板（不要 JSON，不要 Markdown code block）：

输出模板（示例）：
三、学龄前康复阶段（17 题）

最初发现孩子可能存在发育异常的人是谁？

录音内容：......

从孩子最初被怀疑异常，到最终被确诊孤独症，整个过程用了多长时间？

录音中未提及（或：录音内容：......）

……

规则：
- 以 questions 中的四大类标题作为分组标题（原样输出标题）
- 每个问题按“问题原文 + 空行 + 录音内容：xxx/录音中未提及”输出
- “录音内容”要尽量忠实原话，可做轻微归纳，但不要虚构
- 若只能推断到部分信息，也要写在“录音内容：”里，并说明不确定点（例如“可能/推测”）
- 如果某题确实没有信息，统一写：录音中未提及。
- 不要输出任何与任务无关的解释、分析、置信度、JSON、代码块。

现在开始输出最终结果（只输出结果正文）： 
"""


def _openrouter_chat(api_key: str, model: str, prompt: str) -> dict:
    """
    OpenRouter（OpenAI 兼容）接口：
    POST https://openrouter.ai/api/v1/chat/completions
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个擅长定性访谈分析与信息抽取的助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # OpenRouter 推荐带上这两个 header（可选）
            "HTTP-Referer": "http://127.0.0.1:8000",
            "X-Title": "Local Survey Tool",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
        raise RuntimeError(f"OpenRouter HTTPError: {e.code} {raw}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenRouter URLError: {e}")


@app.post("/api/bundle")
def make_bundle():
    """
    将“问题清单(docx)” + “转写文本(job_id)” 打包成 JSON，方便用户调用自己的 LLM API。
    不在服务端调用任何大模型。
    """
    job_id = (request.form.get("job_id") or "").strip()
    if not job_id:
        return jsonify({"error": "缺少 job_id"}), 400

    txt_path = WORK_DIR / f"{job_id}.txt"
    if not txt_path.exists():
        return jsonify({"error": f"找不到转写文本：{txt_path}（请确认任务已完成）"}), 404

    if "docx" not in request.files:
        return jsonify({"error": "缺少 docx 文件字段 docx"}), 400

    f = request.files["docx"]
    if not f.filename or not f.filename.lower().endswith(".docx"):
        return jsonify({"error": "请上传 .docx 文件"}), 400

    bundle_id = uuid.uuid4().hex
    docx_path = WORK_DIR / f"{bundle_id}.docx"
    f.save(str(docx_path))

    try:
        questions = _extract_questions_from_docx(docx_path)
        docx_text = _extract_full_text_from_docx(docx_path)
    except Exception as e:
        return jsonify({"error": f"解析 docx 失败：{e}"}), 400

    transcript = txt_path.read_text(encoding="utf-8", errors="ignore")
    payload = {
        "job_id": job_id,
        "docx_name": f.filename,
        # 你可以把 docx_text 直接喂给你的大模型（比我用正则抽题更“语义完整”）
        "docx_text": docx_text,
        # 同时保留我抽取的结构化 questions，用于约束/校验（可选使用）
        "questions": questions,
        "transcript": transcript,
    }

    out_path = WORK_DIR / f"bundle-{job_id}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return send_file(
        str(out_path),
        mimetype="application/json; charset=utf-8",
        as_attachment=True,
        download_name=f"bundle-{job_id}.json",
    )


@app.post("/api/llm/match")
def llm_match():
    """
    通过 OpenRouter 调用大模型做“问题-答案匹配”。
    注意：不保存 key，不做持久化，只做一次请求。
    """
    body = request.get_json(silent=True) or {}
    transcript = (body.get("transcript") or "").strip()
    questions = (body.get("questions") or "").strip()

    cfg = _load_local_config()
    api_key = cfg.get("openrouter_api_key", "")
    model = cfg.get("openrouter_model", "tngtech/deepseek-r1t2-chimera:free")

    if not api_key:
        return jsonify({"error": "未配置 OpenRouter API Key：请在项目根目录创建 config.json（参考 config.example.json）"}), 400
    if not transcript:
        return jsonify({"error": "缺少 transcript（录音转写文本）"}), 400
    if not questions:
        return jsonify({"error": "缺少 questions（问题模板文本）"}), 400

    prompt = _build_qa_prompt(transcript=transcript, questions_text=questions)
    try:
        resp = _openrouter_chat(api_key=api_key, model=model, prompt=prompt)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # 兼容 OpenAI 风格响应
    content = ""
    try:
        content = resp["choices"][0]["message"]["content"]
    except Exception:
        content = ""

    cleaned = _strip_code_fence(content)

    return jsonify(
        {
            "model": model,
            "content": content,
            "cleaned": cleaned,
        }
    )

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

