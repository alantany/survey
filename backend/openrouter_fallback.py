from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable


def load_models_from_js(js_path: Path) -> list[str]:
    """
    读取形如 module.exports = [ "a", "b", ... ] 的 JS 配置文件，提取字符串模型列表。
    - 仅做最小解析：提取所有引号包裹的字符串，忽略注释/逗号/换行。
    """
    if not js_path.exists():
        return []
    text = js_path.read_text(encoding="utf-8", errors="ignore")
    # 支持 "..." 或 '...'
    items = re.findall(r"""['"]([^'"]+)['"]""", text)
    models: list[str] = []
    for s in items:
        m = (s or "").strip()
        if m and m not in models:
            models.append(m)
    return models


def should_try_next_model(err: Exception) -> bool:
    """
    判断是否应该切换到下一个模型（额度用完/限流/权限等）。
    """
    s = str(err or "")
    # 来自 backend/app.py: "OpenRouter HTTPError: {code} {raw}"
    m = re.search(r"HTTPError:\s*(\d+)", s)
    code = int(m.group(1)) if m else None
    # 402: 额度/计费；403: 权限；429: 限流；404: 模型/端点不存在；5xx: 网关/服务异常（可尝试换模型）
    if code in (402, 403, 404, 429, 500, 502, 503, 504):
        return True
    lowered = s.lower()
    keywords = [
        "insufficient",
        "quota",
        "rate",
        "limit",
        "exceeded",
        "payment",
        "billing",
        "credits",
        "too many requests",
        "no endpoints found",
        "model not found",
        "not found",
        "timeout",
        "timed out",
        "empty content",
        "inner error",
        "filtered",
        "refused",
    ]
    return any(k in lowered for k in keywords)


def chat_with_model_fallback(
    *,
    api_key: str,
    model_candidates: list[str],
    prompt: str,
    max_tokens: int,
    call_fn: Callable[[str, str, str, int], dict],
) -> tuple[str, dict]:
    """
    依次尝试多个模型，直到成功；如果全部失败，抛出最后一次错误。
    返回 (used_model, response_json)。
    """
    last_err: Exception | None = None
    errors: list[tuple[str, str]] = []
    for model in model_candidates:
        try:
            resp = call_fn(api_key, model, prompt, max_tokens)
            
            # 手动校验响应有效性（DeepSeek 等免费模型可能返回 200 但 content 为空）
            if isinstance(resp, dict) and "choices" in resp and len(resp["choices"]) > 0:
                first_choice = resp["choices"][0]
                # 某些模型会在 choice 对象里直接放个 error
                if "error" in first_choice and first_choice["error"]:
                    raise RuntimeError(f"Model returned inner error: {first_choice['error']}")
                # 检查 content 是否为空
                msg_content = first_choice.get("message", {}).get("content", "")
                if not msg_content:
                    raise RuntimeError(f"Model returned empty content (possibly filtered or refused): {resp}")
            
            return model, resp
        except Exception as e:
            last_err = e
            msg = str(e or "")
            if len(msg) > 300:
                msg = msg[:300] + "..."
            errors.append((model, msg))
            print(f">>> Fallback: Model {model} failed with error: {msg}", flush=True)
            if should_try_next_model(e):
                print(f">>> Fallback: Attempting next model due to retryable error.", flush=True)
                continue
            raise
    if last_err:
        # 汇总所有尝试过的模型及错误，方便排查模型名/额度问题
        summary = "; ".join([f"{m}: {em}" for m, em in errors]) if errors else str(last_err)
        raise RuntimeError(f"所有模型都调用失败：{summary}")
    raise RuntimeError("没有可用的模型候选（model_candidates 为空）")


def build_model_candidates(
    *,
    root_dir: Path,
    cfg: dict[str, Any],
) -> list[str]:
    """
    构造模型候选列表（优先级从高到低）：
    1) config.json: openrouter_models（数组）
    2) 项目根目录: openrouter-models.js
    3) config.json: openrouter_model（单个字符串）
    """
    models: list[str] = []

    v = cfg.get("openrouter_models")
    if isinstance(v, list):
        for item in v:
            s = (str(item) if item is not None else "").strip()
            if s and s not in models:
                models.append(s)

    if not models:
        js_path = root_dir / "openrouter-models.js"
        models = load_models_from_js(js_path)

    if not models:
        single = (cfg.get("openrouter_model") or "").strip()
        if single:
            models = [single]

    return models


