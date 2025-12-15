# 语音转文字工具（本地离线版）

一个最简单的 **本地部署** Web 版语音转文字工具：浏览器上传音频文件，本机后端使用 **whisper.cpp（`whisper-cpp`）** 离线转写为文字。

## 适合你的机器吗（Mac Pro M4 / 16GB / 1小时音频）

**可以。**建议从 `small` 模型开始（速度/准确率平衡），1 小时音频转写用时较长属于正常现象。

- **推荐模型**：`ggml-small.bin`（中文普通话性价比好）
- **更快**：`ggml-base.bin`
- **更准但更慢/更吃资源**：`ggml-medium.bin`（不建议一上来就 large）

## 依赖（尽量少）

- **Python 3**（只用来跑一个最小后端）
- **ffmpeg**（把各种音频统一转成 16kHz 单声道 wav）
- **whisper.cpp / whisper-cpp**（离线转写引擎）
- **模型文件**（例如 `models/ggml-small.bin`）

## macOS 安装依赖（Homebrew）

如果你已安装 Homebrew：

```bash
brew install ffmpeg whisper-cpp
```

> 后端默认会自动探测 `whisper-cli`（Homebrew 常见）/`whisper-cpp`；也可通过环境变量指定（见下方）。

## 下载模型（放到 models 目录）

你需要在项目根目录创建 `models/`，并把模型文件放进去，例如：

- `models/ggml-small.bin`

模型下载地址会随版本变化，你可以从 whisper.cpp 官方仓库说明中下载对应 `ggml-*.bin` 模型文件。

## 运行服务

在项目目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python backend/app.py
```

然后用浏览器打开：

- `http://127.0.0.1:8000`

## 使用方法

1. 打开 `http://127.0.0.1:8000`
2. 上传音频文件（支持拖拽）
3. 点击“开始转文字”
4. 等待转写完成（1 小时音频可能需要较长时间）

## LLM 匹配（OpenRouter / DeepSeek）

你可以把 `录音.txt`（转写文本） + `questions.txt`（问题模板）通过 OpenRouter 调用大模型，输出“问题-答案匹配”的 JSON 结果。

1. 在页面下方找到 **LLM 匹配（OpenRouter / DeepSeek）**
2. 输入 **OpenRouter API Key**
3. 填写模型名（默认：`deepseek/deepseek-chat`）
4. 选择两个文件：`录音.txt` 和 `questions.txt`（或 `questions.json`）
5. 点击“开始匹配”，完成后可“下载结果”

> 说明：API Key 仅在本次请求中使用，不会写入本地文件或持久化保存。

## 环境变量（可选）

- **WHISPER_BIN**：whisper 可执行文件名/路径，默认 `whisper-cpp`
-（Homebrew 通常是 `whisper-cli`）
- **WHISPER_MODEL**：模型路径，默认 `models/ggml-small.bin`
- **WHISPER_LANGUAGE**：语言，默认 `zh`
- **PORT**：端口，默认 `8000`
- **MAX_CONTENT_LENGTH_MB**：最大上传大小（MB），默认 `1024`

示例：

```bash
export WHISPER_MODEL="models/ggml-small.bin"
export WHISPER_LANGUAGE="zh"
python backend/app.py
```

## 说明

- 这是**离线**方案：音频不会上传到云端
- 转写速度取决于模型大小、音频质量、设备负载等
