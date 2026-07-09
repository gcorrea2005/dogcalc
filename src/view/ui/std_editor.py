"""STAAD .std text editor — syntax-highlighted, parse-check-load workflow."""

from pathlib import Path
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QFileDialog, QLabel
)
from PySide6.QtCore import Qt, Signal, QRect, QSize
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
    QPainter, QTextFormat
)

# ── STAAD keywords for highlighting ──
KEYWORDS = [
    "STAAD", "SPACE", "PLANE", "TRUSS", "FLOOR",
    "START", "END", "JOB", "INFORMATION",
    "INPUT", "WIDTH", "UNIT", "METER", "KN", "MM", "KNS", "KGS",
    "JOINT", "COORDINATES", "MEMBER", "INCIDENCES",
    "PROPERTY", "TABLE", "PRISMATIC", "YD", "ZD",
    "DEFINE", "MATERIAL", "ISOTROPIC", "ISOTROPIC",
    "E", "POISSON", "DENSITY", "YIELD", "STRENGTH",
    "CONSTANTS", "ALL",
    "SUPPORTS", "FIXED", "PINNED", "ROLLER", "FREE",
    "LOAD", "LOADTYPE", "SELFWEIGHT", "DEAD", "LIVE", "WIND",
    "FX", "FY", "FZ", "MX", "MY", "MZ",
    "PERFORM", "ANALYSIS", "FINISH",
    "MEMBER", "LOAD", "UNI", "GX", "GY", "GZ",
    "TO", "BUT", "NOT",
]
KEYWORDS_SET = set(KEYWORDS)

# Theme colors
CLR_BG   = QColor("#000018")
CLR_TEXT = QColor("#CCCCCC")
CLR_KW   = QColor("#44AAFF")   # keywords
CLR_CMT  = QColor("#666688")   # comments (*)
CLR_NUM   = QColor("#FF9944")  # numbers
CLR_SECT  = QColor("#FFCC00")  # section headers (JOINT COORDINATES, etc.)
CLR_ERR   = QColor("#FF4444")  # error annotations

FONT = QFont("Courier New", 12)

# Section headers that start with keyword (uppercase match)
SECTION_PATTERNS = [
    "JOINT COORDINATES", "MEMBER INCIDENCES", "MEMBER PROPERTY",
    "DEFINE MATERIAL START", "END DEFINE MATERIAL", "CONSTANTS",
    "SUPPORTS", "JOINT LOAD", "MEMBER LOAD", "PERFORM ANALYSIS",
    "END JOB INFORMATION", "START JOB INFORMATION",
]


class _StaadHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for STAAD .std files."""

    def __init__(self, document):
        super().__init__(document)
        self._fmt_kw = QTextCharFormat()
        self._fmt_kw.setForeground(CLR_KW)
        self._fmt_kw.setFontWeight(QFont.Weight.Bold)

        self._fmt_cmt = QTextCharFormat()
        self._fmt_cmt.setForeground(CLR_CMT)
        self._fmt_cmt.setFontItalic(True)

        self._fmt_num = QTextCharFormat()
        self._fmt_num.setForeground(CLR_NUM)

        self._fmt_sect = QTextCharFormat()
        self._fmt_sect.setForeground(CLR_SECT)
        self._fmt_sect.setFontWeight(QFont.Weight.Bold)

    def highlightBlock(self, text: str):
        # Comments: lines starting with *
        if text.strip().startswith("*"):
            self.setFormat(0, len(text), self._fmt_cmt)
            return

        # Section lines: match full uppercase lines
        upper = text.strip().upper()
        for pat in SECTION_PATTERNS:
            if upper == pat or upper.startswith(pat):
                self.setFormat(0, len(text), self._fmt_sect)
                return
        # Also match LOAD n ... lines
        if upper.startswith("LOAD "):
            self.setFormat(0, len(text), self._fmt_sect)
            return

        # Keywords
        for word in text.split():
            uw = word.upper()
            if uw in KEYWORDS_SET:
                idx = text.index(word)
                self.setFormat(idx, len(word), self._fmt_kw)

        # Numbers
        for word in text.split():
            try:
                float(word.replace("-", "").replace("+", ""))
                idx = text.index(word)
                self.setFormat(idx, len(word), self._fmt_num)
            except ValueError:
                pass


class _LineNumberArea(QWidget):
    """Line number gutter for the editor."""

    def __init__(self, text_edit, std_editor):
        super().__init__(text_edit)
        self._text = text_edit
        self._std = std_editor

    def sizeHint(self):
        return QSize(self._std.line_number_width(), 0)

    def paintEvent(self, event):
        self._std.line_number_paint(event)


class StdEditor(QDockWidget):
    """Dockable STAAD .std text editor with syntax highlighting and Check/Load."""

    model_loaded = Signal(object)   # emits Document when parsed

    def __init__(self, document, parent=None):
        super().__init__("STD EDITOR", parent)
        self._doc = document
        self._filepath = None

        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(500)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)

        self._file_label = QLabel("  (no file)")
        self._file_label.setStyleSheet("color: #888; font: 11px 'Courier New';")
        toolbar.addWidget(self._file_label)
        toolbar.addStretch()

        for label, slot in [
            ("Open", self._on_open), ("Save", self._on_save),
            ("Sync", self._on_check), ("Load+Run", self._on_load_run)
        ]:
            btn = QPushButton(label)
            btn.setFixedSize(70, 24)
            btn.setStyleSheet("QPushButton { background: #002244; color: #CCC; border: 1px solid #336; font: 11px 'Courier New'; } QPushButton:hover { background: #003366; }")
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)

        layout.addLayout(toolbar)

        # Editor
        self._editor = QPlainTextEdit()
        self._editor.setFont(FONT)
        self._editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {CLR_BG.name()};
                color: {CLR_TEXT.name()};
                border: 1px solid #1a1a3a;
                selection-background-color: #003388;
            }}
        """)
        self._editor.setTabStopDistance(32)
        self._highlighter = _StaadHighlighter(self._editor.document())

        # Line numbers
        self._line_area = _LineNumberArea(self._editor, self)
        self._editor.blockCountChanged.connect(self._update_line_area_width)
        self._editor.updateRequest.connect(self._update_line_area)
        self._update_line_area_width()

        layout.addWidget(self._editor)
        self.setWidget(body)

    # ── Line numbers ──────────────────────────────

    def line_number_width(self):
        digits = max(1, len(str(self._editor.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance('9') * digits

    def _update_line_area_width(self):
        self._editor.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_line_area(self, rect, dy):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self._editor.viewport().rect()):
            self._update_line_area_width()

    def line_number_paint(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor("#000011"))
        painter.setPen(QColor("#445566"))
        painter.setFont(FONT)

        block = self._editor.firstVisibleBlock()
        block_num = block.blockNumber()
        top = self._editor.blockBoundingGeometry(block).translated(self._editor.contentOffset()).top()
        bottom = top + self._editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                num = str(block_num + 1)
                painter.drawText(0, int(top), self._line_area.width() - 4,
                                 self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, num)
            block = block.next()
            top = bottom
            bottom = top + self._editor.blockBoundingRect(block).height()
            block_num += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self._editor.contentsRect()
        self._line_area.setGeometry(QRect(cr.left(), cr.top(),
                                          self.line_number_width(), cr.height()))

    # ── File I/O ──────────────────────────────────

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open STAAD", "", "STAAD (*.std);;All (*.*)")
        if not path:
            return
        try:
            text = Path(path).read_text()
            self._editor.setPlainText(text)
            self._filepath = path
            self._file_label.setText(f"  {Path(path).name}")
        except Exception as e:
            self._editor.setPlainText(f"* ERROR opening file: {e}")

    def _on_save(self):
        if self._filepath:
            path = self._filepath
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Save STAAD", "model.std", "STAAD (*.std)")
        if not path:
            return
        try:
            Path(path).write_text(self._editor.toPlainText())
            self._filepath = path
            self._file_label.setText(f"  {Path(path).name}")
        except Exception as e:
            self._editor.appendPlainText(f"\n* ERROR saving: {e}")

    def _on_check(self):
        """Parse text and load into document + tables (no analysis)."""
        text = self._editor.toPlainText()
        if not text.strip():
            return
        try:
            import tempfile, os
            with tempfile.NamedTemporaryFile(mode='w', suffix='.std', delete=False) as f:
                f.write(text)
                tmpath = f.name
            from src.io.staad_file import parse_std
            new_doc = parse_std(tmpath)
            os.unlink(tmpath)
            self.model_loaded.emit(new_doc)
            self._editor.appendPlainText(f"\n* Sync OK: {new_doc.node_count}N {new_doc.member_count}M")
        except Exception as e:
            self._editor.appendPlainText(f"\n* PARSE ERROR: {e}")

    def _on_load_run(self):
        """Parse text into document and run analysis."""
        text = self._editor.toPlainText()
        if not text.strip():
            return
        try:
            # Save to temp file and parse
            import tempfile, os
            with tempfile.NamedTemporaryFile(mode='w', suffix='.std', delete=False) as f:
                f.write(text)
                tmpath = f.name

            from src.io.staad_file import parse_std
            new_doc = parse_std(tmpath)
            os.unlink(tmpath)

            self.model_loaded.emit(new_doc)
            self._editor.appendPlainText(f"\n* Loaded: {new_doc.node_count}N {new_doc.member_count}M")

            # Auto-run analysis
            from src.engine.solver import run_analysis_for_document
            result = run_analysis_for_document(new_doc)
            if result.success:
                self._editor.appendPlainText(f"* Analysis OK | Max disp: {result.max_displacement()*1000:.2f} mm")
            else:
                self._editor.appendPlainText(f"* Analysis FAILED: {result.errors[0] if result.errors else '?'}")
        except Exception as e:
            self._editor.appendPlainText(f"\n* ERROR: {e}")

    def set_text(self, text: str):
        self._editor.setPlainText(text)

    def load_file(self, path: str):
        text = Path(path).read_text()
        self._editor.setPlainText(text)
        self._filepath = path
        self._file_label.setText(f"  {Path(path).name}")
