"""
ZipArchive Navigator — A premium desktop ZIP archive browser & extractor.
Built with Python + PyQt6. Dark themed, feature-rich, standalone app.
Run: python app.py
"""

import sys
import os
import zipfile
import io
import datetime
import struct
from pathlib import Path, PurePosixPath

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QSplitter, QToolBar, QStatusBar, QMenuBar, QMenu, QLabel,
    QLineEdit, QFileDialog, QMessageBox, QHeaderView, QTextEdit,
    QFrame, QScrollArea, QAbstractItemView, QStyle, QPushButton,
    QStackedWidget, QSizePolicy, QProgressBar
)
from PyQt6.QtCore import (
    Qt, QSize, QMimeData, QUrl, QTimer, QPropertyAnimation,
    QEasingCurve, pyqtSignal, QThread
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QFont, QAction, QColor, QPalette,
    QDragEnterEvent, QDropEvent, QPainter, QLinearGradient,
    QFontDatabase, QPen, QBrush, QKeySequence
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_NAME = "ZipArchive Navigator"
APP_VERSION = "1.0.0"

FILE_TYPE_ICONS = {
    "folder":  "📁",
    "image":   "🖼️",
    "text":    "📄",
    "code":    "💻",
    "data":    "📊",
    "archive": "📦",
    "audio":   "🎵",
    "video":   "🎬",
    "pdf":     "📕",
    "binary":  "⚙️",
    "unknown": "📎",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tiff", ".tif", ".svg"}
TEXT_EXTENSIONS = {".txt", ".md", ".log", ".cfg", ".ini", ".yml", ".yaml", ".toml", ".env", ".gitignore", ".editorconfig"}
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".css", ".scss", ".less",
                   ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php",
                   ".swift", ".kt", ".scala", ".sh", ".bash", ".bat", ".ps1", ".sql", ".r",
                   ".lua", ".dart", ".vue", ".svelte", ".astro"}
DATA_EXTENSIONS = {".json", ".xml", ".csv", ".tsv", ".xls", ".xlsx"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".wma", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
PDF_EXTENSIONS = {".pdf"}


def get_file_category(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in CODE_EXTENSIONS:
        return "code"
    if ext in DATA_EXTENSIONS:
        return "data"
    if ext in ARCHIVE_EXTENSIONS:
        return "archive"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    return "unknown"


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def is_text_previewable(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in TEXT_EXTENSIONS or ext in CODE_EXTENSIONS or ext in DATA_EXTENSIONS


# ---------------------------------------------------------------------------
# Dark Theme QSS
# ---------------------------------------------------------------------------
DARK_THEME_QSS = """
/* ── Global ── */
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0d1117;
}

/* ── Menu Bar ── */
QMenuBar {
    background-color: #161b22;
    color: #e6edf3;
    border-bottom: 1px solid #30363d;
    padding: 2px 0;
    font-size: 13px;
}

QMenuBar::item {
    padding: 6px 14px;
    border-radius: 6px;
    margin: 2px 2px;
}

QMenuBar::item:selected {
    background-color: #1f6feb33;
    color: #58a6ff;
}

QMenu {
    background-color: #1c2128;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 6px 0;
}

QMenu::item {
    padding: 8px 32px 8px 16px;
    margin: 1px 6px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #1f6feb44;
    color: #58a6ff;
}

QMenu::separator {
    height: 1px;
    background-color: #30363d;
    margin: 4px 12px;
}

/* ── Toolbar ── */
QToolBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 4px 8px;
    spacing: 4px;
}

QToolBar QToolButton {
    background-color: transparent;
    color: #e6edf3;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
}

QToolBar QToolButton:hover {
    background-color: #1f6feb33;
    border: 1px solid #1f6feb55;
    color: #58a6ff;
}

QToolBar QToolButton:pressed {
    background-color: #1f6feb55;
}

/* ── Search Bar ── */
QLineEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 7px 12px;
    color: #e6edf3;
    font-size: 13px;
    selection-background-color: #1f6feb;
}

QLineEdit:focus {
    border: 1px solid #58a6ff;
    background-color: #161b22;
}

QLineEdit::placeholder {
    color: #484f58;
}

/* ── Tree Widget (Sidebar) ── */
QTreeWidget {
    background-color: #0d1117;
    border: none;
    outline: none;
    font-size: 13px;
    padding: 4px;
}

QTreeWidget::item {
    padding: 5px 8px;
    border-radius: 6px;
    margin: 1px 4px;
}

QTreeWidget::item:hover {
    background-color: #161b22;
}

QTreeWidget::item:selected {
    background-color: #1f6feb33;
    color: #58a6ff;
}

QTreeWidget::branch {
    background-color: transparent;
}

QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {
    image: none;
    border-image: none;
}

QTreeWidget::branch:open:has-children:!has-siblings,
QTreeWidget::branch:open:has-children:has-siblings {
    image: none;
    border-image: none;
}

/* ── Table Widget (File List) ── */
QTableWidget {
    background-color: #0d1117;
    border: none;
    gridline-color: #21262d;
    outline: none;
    font-size: 13px;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #161b22;
}

QTableWidget::item:hover {
    background-color: #161b22;
}

QTableWidget::item:selected {
    background-color: #1f6feb33;
    color: #58a6ff;
}

QHeaderView {
    background-color: #161b22;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    border: none;
    border-bottom: 2px solid #30363d;
    border-right: 1px solid #21262d;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

QHeaderView::section:hover {
    color: #e6edf3;
    background-color: #1c2128;
}

/* ── Scrollbars ── */
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #484f58;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #30363d;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

/* ── Status Bar ── */
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
    font-size: 12px;
    padding: 2px 12px;
}

QStatusBar::item {
    border: none;
}

/* ── Text Preview ── */
QTextEdit {
    background-color: #0d1117;
    color: #e6edf3;
    border: none;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
    padding: 12px;
    selection-background-color: #1f6feb;
}

/* ── Labels ── */
QLabel {
    color: #e6edf3;
}

/* ── Frames ── */
QFrame {
    border: none;
}

/* ── Progress Bar ── */
QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    font-size: 0px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1f6feb, stop:1 #58a6ff);
    border-radius: 4px;
}

/* ── Push Button ── */
QPushButton {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #58a6ff;
    color: #58a6ff;
}

QPushButton:pressed {
    background-color: #1f6feb33;
}

QPushButton#accentBtn {
    background-color: #1f6feb;
    border: none;
    color: white;
    font-weight: 600;
}

QPushButton#accentBtn:hover {
    background-color: #388bfd;
}
"""


# ---------------------------------------------------------------------------
# DropZoneWidget — The initial landing view
# ---------------------------------------------------------------------------
class DropZoneWidget(QFrame):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(500, 350)
        self._hovering = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Icon
        icon_label = QLabel("📦")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 64px; background: transparent;")
        layout.addWidget(icon_label)

        # Title
        title = QLabel("ZipArchive Navigator")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #e6edf3;
            background: transparent;
            letter-spacing: -0.5px;
        """)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Drop a ZIP file here to explore its contents")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 15px; color: #8b949e; background: transparent;")
        layout.addWidget(subtitle)

        # Browse button
        browse_btn = QPushButton("  Browse Files  ")
        browse_btn.setObjectName("accentBtn")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse)
        browse_btn.setStyleSheet(browse_btn.styleSheet() + """
            QPushButton#accentBtn {
                padding: 12px 32px;
                font-size: 14px;
                border-radius: 10px;
            }
        """)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Supported formats
        formats = QLabel("Supports .zip files")
        formats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formats.setStyleSheet("font-size: 12px; color: #484f58; background: transparent; margin-top: 8px;")
        layout.addWidget(formats)

        self._update_border()

    def _update_border(self):
        if self._hovering:
            self.setStyleSheet("""
                DropZoneWidget {
                    background-color: #0d111700;
                    border: 2px dashed #58a6ff;
                    border-radius: 16px;
                    margin: 40px;
                }
            """)
        else:
            self.setStyleSheet("""
                DropZoneWidget {
                    background-color: #0d111700;
                    border: 2px dashed #30363d;
                    border-radius: 16px;
                    margin: 40px;
                }
            """)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open ZIP Archive", "",
            "ZIP Archives (*.zip);;All Files (*)"
        )
        if path:
            self.file_dropped.emit(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(".zip"):
                event.acceptProposedAction()
                self._hovering = True
                self._update_border()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._hovering = False
        self._update_border()

    def dropEvent(self, event: QDropEvent):
        self._hovering = False
        self._update_border()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(".zip"):
                self.file_dropped.emit(path)


# ---------------------------------------------------------------------------
# BreadcrumbBar
# ---------------------------------------------------------------------------
class BreadcrumbBar(QFrame):
    path_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 4, 12, 4)
        self._layout.setSpacing(2)
        self.setFixedHeight(36)
        self.setStyleSheet("""
            BreadcrumbBar {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
            }
        """)
        self.set_path("")

    def set_path(self, path: str):
        # Clear existing
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Root
        root_btn = QPushButton("📦 Archive")
        root_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        root_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #58a6ff;
                font-weight: 600;
                font-size: 12px;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1f6feb22; }
        """)
        root_btn.clicked.connect(lambda: self.path_clicked.emit(""))
        self._layout.addWidget(root_btn)

        if path:
            parts = path.strip("/").split("/")
            accumulated = ""
            for i, part in enumerate(parts):
                # Separator
                sep = QLabel("›")
                sep.setStyleSheet("color: #484f58; font-size: 14px; padding: 0 2px; background: transparent;")
                self._layout.addWidget(sep)

                accumulated = f"{accumulated}/{part}" if accumulated else part
                is_last = (i == len(parts) - 1)
                btn = QPushButton(f"📁 {part}" if not is_last else f"📁 {part}")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_path = accumulated

                if is_last:
                    btn.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            border: none;
                            color: #e6edf3;
                            font-weight: 600;
                            font-size: 12px;
                            padding: 4px 8px;
                            border-radius: 4px;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            border: none;
                            color: #58a6ff;
                            font-weight: 500;
                            font-size: 12px;
                            padding: 4px 8px;
                            border-radius: 4px;
                        }
                        QPushButton:hover { background-color: #1f6feb22; }
                    """)
                    btn.clicked.connect(lambda checked, p=btn_path: self.path_clicked.emit(p))

                self._layout.addWidget(btn)

        self._layout.addStretch()


# ---------------------------------------------------------------------------
# Preview Panel
# ---------------------------------------------------------------------------
class PreviewPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Header
        self._header = QFrame()
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(14, 8, 14, 8)
        self._header.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
            }
        """)
        self._header.setFixedHeight(40)

        self._title_label = QLabel("Preview")
        self._title_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #8b949e; background: transparent;")
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8b949e;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #da363333;
                color: #f85149;
            }
        """)
        self._close_btn.clicked.connect(self._clear_preview)
        header_layout.addWidget(self._close_btn)
        self._layout.addWidget(self._header)

        # Stacked content
        self._stack = QStackedWidget()
        self._layout.addWidget(self._stack)

        # Empty state
        self._empty = QLabel("Select a file to preview")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #484f58; font-size: 14px;")
        self._stack.addWidget(self._empty)

        # Text preview
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._stack.addWidget(self._text_edit)

        # Image preview
        self._image_scroll = QScrollArea()
        self._image_scroll.setWidgetResizable(True)
        self._image_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_scroll.setStyleSheet("QScrollArea { background-color: #0d1117; border: none; }")
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background: transparent; padding: 16px;")
        self._image_scroll.setWidget(self._image_label)
        self._stack.addWidget(self._image_scroll)

        # Hex preview
        self._hex_edit = QTextEdit()
        self._hex_edit.setReadOnly(True)
        self._hex_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._hex_edit.setStyleSheet(self._hex_edit.styleSheet() + """
            QTextEdit {
                font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
                font-size: 12px;
                color: #7ee787;
            }
        """)
        self._stack.addWidget(self._hex_edit)

        # Info panel (for non-previewable files)
        self._info_label = QLabel()
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setWordWrap(True)
        self._info_label.setStyleSheet("color: #8b949e; font-size: 14px; padding: 24px;")
        self._stack.addWidget(self._info_label)

        self._stack.setCurrentWidget(self._empty)

    def _clear_preview(self):
        self._stack.setCurrentWidget(self._empty)
        self._title_label.setText("Preview")

    def show_text(self, filename: str, content: str):
        self._title_label.setText(f"📄 {filename}")
        self._text_edit.setPlainText(content)
        self._stack.setCurrentWidget(self._text_edit)

    def show_image(self, filename: str, data: bytes):
        self._title_label.setText(f"🖼️ {filename}")
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if not pixmap.isNull():
            # Scale to fit while maintaining aspect ratio
            max_w = max(self._image_scroll.width() - 40, 200)
            max_h = max(self._image_scroll.height() - 40, 200)
            scaled = pixmap.scaled(
                max_w, max_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._image_label.setPixmap(scaled)
        else:
            self._image_label.setText("Unable to load image")
        self._stack.setCurrentWidget(self._image_scroll)

    def show_hex(self, filename: str, data: bytes):
        self._title_label.setText(f"⚙️ {filename} (Hex View)")
        max_bytes = 4096  # Show first 4KB
        truncated = len(data) > max_bytes
        display_data = data[:max_bytes]

        lines = []
        for offset in range(0, len(display_data), 16):
            chunk = display_data[offset:offset + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{offset:08X}  {hex_part:<48s}  |{ascii_part}|")

        if truncated:
            lines.append(f"\n... truncated ({format_size(len(data))} total)")

        self._hex_edit.setPlainText("\n".join(lines))
        self._stack.setCurrentWidget(self._hex_edit)

    def show_info(self, filename: str, info_text: str):
        self._title_label.setText(f"📎 {filename}")
        self._info_label.setText(info_text)
        self._stack.setCurrentWidget(self._info_label)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class ZipNavigatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1100, 700)
        self.resize(1400, 850)
        self.setAcceptDrops(True)

        self._zip_file: zipfile.ZipFile | None = None
        self._zip_path: str = ""
        self._current_folder: str = ""
        self._all_entries: list[zipfile.ZipInfo] = []
        self._folder_structure: dict = {}
        self._recent_files: list[str] = []

        self._setup_menubar()
        self._setup_toolbar()
        self._setup_ui()
        self._setup_statusbar()
        self._setup_shortcuts()

    # ── Menu Bar ──
    def _setup_menubar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("📂  Open Archive...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        extract_all_action = QAction("📥  Extract All...", self)
        extract_all_action.setShortcut(QKeySequence("Ctrl+E"))
        extract_all_action.triggered.connect(self._extract_all)
        file_menu.addAction(extract_all_action)

        file_menu.addSeparator()

        close_action = QAction("🚫  Close Archive", self)
        close_action.setShortcut(QKeySequence("Ctrl+W"))
        close_action.triggered.connect(self._close_archive)
        file_menu.addAction(close_action)

        file_menu.addSeparator()

        quit_action = QAction("  Exit", self)
        quit_action.setShortcut(QKeySequence("Alt+F4"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        search_action = QAction("🔍  Focus Search", self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self._focus_search)
        view_menu.addAction(search_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("ℹ️  About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ── Toolbar ──
    def _setup_toolbar(self):
        self._toolbar = QToolBar("Main Toolbar")
        self._toolbar.setMovable(False)
        self._toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(self._toolbar)

        # Open
        open_btn = QAction("📂 Open", self)
        open_btn.setToolTip("Open a ZIP archive (Ctrl+O)")
        open_btn.triggered.connect(self._open_file_dialog)
        self._toolbar.addAction(open_btn)

        # Extract All
        self._extract_btn = QAction("📥 Extract All", self)
        self._extract_btn.setToolTip("Extract all files (Ctrl+E)")
        self._extract_btn.setEnabled(False)
        self._extract_btn.triggered.connect(self._extract_all)
        self._toolbar.addAction(self._extract_btn)

        # Close
        self._close_btn = QAction("🚫 Close", self)
        self._close_btn.setToolTip("Close current archive (Ctrl+W)")
        self._close_btn.setEnabled(False)
        self._close_btn.triggered.connect(self._close_archive)
        self._toolbar.addAction(self._close_btn)

        self._toolbar.addSeparator()

        # Search
        search_label = QLabel("  🔍 ")
        search_label.setStyleSheet("background: transparent;")
        self._toolbar.addWidget(search_label)

        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Search files...")
        self._search_bar.setMaximumWidth(300)
        self._search_bar.setMinimumWidth(200)
        self._search_bar.textChanged.connect(self._on_search)
        self._search_bar.setClearButtonEnabled(True)
        self._toolbar.addWidget(self._search_bar)

    # ── Main UI ──
    def _setup_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Stacked: drop zone vs browser
        self._main_stack = QStackedWidget()
        main_layout.addWidget(self._main_stack)

        # ── Drop Zone ──
        self._drop_zone = DropZoneWidget()
        self._drop_zone.file_dropped.connect(self._load_zip)
        self._main_stack.addWidget(self._drop_zone)

        # ── Browser View ──
        browser_widget = QWidget()
        browser_layout = QVBoxLayout(browser_widget)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_layout.setSpacing(0)

        # Breadcrumb
        self._breadcrumb = BreadcrumbBar()
        self._breadcrumb.path_clicked.connect(self._navigate_to)
        browser_layout.addWidget(self._breadcrumb)

        # Splitter: tree | file list | preview
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Tree
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        tree_header = QFrame()
        tree_header.setFixedHeight(36)
        tree_header.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
                border-right: 1px solid #30363d;
            }
        """)
        th_layout = QHBoxLayout(tree_header)
        th_layout.setContentsMargins(12, 0, 12, 0)
        th_label = QLabel("📁  EXPLORER")
        th_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #8b949e; letter-spacing: 1px; background: transparent;")
        th_layout.addWidget(th_label)
        tree_layout.addWidget(tree_header)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.itemClicked.connect(self._on_tree_click)
        tree_layout.addWidget(self._tree)

        self._splitter.addWidget(tree_container)

        # Center: File list
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        list_header = QFrame()
        list_header.setFixedHeight(36)
        list_header.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
            }
        """)
        lh_layout = QHBoxLayout(list_header)
        lh_layout.setContentsMargins(12, 0, 12, 0)
        self._list_header_label = QLabel("📋  FILES")
        self._list_header_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #8b949e; letter-spacing: 1px; background: transparent;")
        lh_layout.addWidget(self._list_header_label)
        lh_layout.addStretch()
        self._file_count_label = QLabel("")
        self._file_count_label.setStyleSheet("font-size: 11px; color: #484f58; background: transparent;")
        lh_layout.addWidget(self._file_count_label)
        list_layout.addWidget(list_header)

        self._file_table = QTableWidget()
        self._file_table.setColumnCount(4)
        self._file_table.setHorizontalHeaderLabels(["Name", "Size", "Type", "Modified"])
        self._file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.verticalHeader().setVisible(False)
        self._file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._file_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._file_table.setShowGrid(False)
        self._file_table.verticalHeader().setDefaultSectionSize(36)
        self._file_table.setSortingEnabled(True)
        self._file_table.cellDoubleClicked.connect(self._on_file_double_click)
        self._file_table.itemSelectionChanged.connect(self._on_file_selected)
        self._file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._file_table.customContextMenuRequested.connect(self._show_context_menu)
        list_layout.addWidget(self._file_table)

        self._splitter.addWidget(list_container)

        # Right: Preview
        self._preview = PreviewPanel()
        self._splitter.addWidget(self._preview)

        self._splitter.setSizes([240, 500, 400])
        browser_layout.addWidget(self._splitter)

        self._main_stack.addWidget(browser_widget)
        self._main_stack.setCurrentWidget(self._drop_zone)

    # ── Status Bar ──
    def _setup_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        self._status_label = QLabel("Ready — Drop a ZIP file to get started")
        self._statusbar.addWidget(self._status_label, 1)

        self._size_label = QLabel("")
        self._statusbar.addPermanentWidget(self._size_label)

    # ── Shortcuts ──
    def _setup_shortcuts(self):
        pass  # Shortcuts are attached to menu actions

    # ── File Operations ──
    def _open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open ZIP Archive", "",
            "ZIP Archives (*.zip);;All Files (*)"
        )
        if path:
            self._load_zip(path)

    def _load_zip(self, path: str):
        try:
            if self._zip_file:
                self._zip_file.close()

            self._zip_file = zipfile.ZipFile(path, "r")
            self._zip_path = path
            self._all_entries = self._zip_file.infolist()
            self._build_folder_structure()
            self._populate_tree()
            self._navigate_to("")
            self._main_stack.setCurrentIndex(1)  # Switch to browser
            self._extract_btn.setEnabled(True)
            self._close_btn.setEnabled(True)
            self.setWindowTitle(f"{APP_NAME} — {os.path.basename(path)}")

            # Stats
            total_files = sum(1 for e in self._all_entries if not e.is_dir())
            total_size = sum(e.file_size for e in self._all_entries)
            self._status_label.setText(
                f"📦 {os.path.basename(path)}  •  {total_files} files  •  {format_size(total_size)} uncompressed"
            )
            compressed = os.path.getsize(path)
            self._size_label.setText(f"Archive: {format_size(compressed)}")

        except zipfile.BadZipFile:
            QMessageBox.critical(self, "Error", "The selected file is not a valid ZIP archive.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open archive:\n{str(e)}")

    def _close_archive(self):
        if self._zip_file:
            self._zip_file.close()
            self._zip_file = None

        self._zip_path = ""
        self._all_entries = []
        self._folder_structure = {}
        self._current_folder = ""
        self._tree.clear()
        self._file_table.setRowCount(0)
        self._extract_btn.setEnabled(False)
        self._close_btn.setEnabled(False)
        self._main_stack.setCurrentWidget(self._drop_zone)
        self.setWindowTitle(APP_NAME)
        self._status_label.setText("Ready — Drop a ZIP file to get started")
        self._size_label.setText("")

    def _build_folder_structure(self):
        """Build a nested dict representing the folder structure."""
        self._folder_structure = {}
        folders_seen = set()

        for info in self._all_entries:
            path = info.filename
            if path.endswith("/"):
                # Directory entry
                folders_seen.add(path.rstrip("/"))
            else:
                # File entry — ensure parent dirs exist
                parent = str(PurePosixPath(path).parent)
                if parent == ".":
                    parent = ""
                while parent:
                    folders_seen.add(parent)
                    parent = str(PurePosixPath(parent).parent)
                    if parent == ".":
                        parent = ""

        # Build tree dict
        root = {}
        for folder in sorted(folders_seen):
            parts = folder.split("/")
            node = root
            for part in parts:
                if part not in node:
                    node[part] = {}
                node = node[part]
        self._folder_structure = root

    def _populate_tree(self):
        self._tree.clear()

        # Root item
        archive_name = os.path.basename(self._zip_path)
        root_item = QTreeWidgetItem(self._tree, [f"📦 {archive_name}"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, "")
        root_item.setExpanded(True)

        font = root_item.font(0)
        font.setBold(True)
        root_item.setFont(0, font)

        self._add_tree_children(root_item, self._folder_structure, "")
        self._tree.expandAll()

    def _add_tree_children(self, parent_item: QTreeWidgetItem, structure: dict, path_prefix: str):
        for folder_name in sorted(structure.keys()):
            full_path = f"{path_prefix}/{folder_name}" if path_prefix else folder_name
            item = QTreeWidgetItem(parent_item, [f"📁 {folder_name}"])
            item.setData(0, Qt.ItemDataRole.UserRole, full_path)
            self._add_tree_children(item, structure[folder_name], full_path)

    # ── Navigation ──
    def _navigate_to(self, folder_path: str):
        self._current_folder = folder_path
        self._breadcrumb.set_path(folder_path)
        self._populate_file_list(folder_path)

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path is not None:
            self._navigate_to(path)

    def _populate_file_list(self, folder_path: str, search_query: str = ""):
        self._file_table.setSortingEnabled(False)
        self._file_table.setRowCount(0)

        if not self._zip_file:
            return

        # Gather items at this folder level
        items = []  # (is_dir, name, full_path, size, date_time)

        # Folders at this level
        if folder_path:
            structure = self._folder_structure
            for part in folder_path.split("/"):
                structure = structure.get(part, {})
        else:
            structure = self._folder_structure

        for sub_folder in sorted(structure.keys()):
            full = f"{folder_path}/{sub_folder}" if folder_path else sub_folder
            if search_query and search_query.lower() not in sub_folder.lower():
                continue
            items.append((True, sub_folder, full, 0, None))

        # Files at this level
        prefix = f"{folder_path}/" if folder_path else ""
        for info in self._all_entries:
            if info.is_dir():
                continue
            name = info.filename
            if prefix:
                if not name.startswith(prefix):
                    continue
                remainder = name[len(prefix):]
            else:
                remainder = name

            # Only immediate children (no further /)
            if "/" in remainder:
                continue

            if search_query and search_query.lower() not in remainder.lower():
                continue

            dt = None
            try:
                dt = datetime.datetime(*info.date_time)
            except Exception:
                pass

            items.append((False, remainder, name, info.file_size, dt))

        self._file_table.setRowCount(len(items))
        self._file_count_label.setText(f"{len(items)} items")

        for row, (is_dir, name, full_path, size, dt) in enumerate(items):
            if is_dir:
                icon_str = "📁"
                type_str = "Folder"
                size_str = ""
            else:
                cat = get_file_category(name)
                icon_str = FILE_TYPE_ICONS.get(cat, "📎")
                ext = Path(name).suffix.lower()
                type_str = ext.upper().lstrip(".") if ext else "File"
                size_str = format_size(size)

            # Name
            name_item = QTableWidgetItem(f"{icon_str}  {name}")
            name_item.setData(Qt.ItemDataRole.UserRole, full_path)
            name_item.setData(Qt.ItemDataRole.UserRole + 1, is_dir)
            if is_dir:
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)
            self._file_table.setItem(row, 0, name_item)

            # Size
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Store numeric size for proper sorting
            size_item.setData(Qt.ItemDataRole.UserRole, size)
            self._file_table.setItem(row, 1, size_item)

            # Type
            type_item = QTableWidgetItem(type_str)
            self._file_table.setItem(row, 2, type_item)

            # Modified
            date_str = dt.strftime("%Y-%m-%d %H:%M") if dt else ""
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._file_table.setItem(row, 3, date_item)

        self._file_table.setSortingEnabled(True)

    def _on_file_double_click(self, row: int, col: int):
        item = self._file_table.item(row, 0)
        if not item:
            return

        full_path = item.data(Qt.ItemDataRole.UserRole)
        is_dir = item.data(Qt.ItemDataRole.UserRole + 1)

        if is_dir:
            self._navigate_to(full_path)
            # Select in tree
            self._select_tree_item(full_path)
        else:
            self._preview_file(full_path)

    def _on_file_selected(self):
        rows = self._file_table.selectionModel().selectedRows()
        if not rows:
            return

        row = rows[0].row()
        item = self._file_table.item(row, 0)
        if not item:
            return

        is_dir = item.data(Qt.ItemDataRole.UserRole + 1)
        if not is_dir:
            full_path = item.data(Qt.ItemDataRole.UserRole)
            self._preview_file(full_path)

    def _select_tree_item(self, path: str):
        """Select & expand the tree item for a given path."""
        root = self._tree.topLevelItem(0)
        if not root:
            return

        if path == "":
            self._tree.setCurrentItem(root)
            return

        parts = path.split("/")
        current = root
        for part in parts:
            found = False
            for i in range(current.childCount()):
                child = current.child(i)
                child_path = child.data(0, Qt.ItemDataRole.UserRole)
                if child_path and child_path.split("/")[-1] == part:
                    current = child
                    current.setExpanded(True)
                    found = True
                    break
            if not found:
                break

        self._tree.setCurrentItem(current)

    # ── Preview ──
    def _preview_file(self, zip_path: str):
        if not self._zip_file:
            return

        filename = PurePosixPath(zip_path).name
        ext = Path(filename).suffix.lower()

        try:
            data = self._zip_file.read(zip_path)
        except Exception as e:
            self._preview.show_info(filename, f"Error reading file:\n{str(e)}")
            return

        # Image
        if ext in IMAGE_EXTENSIONS:
            self._preview.show_image(filename, data)
            return

        # Text / Code / Data
        if is_text_previewable(filename):
            try:
                text = data.decode("utf-8", errors="replace")
                # Limit to ~500KB for performance
                if len(text) > 500_000:
                    text = text[:500_000] + "\n\n... [truncated]"
                self._preview.show_text(filename, text)
            except Exception:
                self._preview.show_hex(filename, data)
            return

        # Try to detect text
        if len(data) < 100_000:
            try:
                text = data.decode("utf-8")
                # If decode succeeds and it looks like text
                if all(c == '\n' or c == '\r' or c == '\t' or (32 <= ord(c) < 127) or ord(c) > 127 for c in text[:1000]):
                    self._preview.show_text(filename, text)
                    return
            except (UnicodeDecodeError, ValueError):
                pass

        # Binary / hex view
        cat = get_file_category(filename)
        icon = FILE_TYPE_ICONS.get(cat, "📎")
        info = f"{icon}\n\n{filename}\n\n"
        info += f"Size: {format_size(len(data))}\n"
        info += f"Type: {ext.upper().lstrip('.') if ext else 'Unknown'}\n\n"

        if len(data) > 0:
            self._preview.show_hex(filename, data)
        else:
            info += "Empty file"
            self._preview.show_info(filename, info)

    # ── Search ──
    def _on_search(self, text: str):
        if text.strip():
            # Search across all files
            self._search_all_files(text.strip())
        else:
            self._populate_file_list(self._current_folder)

    def _search_all_files(self, query: str):
        """Search for files matching query across the entire archive."""
        if not self._zip_file:
            return

        self._file_table.setSortingEnabled(False)
        self._file_table.setRowCount(0)
        query_lower = query.lower()

        matches = []
        for info in self._all_entries:
            if info.is_dir():
                continue
            name = info.filename
            basename = PurePosixPath(name).name
            if query_lower in basename.lower() or query_lower in name.lower():
                dt = None
                try:
                    dt = datetime.datetime(*info.date_time)
                except Exception:
                    pass
                matches.append((name, info.file_size, dt))

        self._file_table.setRowCount(len(matches))
        self._file_count_label.setText(f"{len(matches)} results")

        for row, (full_path, size, dt) in enumerate(matches):
            name = PurePosixPath(full_path).name
            cat = get_file_category(name)
            icon_str = FILE_TYPE_ICONS.get(cat, "📎")
            ext = Path(name).suffix.lower()
            type_str = ext.upper().lstrip(".") if ext else "File"

            # Show full path in search results
            display_name = full_path

            name_item = QTableWidgetItem(f"{icon_str}  {display_name}")
            name_item.setData(Qt.ItemDataRole.UserRole, full_path)
            name_item.setData(Qt.ItemDataRole.UserRole + 1, False)
            self._file_table.setItem(row, 0, name_item)

            size_item = QTableWidgetItem(format_size(size))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            size_item.setData(Qt.ItemDataRole.UserRole, size)
            self._file_table.setItem(row, 1, size_item)

            type_item = QTableWidgetItem(type_str)
            self._file_table.setItem(row, 2, type_item)

            date_str = dt.strftime("%Y-%m-%d %H:%M") if dt else ""
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._file_table.setItem(row, 3, date_item)

        self._file_table.setSortingEnabled(True)

    def _focus_search(self):
        self._search_bar.setFocus()
        self._search_bar.selectAll()

    # ── Context Menu ──
    def _show_context_menu(self, pos):
        row = self._file_table.rowAt(pos.y())
        if row < 0:
            return

        item = self._file_table.item(row, 0)
        if not item:
            return

        full_path = item.data(Qt.ItemDataRole.UserRole)
        is_dir = item.data(Qt.ItemDataRole.UserRole + 1)

        menu = QMenu(self)

        if is_dir:
            open_action = menu.addAction("📂  Open Folder")
            open_action.triggered.connect(lambda: self._navigate_to(full_path))
            menu.addSeparator()
            extract_action = menu.addAction("📥  Extract Folder...")
            extract_action.triggered.connect(lambda: self._extract_folder(full_path))
        else:
            preview_action = menu.addAction("👁️  Preview")
            preview_action.triggered.connect(lambda: self._preview_file(full_path))
            menu.addSeparator()
            extract_action = menu.addAction("📥  Extract File...")
            extract_action.triggered.connect(lambda: self._extract_single(full_path))

        menu.addSeparator()
        copy_path_action = menu.addAction("📋  Copy Path")
        copy_path_action.triggered.connect(
            lambda: QApplication.clipboard().setText(full_path)
        )

        menu.exec(self._file_table.viewport().mapToGlobal(pos))

    # ── Extraction ──
    def _extract_all(self):
        if not self._zip_file:
            return

        dest = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if not dest:
            return

        try:
            self._zip_file.extractall(dest)
            QMessageBox.information(
                self, "Success",
                f"All files extracted to:\n{dest}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed:\n{str(e)}")

    def _extract_single(self, zip_path: str):
        if not self._zip_file:
            return

        filename = PurePosixPath(zip_path).name
        dest, _ = QFileDialog.getSaveFileName(self, "Save File As", filename)
        if not dest:
            return

        try:
            data = self._zip_file.read(zip_path)
            with open(dest, "wb") as f:
                f.write(data)
            QMessageBox.information(self, "Success", f"File saved to:\n{dest}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed:\n{str(e)}")

    def _extract_folder(self, folder_path: str):
        if not self._zip_file:
            return

        dest = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if not dest:
            return

        prefix = f"{folder_path}/" if not folder_path.endswith("/") else folder_path
        try:
            count = 0
            for info in self._all_entries:
                if info.filename.startswith(prefix) and not info.is_dir():
                    # Maintain relative structure
                    relative = info.filename[len(prefix):]
                    target = os.path.join(dest, folder_path.split("/")[-1], relative)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    data = self._zip_file.read(info.filename)
                    with open(target, "wb") as f:
                        f.write(data)
                    count += 1

            QMessageBox.information(
                self, "Success",
                f"Extracted {count} files to:\n{dest}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed:\n{str(e)}")

    # ── Drag & Drop on main window ──
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(".zip"):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(".zip"):
                self._load_zip(path)

    # ── About ──
    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            f"<p>Version {APP_VERSION}</p>"
            f"<p>A premium ZIP archive browser & extractor.</p>"
            f"<p>Built with Python + PyQt6.</p>"
            f"<hr>"
            f"<p style='color: #8b949e;'>All operations run locally — your files never leave your computer.</p>"
        )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Apply dark theme
    app.setStyleSheet(DARK_THEME_QSS)

    # Set palette for native widgets
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#1f6feb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = ZipNavigatorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
