# Bilingual Ebook Maker / 双语电子书制作器

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Platform-Cross--Platform-lightgrey?style=flat-square" alt="Platform">
</p>

<p align="center">
  <strong>English</strong> | <a href="#中文说明">中文说明</a>
</p>

---

## ✨ Features

- 📚 **Upload EPUB or PDF** — Drag & drop support with artistic web UI
- 🌐 **Auto Translation** — English to Chinese with real-time progress tracking
- 📖 **Bilingual Output** — Side-by-side English/Chinese paragraphs in beautiful EPUB format
- 🎯 **IELTS 7+ Vocabulary** — Automatically highlights IELTS Band 7 words with phonetics and Chinese definitions
- 📊 **Progress Tracking** — Real-time WebSocket progress updates with visual indicators
- 📁 **Auto Save** — Output saved to the same directory as the original file
- 📋 **Completion Report** — Detailed statistics after translation
- 🐳 **Docker Ready** — One-command deployment, cross-platform compatible
- 🎨 **Artistic UI** — Dark theme with gold accents and smooth animations

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Pull and run
docker pull getyourhub/bilingual-ebook-maker:latest
docker run -p 8000:8000 -v ./uploads:/app/uploads -v ./outputs:/app/outputs getyourhub/bilingual-ebook-maker:latest

# Or use docker-compose
docker-compose up -d
```

Then open http://localhost:8000 in your browser.

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/getyourhub/bilingual-ebook-maker.git
cd bilingual-ebook-maker

# Install dependencies
pip install -r requirements.txt

# Optional: Install Calibre for better EPUB handling
# macOS: brew install calibre
# Ubuntu: sudo apt-get install calibre
# Windows: Download from https://calibre-ebook.com

# Run the application
python app.py
```

## 📖 How to Use

1. **Upload** — Drag & drop your .epub or .pdf file onto the upload area
2. **Review** — Check the book information displayed
3. **Translate** — Click "Start Translation" and watch the real-time progress
4. **Download** — Get your bilingual EPUB with IELTS vocabulary highlights

## 🎯 IELTS Vocabulary Feature

The app automatically identifies and marks IELTS Band 7 vocabulary:

- **In-text highlighting** — Words are highlighted with tooltips showing phonetics and definitions
- **Chapter summaries** — Each chapter includes a vocabulary card grid
- **Master vocabulary list** — Complete alphabetical list at the end of the book
- **Visual markers** — Color-coded with pronunciation guides

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Frontend**: Vanilla JS, CSS3 with animations
- **Translation**: Google Translate API (via deep-translator)
- **EPUB**: ebooklib, BeautifulSoup4
- **PDF**: pdfplumber
- **Container**: Docker, Docker Compose

## 📁 Project Structure

```
bilingual-ebook-maker/
├── app.py                 # Main FastAPI application
├── translator.py          # Translation & IELTS word detection
├── epub_handler.py        # EPUB/PDF parsing & building
├── progress_manager.py    # Progress tracking
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose config
├── data/
│   └── ielts_words.json   # IELTS 7+ vocabulary database
├── static/
│   ├── css/
│   │   └── style.css      # Artistic dark theme styles
│   └── js/
│       └── app.js         # Frontend logic
└── templates/
    └── index.html         # Web UI template
```

## 🔧 Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_DIR` | `./uploads` | Directory for uploaded files |
| `OUTPUT_DIR` | `./outputs` | Directory for translated files |
| `PORT` | `8000` | Server port |

## 📄 License

MIT License — feel free to use and modify.

---

# 中文说明

## ✨ 功能特点

- 📚 **上传 EPUB 或 PDF** — 支持拖拽上传，艺术感十足的 Web 界面
- 🌐 **自动翻译** — 英文翻译为中文，实时显示翻译进度
- 📖 **双语输出** — 英中对照段落，生成精美 EPUB 格式
- 🎯 **雅思7分词汇** — 自动标注雅思7分高频词汇，显示音标和中文释义
- 📊 **进度追踪** — WebSocket 实时进度更新，可视化进度指示器
- 📁 **自动保存** — 翻译完成的文件自动保存在原电子书目录
- 📋 **完成报告** — 翻译完成后显示详细统计信息
- 🐳 **Docker 就绪** — 一条命令部署，跨平台兼容
- 🎨 **艺术界面** — 暗色主题搭配金色点缀，流畅动画效果

## 🚀 快速开始

### 使用 Docker（推荐）

```bash
# 拉取并运行
docker pull getyourhub/bilingual-ebook-maker:latest
docker run -p 8000:8000 -v ./uploads:/app/uploads -v ./outputs:/app/outputs getyourhub/bilingual-ebook-maker:latest

# 或使用 docker-compose
docker-compose up -d
```

然后在浏览器中打开 http://localhost:8000

### 手动安装

```bash
# 克隆仓库
git clone https://github.com/getyourhub/bilingual-ebook-maker.git
cd bilingual-ebook-maker

# 安装依赖
pip install -r requirements.txt

# 可选：安装 Calibre 以获得更好的 EPUB 处理能力
# macOS: brew install calibre
# Ubuntu: sudo apt-get install calibre
# Windows: 从 https://calibre-ebook.com 下载

# 运行应用
python app.py
```

## 📖 使用方法

1. **上传** — 将 .epub 或 .pdf 文件拖放到上传区域
2. **预览** — 查看显示的书籍信息
3. **翻译** — 点击"开始翻译"，观看实时进度
4. **下载** — 获取带有雅思词汇标注的双语 EPUB

## 🎯 雅思词汇功能

应用会自动识别并标注雅思7分高频词汇：

- **文内高亮** — 词汇高亮显示，鼠标悬停可查看音标和释义
- **章节总结** — 每章末尾包含词汇卡片网格
- **总词汇表** — 书末提供完整的字母排序词汇列表
- **视觉标记** — 颜色编码，配有发音指南

## 🛠️ 技术栈

- **后端**: Python 3.11+, FastAPI, Uvicorn
- **前端**: 原生 JS, CSS3 动画
- **翻译**: Google Translate API（通过 deep-translator）
- **EPUB**: ebooklib, BeautifulSoup4
- **PDF**: pdfplumber
- **容器**: Docker, Docker Compose

## 📄 许可证

MIT 许可证 — 可自由使用和修改
