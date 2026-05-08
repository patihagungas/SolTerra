"""
viewer.py - Drawing viewer widget (PDF + images) for SolTerra Drawing Manager.
PDF rendered via PyMuPDF (fitz). Images via QPixmap.
Supports zoom (Ctrl+scroll / buttons) and pan (scroll bars).
"""
from __future__ import annotations
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QLabel, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
PDF_EXT = ".pdf"


class _PannableLabel(QLabel):
    """QLabel that supports middle/left-drag panning via the parent scroll area."""

    def __init__(self, scroll_area: QScrollArea, parent=None):
        super().__init__(parent)
        self._scroll = scroll_area
        self._drag_start: QPoint | None = None
        self._h_start = 0
        self._v_start = 0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self._drag_start = e.globalPosition().toPoint()
            self._h_start = self._scroll.horizontalScrollBar().value()
            self._v_start = self._scroll.verticalScrollBar().value()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_start is not None:
            delta = e.globalPosition().toPoint() - self._drag_start
            self._scroll.horizontalScrollBar().setValue(self._h_start - delta.x())
            self._scroll.verticalScrollBar().setValue(self._v_start - delta.y())

    def mouseReleaseEvent(self, e: QMouseEvent):
        self._drag_start = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)


class DrawingViewer(QWidget):
    ZOOM_MIN = 0.05
    ZOOM_MAX = 8.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file: Path | None = None
        self._pdf = None          # fitz.Document
        self._page_idx = 0
        self._zoom = 1.0
        self._base_pixmap: QPixmap | None = None   # original-size image (for images)
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  Setup                                                               #
    # ------------------------------------------------------------------ #
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- toolbar ----
        bar = QFrame()
        bar.setFixedHeight(36)
        bar.setStyleSheet("background:#252535; border-bottom:1px solid #3a3a50;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(6, 0, 6, 0)
        bar_layout.setSpacing(4)

        def _btn(text, tip, cb):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setFixedSize(30, 26)
            b.setStyleSheet(
                "QPushButton{background:#3a3a50;color:#cdd6f4;border:none;border-radius:4px;font-size:13px;}"
                "QPushButton:hover{background:#4a4a60;}"
            )
            b.clicked.connect(cb)
            return b

        self._btn_prev   = _btn("◀", "Previous page", self._prev_page)
        self._btn_next   = _btn("▶", "Next page",     self._next_page)
        self._lbl_page   = QLabel("–")
        self._lbl_page.setStyleSheet("color:#a6adc8;font-size:12px;")
        self._lbl_page.setFixedWidth(80)
        self._lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_zoom_out = _btn("−", "Zoom out (Ctrl+scroll)", self._zoom_out)
        self._btn_zoom_in  = _btn("+", "Zoom in  (Ctrl+scroll)", self._zoom_in)
        self._btn_fit      = _btn("⊡", "Fit to window",          self._fit)
        self._lbl_zoom     = QLabel("100%")
        self._lbl_zoom.setStyleSheet("color:#a6adc8;font-size:12px;")
        self._lbl_zoom.setFixedWidth(48)
        self._lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bar_layout.addWidget(self._btn_prev)
        bar_layout.addWidget(self._lbl_page)
        bar_layout.addWidget(self._btn_next)
        bar_layout.addSpacing(12)
        bar_layout.addWidget(self._btn_zoom_out)
        bar_layout.addWidget(self._lbl_zoom)
        bar_layout.addWidget(self._btn_zoom_in)
        bar_layout.addWidget(self._btn_fit)
        bar_layout.addStretch()

        # ---- scroll area ----
        self._scroll = QScrollArea()
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setStyleSheet("background:#1e1e2e; border:none;")
        self._scroll.setWidgetResizable(False)

        self._canvas = _PannableLabel(self._scroll)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._scroll.setWidget(self._canvas)

        # ---- placeholder ----
        self._placeholder = QLabel("Select a drawing to preview")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color:#555; font-size:15px; background:#1e1e2e;")

        root.addWidget(bar)
        root.addWidget(self._placeholder)
        root.addWidget(self._scroll)
        self._scroll.hide()

        self._set_controls_enabled(False)

    def _set_controls_enabled(self, yes: bool):
        for w in (self._btn_prev, self._btn_next,
                  self._btn_zoom_in, self._btn_zoom_out, self._btn_fit):
            w.setEnabled(yes)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def load_file(self, file_path: str | Path):
        self._close_pdf()
        self._file = Path(file_path)
        self._zoom = 1.0
        self._page_idx = 0
        ext = self._file.suffix.lower()

        self._placeholder.hide()
        self._scroll.show()
        self._set_controls_enabled(True)

        if ext == PDF_EXT:
            self._load_pdf()
        elif ext in IMAGE_EXTS:
            self._load_image()
        else:
            self._canvas.setPixmap(QPixmap())
            self._canvas.setText(
                f"No preview for .{ext.lstrip('.')} files.\n\n"
                "Double-click the row to open with your system viewer."
            )
            self._canvas.setStyleSheet("color:#888; font-size:13px;")
            self._canvas.resize(400, 200)
            self._lbl_page.setText("–")
            self._lbl_zoom.setText("–")
            self._btn_prev.setEnabled(False)
            self._btn_next.setEnabled(False)

    def clear(self):
        self._close_pdf()
        self._file = None
        self._base_pixmap = None
        self._scroll.hide()
        self._placeholder.show()
        self._set_controls_enabled(False)

    # ------------------------------------------------------------------ #
    #  PDF                                                                 #
    # ------------------------------------------------------------------ #
    def _load_pdf(self):
        if not HAS_FITZ:
            self._canvas.setText(
                "PyMuPDF not installed.\n\nRun:  pip install pymupdf"
            )
            self._canvas.resize(400, 120)
            self._lbl_page.setText("–")
            return
        try:
            self._pdf = fitz.open(str(self._file))
            self._render_pdf()
        except Exception as exc:
            self._canvas.setText(f"Error opening PDF:\n{exc}")
            self._canvas.resize(400, 120)

    def _render_pdf(self):
        if not self._pdf:
            return
        page = self._pdf[self._page_idx]
        mat = fitz.Matrix(2.0 * self._zoom, 2.0 * self._zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                     QImage.Format.Format_RGB888)
        self._show_pixmap(QPixmap.fromImage(img))
        total = len(self._pdf)
        self._lbl_page.setText(f"{self._page_idx + 1} / {total}")
        self._btn_prev.setEnabled(self._page_idx > 0)
        self._btn_next.setEnabled(self._page_idx < total - 1)
        self._lbl_zoom.setText(f"{int(self._zoom * 100)}%")

    def _close_pdf(self):
        if self._pdf:
            self._pdf.close()
            self._pdf = None

    def _prev_page(self):
        if self._pdf and self._page_idx > 0:
            self._page_idx -= 1
            self._render_pdf()

    def _next_page(self):
        if self._pdf and self._page_idx < len(self._pdf) - 1:
            self._page_idx += 1
            self._render_pdf()

    # ------------------------------------------------------------------ #
    #  Images                                                              #
    # ------------------------------------------------------------------ #
    def _load_image(self):
        self._base_pixmap = QPixmap(str(self._file))
        if self._base_pixmap.isNull():
            self._canvas.setText("Could not load image.")
            return
        self._lbl_page.setText("Image")
        self._btn_prev.setEnabled(False)
        self._btn_next.setEnabled(False)
        self._apply_image_zoom()

    def _apply_image_zoom(self):
        if not self._base_pixmap:
            return
        w = int(self._base_pixmap.width()  * self._zoom)
        h = int(self._base_pixmap.height() * self._zoom)
        scaled = self._base_pixmap.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._show_pixmap(scaled)
        self._lbl_zoom.setText(f"{int(self._zoom * 100)}%")

    # ------------------------------------------------------------------ #
    #  Zoom                                                                #
    # ------------------------------------------------------------------ #
    def _show_pixmap(self, pm: QPixmap):
        self._canvas.setPixmap(pm)
        self._canvas.resize(pm.size())

    def _zoom_in(self):
        self._set_zoom(self._zoom * 1.25)

    def _zoom_out(self):
        self._set_zoom(self._zoom / 1.25)

    def _fit(self):
        self._set_zoom(1.0)

    def _set_zoom(self, z: float):
        self._zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, z))
        self._refresh()

    def _refresh(self):
        if not self._file:
            return
        ext = self._file.suffix.lower()
        if ext == PDF_EXT:
            self._render_pdf()
        elif ext in IMAGE_EXTS:
            self._apply_image_zoom()

    def wheelEvent(self, e: QWheelEvent):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if e.angleDelta().y() > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            e.accept()
        else:
            super().wheelEvent(e)
