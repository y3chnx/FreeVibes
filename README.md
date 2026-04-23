<img src="logo.png">

**Free Vibes** is a desktop AI-powered coding environment built with Python and PyQt6.  
It combines an interactive code editor, AI assistant, and terminal into one unified workspace.

Unlike traditional IDEs, Free Vibes is designed to feel like a **real-time AI pair programmer**, helping users write, run, and understand code instantly.

---

## 🚀 Features

### AI Coding Assistant
- Powered by an LLM (NVIDIA-hosted OpenAI-compatible API)
- Streaming responses for real-time interaction
- Context-aware conversation history

### Built-in Code Editor
- Python syntax highlighting
- Auto-indentation
- Clean modern dark UI (VS Code style)
- Instant code execution inside the app

### Interactive Terminal
- Live output display
- Python `exec()` execution environment
- Input handling system for interactive scripts

### File Support
- Save Python files directly from the editor
- Run code instantly without leaving the app

### Modern UI
- Fully custom PyQt6 interface
- Split-pane design (AI chat + editor + terminal)
- Integrated logo and branding

---

## How It Works

Free Vibes integrates three core systems:

1. **AI Chat System**
   - Sends conversation history to an LLM API
   - Streams responses back in real time

2. **Code Editor Engine**
   - Custom Python syntax highlighter
   - Auto-indentation logic for better coding flow

3. **Execution Sandbox**
   - Runs Python code dynamically inside the app
   - Redirects stdout to the built-in terminal

---

## Tech Stack

- Python 3
- PyQt6
- OpenAI-compatible API (NVIDIA hosted model)
- threading + event system for async execution

---

## Project Idea

Free Vibes is built around the idea of a **“Free AI Coding Agent IDE”**:

- A lightweight alternative to expensive tools like Cursor or cloud IDEs
- Combines AI + coding environment in a single desktop app
- Designed to make coding more accessible and interactive

---

## Challenges I Ran Into

- Building a real-time AI streaming system inside PyQt without freezing the UI
- Designing a functional Python code editor with syntax highlighting from scratch
- Handling multi-threaded execution for AI responses and code execution simultaneously
- Managing integration with an OpenAI-compatible API (NVIDIA endpoint)
- Structuring the app so terminal input, AI chat, and editor all work independently without blocking each other

---

## Future Improvements

- Add multi-language support (JavaScript or C++)
- Sandboxed execution environment
- Plugin system for AI tools
- Cloud sync for projects
- Better UI/UX animations

---

## 🎥 Demo

[Watch Demo Video](https://www.youtube.com/watch?v=NtXNjKbPtEs)

---

## ⬇ Download

[Download From Google Drive](https://drive.google.com/file/d/1udezAeY13_tAkr0rACmV3ZwpY4357zBg/view?usp=sharing)

---

## 📄 License

[MIT License](./LICENSE)
