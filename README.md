# 问卷调查AI智能助手

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**专为问卷调查和深度访谈场景设计的AI驱动智能转写与分析系统**

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用指南](#使用指南) • [配置说明](#配置说明)

</div>

---

## 📋 项目简介

问卷调查AI智能助手是一个集成了**语音识别**、**文本格式化**、**智能问答匹配**等多项AI能力的Web应用系统。系统支持本地离线转写和在线API转写两种模式，能够将传统的人工访谈录音整理工作自动化，大幅提升研究效率。

### 核心价值

- ⚡ **效率提升**：将数小时的人工转录工作缩短至分钟级
- 🎯 **质量保证**：基于大语言模型的内容匹配与格式化，确保输出标准化
- 💰 **成本降低**：支持本地离线部署，减少云端服务依赖
- 🚀 **易于使用**：Web界面操作，零技术门槛

---

## ✨ 功能特性

### 🎤 语音转文字
- **本地模式**：使用 Whisper.cpp 离线转写，完全本地化处理，保障数据隐私
- **在线模式**：集成科大讯飞语音识别API，支持新版/旧版接口自动切换
- **多格式支持**：MP3、WAV、OGG、M4A 等常见音频格式
- **智能预处理**：FFmpeg统一转码为16kHz单声道WAV，确保识别准确率

### 📝 AI智能格式化
- 将未标注说话人的转写文本自动整理为「采访者 / 受访者」对话格式
- 基于大语言模型的语义理解，自动识别说话人角色
- 支持长文本分段处理，避免上下文截断
- 输出格式规范，一行一句，便于阅读

### 🔍 智能问答匹配
- 将转写内容按照预设的问题清单进行智能匹配
- 支持从Word文档（.docx）自动提取问题列表
- 基于大语言模型的语义匹配，而非简单关键词搜索
- 自动处理未提及内容（标注"录音中未提及"）

### 🔄 多模型容错机制
- 支持配置多个AI模型（OpenRouter平台）
- 当某个模型遇到额度不足/限流/404错误时，自动切换到下一个模型
- 可配置模型优先级，确保高优先级模型优先使用
- 提升系统可用性与稳定性

### 📄 文本文件直接上传
- 支持直接上传已有文本文件进行格式化
- 无需重新转写，直接进入格式化流程
- 提升使用灵活性

---

## 🛠️ 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| **前端** | HTML5 + JavaScript | 纯前端实现，无需构建工具 |
| **后端** | Python 3 + Flask | 轻量级Web框架，RESTful API |
| **语音识别** | Whisper.cpp（本地）| 离线转写，支持中文 |
| | 科大讯飞API（在线）| 备用方案，支持大规模并发 |
| **AI处理** | OpenRouter API | 多模型聚合，自动容错 |
| **文本处理** | OpenCC | 繁体转简体标准化 |
| **部署** | Docker + Docker Compose | 支持本地/云端部署 |

---

## 🚀 快速开始

### 系统要求

- **操作系统**：macOS / Linux
- **Python**：3.8+
- **内存**：8GB+（推荐）
- **磁盘空间**：10GB+（用于模型文件）

### 安装依赖

#### macOS (Homebrew)

```bash
# 安装系统依赖
brew install ffmpeg whisper-cpp

# 下载模型文件（放到 models/ 目录）
mkdir -p models
cd models
# 下载 ggml-small.bin 模型文件
# 下载地址：https://github.com/ggerganov/whisper.cpp
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# 安装 whisper-cpp（参考官方文档）
# https://github.com/ggerganov/whisper.cpp
```

### 安装Python依赖

```bash
# 克隆项目
git clone <your-repo-url>
cd 问卷调查

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

复制配置文件模板并编辑：

```bash
cp config.example.json config.json
```

编辑 `config.json`，配置必要的API密钥：

```json
{
  "openrouter_api_key": "你的OpenRouter API Key",
  "openrouter_model": "tngtech/deepseek-r1t2-chimera:free",
  "openrouter_max_tokens": 8192,
  "stt_api_type": "xunfei",
  "stt_api_appid": "你的科大讯飞APPID",
  "stt_api_key": "你的APIKey",
  "stt_api_secret_key": "你的APISecret"
}
```

### 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
./run.sh start
```

#### 方式二：直接运行

```bash
python backend/app.py
```

#### 方式三：后台运行

```bash
./run.sh start
# 或
nohup python backend/app.py > server.log 2>&1 &
```

### 访问

打开浏览器访问：`http://127.0.0.1:8000`

---

## 📖 使用指南

### 1. 语音转文字

#### 方式A：上传音频文件

1. 点击左侧「上传音频文件」区域，选择音频文件（或直接拖拽）
2. 选择转写模式：**本地转写** 或 **在线转写**
3. 点击「开始转文字」
4. 等待转写完成（1小时音频可能需要较长时间）

#### 方式B：直接上传文本文件

1. 点击右侧「上传文本文件」区域，选择 `.txt` 文本文件
2. 文本内容会自动加载到结果区域
3. 可直接进行格式化操作

### 2. 格式化文本

转写完成后，点击「格式化文本」按钮，系统会：
- 自动识别说话人角色（采访者/受访者）
- 整理为一行一句的标准对话格式
- 输出简体中文

### 3. 智能问答匹配

1. 在「第二步：AI智能匹配」区域
2. 选择转写结果文件（`.txt`）
3. 选择问题模板文件（`.txt` 或 `.docx`）
4. 点击「开始匹配」
5. 等待匹配完成，下载结果

### 4. 下载结果

- **复制文本**：一键复制到剪贴板
- **下载结果**：导出为 `.txt` 文件

---

## ⚙️ 配置说明

### 配置文件结构

`config.json` 支持以下配置项：

```json
{
  // OpenRouter API 配置（用于AI格式化/匹配）
  "openrouter_api_key": "sk-or-v1-...",
  "openrouter_model": "tngtech/deepseek-r1t2-chimera:free",
  "openrouter_max_tokens": 8192,
  
  // 科大讯飞语音识别配置
  "stt_api_type": "xunfei",
  "stt_api_appid": "你的APPID",
  "stt_api_key": "你的APIKey",
  "stt_api_secret_key": "你的APISecret",
  
  // 格式化分段大小（字符数）
  "format_chunk_chars": 8000
}
```

### 多模型配置

在项目根目录创建 `openrouter-models.js`：

```javascript
module.exports = [
  'xiaomi/mimo-v2-flash:free',          // 主模型
  'google/gemini-2.0-flash-exp:free',   // 备份1
  'moonshotai/kimi-k2:free',            // 备份2
  'deepseek/deepseek-r1-0528:free',      // 备份3
];
```

系统会按顺序尝试模型，遇到错误自动切换到下一个。

### 环境变量

支持通过环境变量配置：

```bash
export WHISPER_BIN="whisper-cli"
export WHISPER_MODEL="models/ggml-small.bin"
export WHISPER_LANGUAGE="zh"
export PORT=8000
export HOST=127.0.0.1
export MAX_CONTENT_LENGTH_MB=1024
```

---

## 🐳 Docker 部署

### 构建镜像

```bash
docker build -t survey-assistant .
```

### 使用 Docker Compose

```bash
# 编辑 docker-compose.oci.yml，配置环境变量
docker compose -f docker-compose.oci.yml up -d
```

### 查看日志

```bash
docker compose -f docker-compose.oci.yml logs -f
```

---

## 📡 API 接口

### 转写接口

```bash
# 提交转写任务
POST /api/transcribe
Content-Type: multipart/form-data

file: <audio_file>
mode: local|api
```

### 查询任务状态

```bash
GET /api/jobs/<job_id>
```

### AI格式化

```bash
POST /api/llm/format
Content-Type: application/json

{
  "transcript": "转写文本内容..."
}
```

### AI匹配

```bash
POST /api/llm/match
Content-Type: application/json

{
  "transcript": "转写文本内容...",
  "questions": "问题清单文本..."
}
```

---

## 📁 项目结构

```
问卷调查/
├── backend/
│   ├── app.py                 # Flask后端主程序
│   └── openrouter_fallback.py # 多模型容错模块
├── survey-assistant-ui/       # Next.js UI参考（可选）
├── models/                    # Whisper模型文件目录
├── data/                      # 数据目录
│   ├── uploads/              # 上传文件
│   └── work/                 # 工作文件
├── survey/                   # 输出目录
├── index.html                # 前端页面
├── config.example.json       # 配置模板
├── openrouter-models.js      # 模型列表配置
├── requirements.txt          # Python依赖
├── run.sh                    # 启动脚本
└── README.md                 # 本文档
```

---

## 🔧 常见问题

### Q: 转写速度慢怎么办？

A: 
- 使用更小的模型（如 `ggml-base.bin`）
- 使用在线转写模式（科大讯飞API）
- 检查系统资源占用

### Q: 格式化结果不完整？

A: 
- 检查 `openrouter_max_tokens` 配置是否足够
- 查看状态栏的 `finish_reason`，如果是 `length` 说明被截断
- 系统会自动分段处理长文本

### Q: 模型额度用完了？

A: 
- 在 `openrouter-models.js` 中添加更多模型
- 系统会自动切换到下一个可用模型

### Q: 如何查看详细日志？

A: 
- 查看 `server.log` 文件
- 或访问 `/api/jobs/<job_id>` 查看任务详情

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
# 克隆项目
git clone <your-repo-url>
cd 问卷调查

# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
python backend/app.py
```

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) - 本地语音识别引擎
- [OpenRouter](https://openrouter.ai/) - AI模型聚合平台
- [Flask](https://flask.palletsprojects.com/) - Web框架

---

## 📞 联系方式

如有问题或建议，请提交 [Issue](https://github.com/your-repo/issues)。

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ for researchers and interviewers

</div>
