# Blog Pipeline

Autonomous publishing **agent** that automatically moves Obsidian notes to the Docusaurus blog (Turkish + English).

## Overview

I built an **agentic publishing pipeline** (agent workflow) using **LangGraph**:

- **parse_and_assets** — reads the Markdown file, rewrites Obsidian wiki-links and standard image links to Docusaurus asset paths.
- **translate** — translates the Turkish content into English via Gemini with strict constraints (code blocks and SVGs are preserved as-is, translation-only, order/scoring kept). Falls back to local Ollama models if Gemini fails.
- **write_files** — writes Turkish and English content into the Docusaurus blog directories with generated frontmatter.
- **human_review** — starts the local Docusaurus server and waits for human approval (human-in-the-loop).

The frontmatter is generated from the slug (auto title from slug; user-provided tags via `--tags` or interactive prompt).

## Setup

```bash
pip install -r requirements.txt
```

## Environment Variables (.env)

- `GEMINI_API_KEY` — LLM API key (Gemini)
- `DOCUSAURUS_ROOT` — Docusaurus root directory
- `TR_BLOG_DIR` — Turkish blog directory
- `EN_BLOG_DIR` — English blog directory
- `STATIC_IMG_DIR` — Static images directory
- `OLLAMA_BASE_URL` — Local Ollama endpoint (optional)
- `OLLAMA_API_KEY` — Local Ollama api key (optional)

## Usage

```bash
python main.py "<obsidian path>/<file name>.md" --slug YYYY-MM-DD-slug-name --tags tag1,tag2
```

- **Argument:** Path to the `.md` file (must be a valid path from the Obsidian folder).
- **`--slug`:** Optional. Auto-generated as `YYYY-MM-DD-<file-name>` if not provided.

After running the pipeline:

1. 📂 Reads Markdown, moves images (`static/img/blog/<slug>/`).
2. 🌐 Translates to English via **Gemini** in strict mode (code blocks and SVGs stay intact, only text is translated).
3. 💾 Writes Turkish and English content into the Docusaurus blog directories.
4. 🚀 Starts local Docusaurus server and waits for human approval (human-in-the-loop).
