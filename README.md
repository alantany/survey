# 语音转文字工具（本地离线版）

一个最简单的 **本地部署** Web 版语音转文字工具：浏览器上传音频文件，本机后端使用 **whisper.cpp（`whisper-cpp`）** 离线转写为文字。

## 这是什么 / 适合谁用

- **适合**：研究访谈/会议录音等，想在本机离线转写（不上传云端），并且用浏览器完成“上传-转写-查看结果”的流程。
- **不适合**：需要多人在线协作、强权限/审计、或要在公网直接暴露服务（除非你自己加反向代理与鉴权）。

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

## 项目结构（你会看到的目录）

- `index.html`：前端页面（上传音频、查看转写、LLM 匹配 UI）
- `backend/app.py`：后端服务（转写任务、docx 工具、LLM 匹配接口）
- `models/`：放 whisper.cpp 的 `ggml-*.bin` 模型文件（自行下载）
- `survey/`：你的访谈素材目录（音频、docx、转写输出等；默认不会提交到 GitHub）

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

## 本地运行（开发/日常使用）

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

你可以把 `录音.txt`（转写文本） + `questions.txt`（问题模板）通过 OpenRouter 调用大模型，输出**按四大类分组的“问题-答案匹配”可读文本**（更便于人工阅读和后续二次处理）。

### 一次性配置（普通用户只做一次）

在项目根目录复制一份配置文件：

```bash
cp config.example.json config.json
```

编辑 `config.json`，填入：
- `openrouter_api_key`
- `openrouter_model`（默认已给出一个免费模型）
- `openrouter_max_tokens`（可选，控制模型**单次输出长度上限**；输出过长可能需要适当调大）

> `config.json` 已被 `.gitignore` 忽略，不会同步到 GitHub。

1. 在页面下方找到 **LLM 匹配（OpenRouter / DeepSeek）**
2. 选择两个文件：`录音.txt` 和 `questions.txt`
3. 点击“开始匹配”，完成后可“下载结果”

> 说明：API Key 存在本机 `config.json`，页面不要求用户输入（更适合给普通访谈员使用）。
> 页面完成后会在状态提示里展示 `finish_reason`（如果接口返回），用于判断是否“正常结束(stop)”还是“长度截断(length)”。

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

## 部署方案（长期运行 / 自启动）

下面是“在你自己的电脑上长期跑着”的最简单方案（不引入 Docker/Nginx 也能用）。

### 方案 A：前台运行（最简单）

适合你自己临时用：

```bash
cd /path/to/survey
source .venv/bin/activate
python backend/app.py
```

### 方案 B：后台运行（关闭终端仍可用）

```bash
cd /path/to/survey
source .venv/bin/activate
nohup python backend/app.py > server.log 2>&1 &
```

停止：

```bash
pkill -f "python backend/app.py"
```

### 方案 C：macOS 自启动（LaunchAgent，推荐）

1) 创建 `~/Library/LaunchAgents/com.survey.whisper.plist`（把路径改成你自己的）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>com.survey.whisper</string>
    <key>WorkingDirectory</key><string>/path/to/survey</string>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/zsh</string>
      <string>-lc</string>
      <string>source .venv/bin/activate &amp;&amp; python backend/app.py</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/path/to/survey/server.log</string>
    <key>StandardErrorPath</key><string>/path/to/survey/server.log</string>
  </dict>
</plist>
```

2) 加载并启动：

```bash
launchctl load -w ~/Library/LaunchAgents/com.survey.whisper.plist
launchctl start com.survey.whisper
```

3) 停止/卸载：

```bash
launchctl stop com.survey.whisper
launchctl unload -w ~/Library/LaunchAgents/com.survey.whisper.plist
```

### 可选：只允许本机访问（更安全）

默认用 `http://127.0.0.1:8000` 即只在本机可访问；如果你把服务监听到 `0.0.0.0` 并打算在局域网访问，建议加上反向代理与鉴权（否则同网段的人都可能访问）。

## 云端部署（OCI / Linux，方案 A：云端离线转写 + Web）

> 说明：云端离线转写会比较吃 CPU，建议先从 `ggml-base.bin` 或 `ggml-small.bin` 开始；并发务必控制为 1。

### 0）前提

- OCI 实例能出网（用于 `docker build` 拉依赖、下载模型等）
- 安全组/安全列表放行端口（如果要公网直连）：`8000/tcp`
  - 更安全的方式：不开放 8000，使用 **SSH 隧道** 访问（见下方）

### 1）在 OCI 上安装 Docker（如果已装可跳过）

不同镜像安装方式不同；你可以先验证：

```bash
docker --version
docker compose version
```

### 2）拉代码并准备配置

```bash
git clone https://github.com/alantany/survey.git
cd survey
cp config.example.json config.json
vi config.json
```

> 注意：`config.json` 已被忽略，不会进 Git。

### 3）准备模型文件（放到 models/）

```bash
mkdir -p models
# 把 ggml-small.bin 放到 models/ 目录，例如：
# models/ggml-small.bin
```

### 4）启动（Docker Compose）

```bash
docker compose -f docker-compose.oci.yml up -d --build
docker compose -f docker-compose.oci.yml logs -f --tail=200
```

健康检查（容器启动后）：

```bash
curl -s http://127.0.0.1:8000/api/health | head
```

### 5）访问方式

- **方式 A（推荐，更安全）**：SSH 隧道，不开放 8000

```bash
ssh -N -L 8000:127.0.0.1:8000 opc@YOUR_SERVER_IP
```

然后在本机浏览器打开：

- `http://127.0.0.1:8000`

- **方式 B（公网直连）**：放行 `8000/tcp` 后访问 `http://YOUR_SERVER_IP:8000`

### 6）常用运维命令

```bash
docker compose -f docker-compose.oci.yml ps
docker compose -f docker-compose.oci.yml restart
docker compose -f docker-compose.oci.yml down
```

## 说明

- 这是**离线**方案：音频不会上传到云端
- 转写速度取决于模型大小、音频质量、设备负载等
