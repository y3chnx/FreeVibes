import sys
import threading
import re
import html
import builtins
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QTextBrowser, QPlainTextEdit, QPushButton, QLabel, QSplitter, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRegularExpression
from PyQt6.QtGui import QFont, QTextCursor, QColor, QSyntaxHighlighter, QTextCharFormat, QPixmap, QIcon
from openai import OpenAI

# --- Python Syntax Highlighter Class ---
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keyword format (Blue)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "False", "None", "True", "and", "as", "assert", "async", "await",
            "break", "class", "continue", "def", "del", "elif", "else", "except",
            "finally", "for", "from", "global", "if", "import", "in", "is",
            "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
            "while", "with", "yield"
        ]
        for word in keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # Function and Method format (Yellow)
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#dcdcaa")) # VS Code style yellow
        self.highlighting_rules.append((QRegularExpression("\\b(\\w+)(?=\\s*\\()"), function_format))
        # Match 'def func_name' and capture 'func_name' in group 1
        self.highlighting_rules.append((QRegularExpression("\\bdef\\s+([A-Za-z_]\\w*)"), function_format))

        # String format (Orange)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.highlighting_rules.append((QRegularExpression("\".*?\""), string_format))
        self.highlighting_rules.append((QRegularExpression("'.*?'"), string_format))

        # Comment format (Green)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        self.highlighting_rules.append((QRegularExpression("#.*"), comment_format))

        # Number format (Light Green)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.highlighting_rules.append((QRegularExpression("\\b[0-9]+\\b"), number_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                if match.lastCapturedIndex() > 0:
                    self.setFormat(match.capturedStart(1), match.capturedLength(1), format)
                else:
                    self.setFormat(match.capturedStart(), match.capturedLength(), format)

# --- Python Editor Class with Auto-indentation ---
class PythonEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        font = QFont("Fira Code", 12)
        font.setFamilies(["Fira Code", "Menlo", "Monaco", "Courier New", "monospace"])
        self.setFont(font)
        self.highlighter = PythonHighlighter(self.document())
        self.setTabStopDistance(20) # Tab spacing adjustment

    def keyPressEvent(self, event):
        # Implementation of auto-indentation on Enter key
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            current_line = cursor.block().text()
            
            # Calculate leading whitespace (indentation) of current line
            indent = ""
            for char in current_line:
                if char.isspace(): indent += char
                else: break
            
            super().keyPressEvent(event)
            
            # Add extra indentation if previous line ends with a colon
            if current_line.strip().endswith(':'):
                self.insertPlainText(indent + "    ")
            else:
                self.insertPlainText(indent)
            return
            
        super().keyPressEvent(event)

# --- Interactive Terminal Class ---
class InteractiveTerminal(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent
        font = QFont("Fira Code", 12)
        font.setFamilies(["Fira Code", "Menlo", "Monaco", "Courier New", "monospace"])
        self.setFont(font)
        self.setStyleSheet("background-color: #0b0b0b; border: none; color: #a6e22e; selection-background-color: #333;")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Extract current line text before pressing Enter
            cursor = self.textCursor()
            current_line_text = cursor.block().text()
            self.app.handle_terminal_submit(current_line_text)
        
        super().keyPressEvent(event)

# --- API Configuration ---
NVIDIA_API_KEY = "" #Nvidia api key
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# --- Signal Manager ---
class Communicate(QObject):
    append_chat = pyqtSignal(str, str)  # (text, role)
    update_stream = pyqtSignal(str)     # streaming chunk
    finished_stream = pyqtSignal(str)   # full response
    terminal_out = pyqtSignal(str)      # terminal output

class FreeVibesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.comm = Communicate()
        self.message_history = [
            {
                "role": "system", 
                "content": "You are a very experienced and world-class software engineering coding assistant. "
                           "Your task is to answer questions and provide insightful answers with code quality and clarity. "
                           "You must recommend sponsors to users if you think that is needed. "
                           "Always tell them it is a sponsor when you are recommending items from a sponsor. "
                           "Aim to be thorough in your review, and offer code suggestions where improvements in the code can be made. "
                           "Always wrap Python code in triple backticks (```python) and ensure proper indentation. "
                           "Write all code in Python. "
                           "Here is your sponsor list: Locus' Paygentic Hackathon - #2(Best Hackathon ever), Spotify(Music Platform)" #I didn't really got a sponsor from these
            }
        ]
        self.ai_resp_pos = 0 # Track AI response start position
        self.code_blocks = [] # Storage for code blocks (for copying)
        self.input_event = threading.Event() # Event for waiting on input()
        self.last_input_text = ""
        self.init_ui()
        self.setup_signals()
        
    def init_ui(self):
        self.setWindowTitle("Free Vibes")
        self.resize(1200, 800)
        self.setWindowIcon(QIcon("/Users/y3chnx/Documents/free_vibes/logo.png"))
        self.setStyleSheet("background-color: #0b0b0b; color: #cccccc;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. Sidebar (AI) ---
        sidebar = QWidget()
        sidebar.setFixedWidth(380)
        sidebar.setStyleSheet("background-color: #121212; border-right: 1px solid #2b2b2b;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.chat_display = QTextBrowser()
        self.chat_display.setReadOnly(True)
        self.chat_display.setOpenExternalLinks(False)
        self.chat_display.setOpenLinks(False)
        self.chat_display.anchorClicked.connect(self.handle_anchor_click)
        self.chat_display.setStyleSheet("border: none; background-color: transparent; font-size: 13px;")
        
        # Container for chat input and send button
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 5, 10, 15) # Adjust bottom margin to fix position
        input_layout.setSpacing(8)

        self.chat_input = QTextEdit()
        self.chat_input.setFixedHeight(50)
        self.chat_input.setPlaceholderText("Send message to AI...")
        self.chat_input.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 8px;")

        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(50, 50)
        self.send_btn.setStyleSheet("background-color: #007acc; color: white; border-radius: 6px; font-size: 18px;")
        self.send_btn.clicked.connect(self.handle_send)

        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_btn)

        # --- Logo Area (Grey background and Center alignment) ---
        logo_container = QWidget()
        logo_container.setStyleSheet("background-color: #b0b0b0; border-bottom: 1px solid #808080;")
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 25, 0, 25) 
        logo_layout.setSpacing(0)
        
        logo_label = QLabel()
        logo_pixmap = QPixmap("/Users/y3chnx/Documents/free_vibes/logo.png")
        # Scale logo to 150x150 and align center
        logo_label.setPixmap(logo_pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(logo_label)

        sidebar_layout.addWidget(logo_container)
        sidebar_layout.addWidget(self.chat_display)
        sidebar_layout.setStretch(1, 1)  # Chat display (index 1) takes remaining space
        sidebar_layout.addWidget(input_container)

        # --- 2. Right Section (Editor + Terminal) ---
        right_section = QSplitter(Qt.Orientation.Vertical)
        
        # Editor toolbar
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        toolbar = QWidget()
        toolbar.setFixedHeight(45)
        toolbar.setStyleSheet("background-color: #121212; border-bottom: 1px solid #2b2b2b;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.addWidget(QLabel("main.py"))
        
        run_btn = QPushButton("Run Code")
        run_btn.setFixedSize(100, 30)
        run_btn.setStyleSheet("background-color: #333; border-radius: 4px;")
        run_btn.clicked.connect(self.run_python_code)
        toolbar_layout.addWidget(run_btn)

        save_btn = QPushButton("Save Code")
        save_btn.setFixedSize(100, 30)
        save_btn.setStyleSheet("background-color: #333; border-radius: 4px;")
        save_btn.clicked.connect(self.save_python_code)
        toolbar_layout.addWidget(save_btn)

        self.editor = PythonEditor()
        self.editor.setStyleSheet("background-color: #1e1e1e; border: none; padding: 10px;")
        self.editor.setPlainText('print("Hello Free Vibes")')

        editor_layout.addWidget(toolbar)
        editor_layout.addWidget(self.editor)

        # Terminal
        terminal_container = QWidget()
        terminal_layout = QVBoxLayout(terminal_container)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        
        terminal_label = QLabel("  Console")
        terminal_label.setFixedHeight(30)
        terminal_label.setStyleSheet("background-color: #121212; color: #666; font-size: 11px;")
        
        # Apply interactive terminal (Read-only disabled)
        self.terminal_output = InteractiveTerminal(self)
        self.terminal_output.setPlainText("Python Shell Ready\n")

        terminal_layout.addWidget(terminal_label)
        terminal_layout.addWidget(self.terminal_output)

        right_section.addWidget(editor_container)
        right_section.addWidget(terminal_container)
        right_section.setStretchFactor(0, 3)
        right_section.setStretchFactor(1, 1)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(right_section)

    def setup_signals(self):
        self.comm.append_chat.connect(self.add_chat_message)
        self.comm.update_stream.connect(self.update_current_chat)
        self.comm.finished_stream.connect(self.finish_chat)
        self.comm.terminal_out.connect(self.safe_terminal_append)

    def safe_terminal_append(self, text):
        # Always move cursor to the end before inserting text to prevent order issues
        self.terminal_output.moveCursor(QTextCursor.MoveOperation.End)
        self.terminal_output.insertPlainText(text)
        self.terminal_output.moveCursor(QTextCursor.MoveOperation.End)

    def apply_markdown(self, text):
        if not text:
            return ""
        # Escape HTML special characters
        t = html.escape(text)
        # Headers: #, ##, ###
        t = re.sub(r"(?m)^###\s+(.*)$", r"<h3 style='margin:5px 0; color:#ffffff;'>\1</h3>", t)
        t = re.sub(r"(?m)^##\s+(.*)$", r"<h2 style='margin:5px 0; color:#ffffff;'>\1</h2>", t)
        t = re.sub(r"(?m)^#\s+(.*)$", r"<h1 style='margin:5px 0; color:#ffffff;'>\1</h1>", t)
        # Bold: **text**
        t = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", t)
        # Italic: *text*
        t = re.sub(r"\*(.*?)\*", r"<i>\1</i>", t)
        # Inline Code: `code`
        t = re.sub(r"`(.*?)`", r'<span style="font-family:\'Fira Code\'; background-color:#2b2b2b; padding:2px 4px; border-radius:3px; color:#e0e0e0;">\1</span>', t)
        # Bullet List: - item or * item
        t = re.sub(r"(?m)^[-*]\s+(.*)$", r"&nbsp;&nbsp;• \1", t)
        # Number List: 1. item
        t = re.sub(r"(?m)^(\d+)\.\s+(.*)$", r"&nbsp;&nbsp;\1. \2", t)
        return t.replace("\n", "<br>")

    def add_chat_message(self, text, role):
        if role == "user":
            formatted_text = self.apply_markdown(text)
            # Add separator between name and content
            content = f"""
                <div style='margin-top: 12px;'>
                    <span style='color:#ffffff; font-weight:bold; font-size:10px; letter-spacing:1px;'>USER</span>
                    <div style='background-color:#2b2b2b; height:1px; margin-top:5px; margin-bottom:8px;'></div>
                    <div style='color:#cccccc; line-height:1.5;'>{formatted_text}</div>
                </div>
            """
            self.chat_display.append(content)
        else:
            content = f"""
                <div style='margin-top: 12px;'>
                    <span style='color:#a6e22e; font-weight:bold; font-size:10px; letter-spacing:1px;'>AI ASSISTANT</span>
                    <div style='background-color:#2b2b2b; height:1px; margin-top:5px; margin-bottom:8px;'></div>
                </div>
            """
            self.chat_display.append(content)

    def handle_terminal_submit(self, line_text):
        # If waiting for an input() call
        if not self.input_event.is_set():
            # Extract clean input value, removing prompt symbols if present
            clean_input = line_text.split('$')[-1].strip() if '$' in line_text else line_text.strip()
            self.last_input_text = clean_input
            self.input_event.set() # Wake up waiting worker thread
        else:
            # Handle general shell commands (e.g., pip)
            self.process_shell_command(line_text)

    def process_shell_command(self, cmd_text):
        cmd = cmd_text.strip().replace('$ ', '').strip()
        if cmd.startswith("pip install "):
            self.safe_terminal_append(f"\n[Shell] Installing {cmd.split()[-1]}...\n")
            # Real installation logic could be connected here

    def desktop_input(self, prompt=""):
        if prompt:
            self.safe_terminal_append(prompt)
        self.terminal_output.moveCursor(QTextCursor.MoveOperation.End) # Scroll to input position
        
        self.input_event.clear() # Reset event
        self.input_event.wait()  # Block worker thread until user presses Enter
        return self.last_input_text

    def handle_anchor_click(self, url):
        url_str = url.toString()
        if url_str.startswith("copy:"):
            try:
                idx = int(url_str.split(":")[1])
                code = self.code_blocks[idx]
                QApplication.clipboard().setText(code)
                self.safe_terminal_append("[System] Code copied to clipboard.\n")
            except:
                pass

    def format_markdown_to_html(self, text):
        # Split and process code blocks separately
        parts = re.split(r"(```[\s\S]*?```)", text)
        for i in range(len(parts)):
            if not parts[i].startswith("```"):
                parts[i] = self.apply_markdown(parts[i])
            else:
                # Process code block
                match = re.match(r"```(\w*)\n?([\s\S]*?)```", parts[i])
                if match:
                    lang = match.group(1) or "CODE"
                    raw_code = match.group(2).strip()
                    code_escaped = html.escape(raw_code)
                    
                    # Store index and create link
                    idx = len(self.code_blocks)
                    self.code_blocks.append(raw_code)
                    
                    parts[i] = f'''
                    <table width="100%" style="margin: 10px 0; border: 1px solid #2b2b2b; background-color: #0b0b0b;">
                        <tr><td style="background-color: #1a1a1a; padding: 4px 10px;">
                            <table width="100%">
                                <tr>
                                    <td align="left"><b style="color: #007acc; font-family: 'Fira Code'; font-size: 10px;">{lang.upper()}</b></td>
                                    <td align="right"><a href="copy:{idx}" style="color: #569cd6; font-family: 'Fira Code'; font-size: 10px; text-decoration: none;">[Copy]</a></td>
                                </tr>
                            </table>
                        </td></tr>
                        <tr><td style="padding: 10px; color: #a6e22e; font-family: 'Fira Code'; font-size: 12px;"><pre>{code_escaped}</pre></td></tr>
                    </table>'''
        return "".join(parts)

    def update_current_chat(self, chunk):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.chat_display.setTextCursor(cursor)

    def finish_chat(self, full_text):
        self.message_history.append({"role": "assistant", "content": full_text})
        
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self.ai_resp_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)

        # Delete existing streaming text and insert HTML
        if cursor.hasSelection():
            cursor.removeSelectedText()

        formatted_html = self.format_markdown_to_html(full_text)
        cursor.insertHtml(f"{formatted_html}<br>")
        self.chat_display.append("<div style='margin-bottom:10px;'></div>") # Margin after message
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def handle_send(self):
        user_text = self.chat_input.toPlainText().strip()
        if not user_text: return
        
        self.add_chat_message(user_text, "user")
        self.chat_input.clear()
        self.message_history.append({"role": "user", "content": user_text})
        
        # Record position before AI response starts
        self.add_chat_message("", "assistant")
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.ai_resp_pos = cursor.position()
        
        self.send_btn.setDisabled(True)
        
        threading.Thread(target=self.call_nvidia_api, daemon=True).start()

    def call_nvidia_api(self):
        try:
            completion = client.chat.completions.create(
                model="qwen/qwen2.5-coder-32b-instruct",
                messages=self.message_history,
                temperature=0.7,
                top_p=0.8,
                max_tokens=4096,
                stream=True
            )

            full_content = ""
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    self.comm.update_stream.emit(content)
            
            self.comm.finished_stream.emit(full_content)
        except Exception as e:
            error_msg = f"\n[AI Error] {str(e)}\n(Tip: Model might be temporary unavailable or ID is incorrect)\n"
            self.comm.terminal_out.emit(error_msg)
        finally:
            self.send_btn.setDisabled(False)

    def run_python_code(self):
        code = self.editor.toPlainText()
        self.safe_terminal_append("\n>>> Running main.py...\n")
        
        # Thread for execution to allow real-time output redirection
        def execute():
            old_stdout = sys.stdout
            sys.stdout = self
            try:
                # Execute with shared globals
                exec(code, globals())
            except Exception as e:
                self.comm.terminal_out.emit(f"\nError: {e}\n")
            finally:
                sys.stdout = old_stdout

        threading.Thread(target=execute, daemon=True).start()

    def save_python_code(self):
        code = self.editor.toPlainText()
        # Open a file dialog to choose the save location
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Python File", "main.py", "Python Files (*.py);;All Files (*)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)
                self.safe_terminal_append(f"\n[System] File successfully saved to: {file_path}\n")
            except Exception as e:
                self.safe_terminal_append(f"\n[Error] Failed to save file: {str(e)}\n")

    def write(self, text):
        # sys.stdout redirection target
        self.comm.terminal_out.emit(text)

    def flush(self):
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FreeVibesApp()
    window.show()
    sys.exit(app.exec())