"""
ui.py - Full UI for SolTerra Drawing Manager.
Layout: sidebar navigation + stacked content area.
"""
from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QTableWidget, QTableWidgetItem,
    QSplitter, QTabWidget, QLineEdit, QComboBox, QTextEdit, QFormLayout,
    QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QHeaderView,
    QScrollArea, QGridLayout, QSizePolicy, QDateEdit, QListWidget,
    QListWidgetItem, QAbstractItemView, QMenu, QApplication,
)
from PyQt6.QtCore import Qt, QSize, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QIcon, QPen, QAction

from db import DatabaseManager
from viewer import DrawingViewer

# ------------------------------------------------------------------ #
#  Colour constants                                                    #
# ------------------------------------------------------------------ #
C_BG       = "#1e1e2e"
C_SIDEBAR  = "#181825"
C_SURFACE  = "#252535"
C_SURFACE2 = "#313244"
C_BORDER   = "#3a3a50"
C_ACCENT   = "#89b4fa"
C_GREEN    = "#a6e3a1"
C_YELLOW   = "#f9e2af"
C_RED      = "#f38ba8"
C_TEXT     = "#cdd6f4"
C_SUB      = "#a6adc8"

STATUS_COLORS = {
    "Draft":    C_YELLOW,
    "Released": C_GREEN,
    "Obsolete": C_RED,
}

DARK_STYLE = f"""
QWidget {{
    background: {C_BG};
    color: {C_TEXT};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QScrollArea, QAbstractScrollArea {{ background: {C_BG}; border: none; }}
QScrollBar:vertical {{
    background: {C_SURFACE}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {C_SURFACE2}; border-radius: 4px; min-height: 20px;
}}
QScrollBar:horizontal {{
    background: {C_SURFACE}; height: 8px; border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {C_SURFACE2}; border-radius: 4px; min-width: 20px;
}}
QTableWidget {{
    background: {C_SURFACE};
    gridline-color: {C_BORDER};
    border: none;
    selection-background-color: {C_SURFACE2};
}}
QHeaderView::section {{
    background: {C_SIDEBAR};
    color: {C_SUB};
    border: none;
    padding: 4px 8px;
    font-size: 12px;
}}
QLineEdit, QTextEdit, QComboBox, QDateEdit {{
    background: {C_SURFACE2};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 5px;
    padding: 4px 8px;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {C_ACCENT};
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {C_SURFACE2};
    color: {C_TEXT};
    selection-background-color: {C_ACCENT};
    selection-color: {C_SIDEBAR};
}}
QPushButton {{
    background: {C_SURFACE2};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 5px;
    padding: 5px 14px;
}}
QPushButton:hover  {{ background: {C_ACCENT}; color: {C_SIDEBAR}; border-color: {C_ACCENT}; }}
QPushButton:pressed {{ background: #6a94e0; }}
QTabWidget::pane   {{ border: 1px solid {C_BORDER}; background: {C_SURFACE}; }}
QTabBar::tab {{
    background: {C_SIDEBAR};
    color: {C_SUB};
    padding: 6px 16px;
    border: none;
}}
QTabBar::tab:selected {{ background: {C_SURFACE}; color: {C_TEXT}; }}
QListWidget {{
    background: {C_SURFACE};
    border: none;
}}
QListWidget::item:selected {{ background: {C_SURFACE2}; }}
QDialog {{ background: {C_BG}; }}
QMessageBox {{ background: {C_BG}; }}
QMenu {{
    background: {C_SURFACE2};
    border: 1px solid {C_BORDER};
}}
QMenu::item:selected {{ background: {C_ACCENT}; color: {C_SIDEBAR}; }}
"""

ALLOWED_EXTS = "Drawings (*.pdf *.dwg *.dxf *.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #
def _card(title: str, value: str, color: str = C_ACCENT) -> QFrame:
    f = QFrame()
    f.setStyleSheet(
        f"QFrame{{background:{C_SURFACE};border:1px solid {C_BORDER};"
        f"border-radius:8px;padding:4px;}}"
    )
    lay = QVBoxLayout(f)
    lbl_t = QLabel(title)
    lbl_t.setStyleSheet(f"color:{C_SUB};font-size:11px;border:none;")
    lbl_v = QLabel(value)
    lbl_v.setStyleSheet(f"color:{color};font-size:24px;font-weight:bold;border:none;")
    lay.addWidget(lbl_t)
    lay.addWidget(lbl_v)
    return f


def _status_badge(status: str) -> QLabel:
    lbl = QLabel(f" {status} ")
    col = STATUS_COLORS.get(status, C_SUB)
    lbl.setStyleSheet(
        f"color:{C_SIDEBAR};background:{col};border-radius:4px;"
        f"font-size:11px;font-weight:bold;padding:1px 4px;"
    )
    return lbl


def _sidebar_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCheckable(True)
    btn.setFixedHeight(40)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent; color: {C_SUB};
            border: none; border-radius: 6px;
            text-align: left; padding-left: 16px;
            font-size: 14px;
        }}
        QPushButton:hover   {{ background: {C_SURFACE}; color: {C_TEXT}; }}
        QPushButton:checked {{ background: {C_SURFACE}; color: {C_ACCENT};
                               font-weight: bold; }}
    """)
    return btn


# ------------------------------------------------------------------ #
#  Simple bar-chart widget (no matplotlib dependency)                 #
# ------------------------------------------------------------------ #
class BarChartWidget(QWidget):
    BAR_COLORS = [C_ACCENT, C_GREEN, C_YELLOW, C_RED, "#cba6f7", "#89dceb"]

    def __init__(self, data: list[tuple[str, int]] | None = None, parent=None):
        super().__init__(parent)
        self.data = data or []
        self.setMinimumHeight(160)

    def set_data(self, data: list[tuple[str, int]]):
        self.data = data
        self.update()

    def paintEvent(self, _):
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        label_w = 140
        val_w   = 36
        pad     = 10
        n       = len(self.data)
        bar_h   = min(28, (h - pad * 2) // n - 4)
        max_v   = max(v for _, v in self.data) or 1

        for i, (label, value) in enumerate(self.data):
            y   = pad + i * (bar_h + 6)
            col = QColor(self.BAR_COLORS[i % len(self.BAR_COLORS)])

            # label
            p.setPen(QColor(C_SUB))
            p.drawText(0, y, label_w - 6, bar_h,
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       label[:22])

            # bar
            bar_max_w = w - label_w - val_w - 8
            bw = max(4, int((value / max_v) * bar_max_w))
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(label_w, y + 2, bw, bar_h - 4, 4, 4)

            # value
            p.setPen(QColor(C_TEXT))
            p.drawText(label_w + bw + 6, y, val_w, bar_h,
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       str(value))
        p.end()


# ================================================================== #
#  DASHBOARD PANEL                                                     #
# ================================================================== #
class DashboardPanel(QWidget):
    open_drawings_requested = pyqtSignal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Dashboard")
        title.setStyleSheet(f"font-size:22px;font-weight:bold;color:{C_TEXT};")
        root.addWidget(title)

        # stat cards row
        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(12)
        root.addLayout(self._cards_row)

        # middle: chart + recent lists
        mid = QHBoxLayout()
        mid.setSpacing(16)

        # chart block
        chart_box = QFrame()
        chart_box.setStyleSheet(
            f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:8px;"
        )
        chart_lay = QVBoxLayout(chart_box)
        chart_lay.setContentsMargins(12, 10, 12, 10)
        chart_lay.addWidget(QLabel("Drawings by Category"))
        self._chart = BarChartWidget()
        chart_lay.addWidget(self._chart)
        mid.addWidget(chart_box, 3)

        # right column: type breakdown
        type_box = QFrame()
        type_box.setStyleSheet(
            f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:8px;"
        )
        type_lay = QVBoxLayout(type_box)
        type_lay.setContentsMargins(12, 10, 12, 10)
        type_lay.addWidget(QLabel("By File Type"))
        self._type_chart = BarChartWidget()
        type_lay.addWidget(self._type_chart)
        mid.addWidget(type_box, 2)

        root.addLayout(mid)

        # recent rows
        bot = QHBoxLayout()
        bot.setSpacing(16)

        self._recent_mod  = self._make_list_box("Recently Modified")
        self._recent_view = self._make_list_box("Recently Viewed")
        bot.addWidget(self._recent_mod[0])
        bot.addWidget(self._recent_view[0])
        root.addLayout(bot)
        root.addStretch()

    def _make_list_box(self, title: str):
        box = QFrame()
        box.setStyleSheet(
            f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:8px;"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 10)
        hdr = QLabel(title)
        hdr.setStyleSheet(f"color:{C_TEXT};font-weight:bold;")
        lay.addWidget(hdr)
        lst = QListWidget()
        lst.setStyleSheet(f"background:{C_SURFACE};border:none;font-size:12px;")
        lst.setFixedHeight(160)
        lay.addWidget(lst)
        return box, lst

    def refresh(self):
        stats = self.db.get_stats()

        # clear cards
        while self._cards_row.count():
            item = self._cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        by_status = stats["by_status"]
        self._cards_row.addWidget(_card("Total Drawings", str(stats["total"]), C_ACCENT))
        self._cards_row.addWidget(_card("Draft",    str(by_status.get("Draft",    0)), C_YELLOW))
        self._cards_row.addWidget(_card("Released", str(by_status.get("Released", 0)), C_GREEN))
        self._cards_row.addWidget(_card("Obsolete", str(by_status.get("Obsolete", 0)), C_RED))
        self._cards_row.addStretch()

        self._chart.set_data(stats["by_category"])
        self._type_chart.set_data(stats["by_type"])

        # recent modified
        _, lst_mod = self._recent_mod
        lst_mod.clear()
        for r in self.db.get_recent_modified(12):
            lst_mod.addItem(f"  {r['drawing_number']}  –  {r['title'][:35]}")

        # recent viewed
        _, lst_view = self._recent_view
        lst_view.clear()
        for r in self.db.get_recent_views(12):
            lst_view.addItem(f"  {r['drawing_number']}  –  {r['title'][:35]}")


# ================================================================== #
#  DIALOGS                                                             #
# ================================================================== #
class _BaseDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self._form = QFormLayout()
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._form.setSpacing(10)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(self._form)
        root.addSpacing(8)
        root.addWidget(buttons)


class ProjectDialog(_BaseDialog):
    def __init__(self, parent=None, name="", description=""):
        super().__init__("Project", parent)
        self._name = QLineEdit(name)
        self._desc = QLineEdit(description)
        self._form.addRow("Name*:", self._name)
        self._form.addRow("Description:", self._desc)

    def values(self):
        return self._name.text().strip(), self._desc.text().strip()

    def accept(self):
        if not self._name.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        super().accept()


class CategoryDialog(_BaseDialog):
    def __init__(self, parent=None, name="", description=""):
        super().__init__("Category", parent)
        self._name = QLineEdit(name)
        self._desc = QLineEdit(description)
        self._form.addRow("Name*:", self._name)
        self._form.addRow("Description:", self._desc)

    def values(self):
        return self._name.text().strip(), self._desc.text().strip()

    def accept(self):
        if not self._name.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        super().accept()


class AddDrawingDialog(QDialog):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Add Drawing")
        self.setMinimumWidth(520)
        self._file_path = ""
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # file picker
        file_row = QHBoxLayout()
        self._file_lbl = QLineEdit()
        self._file_lbl.setReadOnly(True)
        self._file_lbl.setPlaceholderText("Select drawing file…")
        btn_browse = QPushButton("Browse")
        btn_browse.setFixedWidth(72)
        btn_browse.clicked.connect(self._browse)
        file_row.addWidget(self._file_lbl)
        file_row.addWidget(btn_browse)
        form.addRow("File*:", file_row)

        self._num   = QLineEdit(); self._num.setPlaceholderText("e.g. DWG-001")
        self._title = QLineEdit(); self._title.setPlaceholderText("Drawing title")
        self._part  = QLineEdit(); self._part.setPlaceholderText("Part / assembly number")
        self._rev   = QLineEdit("A"); self._rev.setFixedWidth(60)
        self._desc  = QTextEdit(); self._desc.setFixedHeight(60)
        self._tags  = QLineEdit(); self._tags.setPlaceholderText("comma, separated, tags")
        self._note  = QLineEdit("Initial upload")

        # project / category / status
        self._project  = QComboBox()
        self._category = QComboBox()
        self._status   = QComboBox()
        self._status.addItems(["Draft", "Released", "Obsolete"])

        self._project.addItem("— None —", None)
        for p in self.db.get_projects():
            self._project.addItem(p["name"], p["id"])

        self._category.addItem("— None —", None)
        for c in self.db.get_categories():
            self._category.addItem(c["name"], c["id"])

        form.addRow("Drawing #*:", self._num)
        form.addRow("Title*:",     self._title)
        form.addRow("Part #:",     self._part)
        form.addRow("Revision:",   self._rev)
        form.addRow("Project:",    self._project)
        form.addRow("Category:",   self._category)
        form.addRow("Status:",     self._status)
        form.addRow("Description:", self._desc)
        form.addRow("Tags:",       self._tags)
        form.addRow("Change note:", self._note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root.addLayout(form)
        root.addSpacing(8)
        root.addWidget(buttons)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Drawing", "", ALLOWED_EXTS)
        if path:
            self._file_path = path
            self._file_lbl.setText(path)
            # auto-fill drawing number from filename if empty
            if not self._num.text():
                self._num.setText(Path(path).stem)
            if not self._title.text():
                self._title.setText(Path(path).stem.replace("_", " ").replace("-", " "))

    def accept(self):
        if not self._file_path:
            QMessageBox.warning(self, "Validation", "Please select a file.")
            return
        if not self._num.text().strip():
            QMessageBox.warning(self, "Validation", "Drawing number is required.")
            return
        if not self._title.text().strip():
            QMessageBox.warning(self, "Validation", "Title is required.")
            return
        super().accept()

    def values(self) -> dict:
        return dict(
            file_path    = self._file_path,
            drawing_number = self._num.text().strip(),
            title        = self._title.text().strip(),
            part_number  = self._part.text().strip(),
            revision     = self._rev.text().strip() or "A",
            project_id   = self._project.currentData(),
            category_id  = self._category.currentData(),
            status       = self._status.currentText(),
            description  = self._desc.toPlainText().strip(),
            tags         = [t.strip() for t in self._tags.text().split(",") if t.strip()],
            change_note  = self._note.text().strip() or "Initial upload",
        )


class EditDrawingDialog(QDialog):
    def __init__(self, db: DatabaseManager, drawing: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.drawing = drawing
        self.setWindowTitle(f"Edit – {drawing['drawing_number']}")
        self.setMinimumWidth(520)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        d = self.drawing
        self._title = QLineEdit(d["title"] or "")
        self._part  = QLineEdit(d["part_number"] or "")
        self._rev   = QLineEdit(d["current_revision"] or "A"); self._rev.setFixedWidth(60)
        self._desc  = QTextEdit(d["description"] or ""); self._desc.setFixedHeight(60)
        tags_str    = ", ".join(self.db.get_tags_for_drawing(d["id"]))
        self._tags  = QLineEdit(tags_str)

        self._project  = QComboBox()
        self._category = QComboBox()
        self._status   = QComboBox()
        self._status.addItems(["Draft", "Released", "Obsolete"])

        self._project.addItem("— None —", None)
        cur_proj = d["project_id"]
        for p in self.db.get_projects():
            self._project.addItem(p["name"], p["id"])
            if p["id"] == cur_proj:
                self._project.setCurrentIndex(self._project.count() - 1)

        self._category.addItem("— None —", None)
        cur_cat = d["category_id"]
        for c in self.db.get_categories():
            self._category.addItem(c["name"], c["id"])
            if c["id"] == cur_cat:
                self._category.setCurrentIndex(self._category.count() - 1)

        idx = self._status.findText(d["status"] or "Draft")
        if idx >= 0:
            self._status.setCurrentIndex(idx)

        form.addRow("Title*:",     self._title)
        form.addRow("Part #:",     self._part)
        form.addRow("Revision:",   self._rev)
        form.addRow("Project:",    self._project)
        form.addRow("Category:",   self._category)
        form.addRow("Status:",     self._status)
        form.addRow("Description:", self._desc)
        form.addRow("Tags:",       self._tags)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root.addLayout(form)
        root.addSpacing(8)
        root.addWidget(buttons)

    def accept(self):
        if not self._title.text().strip():
            QMessageBox.warning(self, "Validation", "Title is required.")
            return
        super().accept()

    def values(self) -> dict:
        return dict(
            title          = self._title.text().strip(),
            part_number    = self._part.text().strip(),
            current_revision = self._rev.text().strip() or "A",
            project_id     = self._project.currentData(),
            category_id    = self._category.currentData(),
            status         = self._status.currentText(),
            description    = self._desc.toPlainText().strip(),
            tags           = [t.strip() for t in self._tags.text().split(",") if t.strip()],
        )


class NewVersionDialog(_BaseDialog):
    def __init__(self, parent=None, current_rev: str = "A"):
        super().__init__("Upload New Version", parent)
        self._file_path = ""
        self._rev  = QLineEdit(current_rev)
        self._note = QLineEdit()
        self._note.setPlaceholderText("Describe what changed…")

        file_row = QHBoxLayout()
        self._file_lbl = QLineEdit(); self._file_lbl.setReadOnly(True)
        self._file_lbl.setPlaceholderText("Select new file…")
        btn = QPushButton("Browse"); btn.setFixedWidth(72)
        btn.clicked.connect(self._browse)
        file_row.addWidget(self._file_lbl); file_row.addWidget(btn)

        self._form.addRow("File*:",       file_row)
        self._form.addRow("New Revision:", self._rev)
        self._form.addRow("Change note:",  self._note)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", ALLOWED_EXTS)
        if path:
            self._file_path = path
            self._file_lbl.setText(path)

    def accept(self):
        if not self._file_path:
            QMessageBox.warning(self, "Validation", "Please select a file.")
            return
        super().accept()

    def values(self) -> dict:
        return dict(
            file_path   = self._file_path,
            revision    = self._rev.text().strip() or "A",
            change_note = self._note.text().strip(),
        )


class VersionHistoryDialog(QDialog):
    def __init__(self, db: DatabaseManager, drawing_id: int, drawing_number: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.drawing_id = drawing_id
        self.setWindowTitle(f"Version History – {drawing_number}")
        self.setMinimumSize(620, 340)
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Ver.", "Revision", "Change Note", "Uploaded", "Size"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)

        btn_restore = QPushButton("Restore Selected Version")
        btn_restore.clicked.connect(self._restore)
        btn_open    = QPushButton("Open File")
        btn_open.clicked.connect(self._open_file)

        bar = QHBoxLayout()
        bar.addWidget(btn_open)
        bar.addWidget(btn_restore)
        bar.addStretch()

        root.addWidget(self._table)
        root.addLayout(bar)

    def _load(self):
        self._versions = self.db.get_versions(self.drawing_id)
        self._table.setRowCount(len(self._versions))
        for row, v in enumerate(self._versions):
            self._table.setItem(row, 0, QTableWidgetItem(str(v["version_number"])))
            self._table.setItem(row, 1, QTableWidgetItem(v["revision"]))
            self._table.setItem(row, 2, QTableWidgetItem(v["change_note"] or ""))
            self._table.setItem(row, 3, QTableWidgetItem(v["uploaded_at"][:16]))
            size_kb = (v["file_size"] or 0) // 1024
            self._table.setItem(row, 4, QTableWidgetItem(f"{size_kb} KB"))

    def _restore(self):
        row = self._table.currentRow()
        if row < 0:
            return
        v = self._versions[row]
        ok = QMessageBox.question(
            self, "Restore",
            f"Restore to version {v['version_number']} (Rev {v['revision']})?",
        )
        if ok == QMessageBox.StandardButton.Yes:
            self.db.restore_version(self.drawing_id, v["id"])
            QMessageBox.information(self, "Done", "Version restored.")
            self.accept()

    def _open_file(self):
        row = self._table.currentRow()
        if row < 0:
            return
        p = Path(self._versions[row]["file_path"])
        if p.exists():
            os.startfile(str(p))
        else:
            QMessageBox.warning(self, "Not Found", f"File not found:\n{p}")


class AttachmentDialog(_BaseDialog):
    def __init__(self, parent=None):
        super().__init__("Add Attachment", parent)
        self._file_path = ""
        self._desc = QLineEdit()

        file_row = QHBoxLayout()
        self._file_lbl = QLineEdit(); self._file_lbl.setReadOnly(True)
        self._file_lbl.setPlaceholderText("Select file…")
        btn = QPushButton("Browse"); btn.setFixedWidth(72)
        btn.clicked.connect(self._browse)
        file_row.addWidget(self._file_lbl); file_row.addWidget(btn)

        self._form.addRow("File*:",       file_row)
        self._form.addRow("Description:", self._desc)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*)")
        if path:
            self._file_path = path
            self._file_lbl.setText(path)

    def accept(self):
        if not self._file_path:
            QMessageBox.warning(self, "Validation", "Please select a file.")
            return
        super().accept()

    def values(self):
        return dict(file_path=self._file_path, description=self._desc.text().strip())


class ManageListDialog(QDialog):
    """Generic manager for projects or categories."""

    def __init__(self, db: DatabaseManager, mode: str, parent=None):
        super().__init__(parent)
        self.db   = db
        self.mode = mode  # "project" or "category"
        self.setWindowTitle(f"Manage {'Projects' if mode == 'project' else 'Categories'}")
        self.setMinimumSize(420, 320)
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.setStyleSheet(f"background:{C_SURFACE};")

        bar = QHBoxLayout()
        btn_add  = QPushButton("Add")
        btn_edit = QPushButton("Edit")
        btn_del  = QPushButton("Delete")
        bar.addWidget(btn_add); bar.addWidget(btn_edit); bar.addWidget(btn_del)
        bar.addStretch()

        btn_add.clicked.connect(self._add)
        btn_edit.clicked.connect(self._edit)
        btn_del.clicked.connect(self._delete)

        root.addWidget(self._list)
        root.addLayout(bar)

    def _load(self):
        self._list.clear()
        items = self.db.get_projects() if self.mode == "project" else self.db.get_categories()
        for item in items:
            li = QListWidgetItem(item["name"])
            li.setData(Qt.ItemDataRole.UserRole, item["id"])
            self._list.addItem(li)

    def _add(self):
        dlg = ProjectDialog(self) if self.mode == "project" else CategoryDialog(self)
        if dlg.exec():
            name, desc = dlg.values()
            try:
                if self.mode == "project":
                    self.db.add_project(name, desc)
                else:
                    self.db.add_category(name, desc)
                self._load()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _edit(self):
        li = self._list.currentItem()
        if not li:
            return
        item_id = li.data(Qt.ItemDataRole.UserRole)
        dlg = ProjectDialog(self, li.text()) if self.mode == "project" else CategoryDialog(self, li.text())
        if dlg.exec():
            name, desc = dlg.values()
            try:
                if self.mode == "project":
                    self.db.update_project(item_id, name, desc)
                else:
                    self.db.update_category(item_id, name, desc)
                self._load()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete(self):
        li = self._list.currentItem()
        if not li:
            return
        ok = QMessageBox.question(self, "Confirm", f"Delete '{li.text()}'?")
        if ok == QMessageBox.StandardButton.Yes:
            item_id = li.data(Qt.ItemDataRole.UserRole)
            if self.mode == "project":
                self.db.delete_project(item_id)
            else:
                self.db.delete_category(item_id)
            self._load()


# ================================================================== #
#  DRAWING DETAIL PANEL                                                #
# ================================================================== #
class DrawingDetailPanel(QWidget):
    refreshed = pyqtSignal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._drawing_id: int | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Viewer + detail split (vertical)
        splitter = QSplitter(Qt.Orientation.Vertical)

        self._viewer = DrawingViewer()
        splitter.addWidget(self._viewer)

        # Tabs: Info / Attachments
        self._tabs = QTabWidget()
        self._tab_info  = QWidget()
        self._tab_attach = QWidget()
        self._tabs.addTab(self._tab_info,   "Info")
        self._tabs.addTab(self._tab_attach, "Attachments")

        self._build_info_tab()
        self._build_attach_tab()

        splitter.addWidget(self._tabs)
        splitter.setSizes([420, 220])
        root.addWidget(splitter)

    # ---- Info tab ----
    def _build_info_tab(self):
        lay = QFormLayout(self._tab_info)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def _ro(text=""):
            w = QLineEdit(text)
            w.setReadOnly(True)
            w.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:4px;padding:3px 6px;")
            return w

        self._i_num     = _ro()
        self._i_title   = _ro()
        self._i_part    = _ro()
        self._i_rev     = _ro()
        self._i_proj    = _ro()
        self._i_cat     = _ro()
        self._i_status  = _ro()
        self._i_type    = _ro()
        self._i_created = _ro()
        self._i_mod     = _ro()
        self._i_tags    = _ro()
        self._i_desc    = QTextEdit()
        self._i_desc.setReadOnly(True)
        self._i_desc.setFixedHeight(52)
        self._i_desc.setStyleSheet(
            f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:4px;"
        )

        lay.addRow("Drawing #:",  self._i_num)
        lay.addRow("Title:",      self._i_title)
        lay.addRow("Part #:",     self._i_part)
        lay.addRow("Revision:",   self._i_rev)
        lay.addRow("Project:",    self._i_proj)
        lay.addRow("Category:",   self._i_cat)
        lay.addRow("Status:",     self._i_status)
        lay.addRow("File Type:",  self._i_type)
        lay.addRow("Created:",    self._i_created)
        lay.addRow("Modified:",   self._i_mod)
        lay.addRow("Tags:",       self._i_tags)
        lay.addRow("Description:", self._i_desc)

    # ---- Attachments tab ----
    def _build_attach_tab(self):
        lay = QVBoxLayout(self._tab_attach)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        bar = QHBoxLayout()
        self._btn_add_att = QPushButton("Add Attachment")
        self._btn_del_att = QPushButton("Delete")
        self._btn_open_att = QPushButton("Open")
        bar.addWidget(self._btn_add_att)
        bar.addWidget(self._btn_open_att)
        bar.addWidget(self._btn_del_att)
        bar.addStretch()
        lay.addLayout(bar)

        self._att_list = QListWidget()
        self._att_list.setStyleSheet(f"background:{C_SURFACE};")
        lay.addWidget(self._att_list)

        self._btn_add_att.clicked.connect(self._add_attachment)
        self._btn_del_att.clicked.connect(self._delete_attachment)
        self._btn_open_att.clicked.connect(self._open_attachment)
        self._btn_add_att.setEnabled(False)
        self._btn_del_att.setEnabled(False)
        self._btn_open_att.setEnabled(False)

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #
    def load_drawing(self, drawing_id: int):
        self._drawing_id = drawing_id
        d = self.db.get_drawing(drawing_id)
        if not d:
            return
        self.db.record_view(drawing_id)

        self._i_num.setText(d["drawing_number"] or "")
        self._i_title.setText(d["title"] or "")
        self._i_part.setText(d["part_number"] or "")
        self._i_rev.setText(d["current_revision"] or "")
        self._i_proj.setText(d["project_name"] or "")
        self._i_cat.setText(d["category_name"] or "")
        self._i_status.setText(d["status"] or "")
        self._i_type.setText((d["file_type"] or "").upper())
        self._i_created.setText((d["created_at"] or "")[:16])
        self._i_mod.setText((d["modified_at"] or "")[:16])
        self._i_tags.setText(", ".join(self.db.get_tags_for_drawing(drawing_id)))
        self._i_desc.setPlainText(d["description"] or "")

        fp = d["current_file_path"]
        if fp and Path(fp).exists():
            self._viewer.load_file(fp)
        else:
            self._viewer.clear()

        self._load_attachments()
        self._btn_add_att.setEnabled(True)
        self._btn_del_att.setEnabled(True)
        self._btn_open_att.setEnabled(True)

    def clear(self):
        self._drawing_id = None
        self._viewer.clear()
        for w in (self._i_num, self._i_title, self._i_part, self._i_rev,
                  self._i_proj, self._i_cat, self._i_status, self._i_type,
                  self._i_created, self._i_mod, self._i_tags):
            w.setText("")
        self._i_desc.clear()
        self._att_list.clear()
        self._btn_add_att.setEnabled(False)
        self._btn_del_att.setEnabled(False)
        self._btn_open_att.setEnabled(False)

    def _load_attachments(self):
        self._att_list.clear()
        if self._drawing_id is None:
            return
        for a in self.db.get_attachments(self._drawing_id):
            li = QListWidgetItem(f"  {a['filename']}  ({(a['file_size'] or 0)//1024} KB)")
            li.setData(Qt.ItemDataRole.UserRole, a["id"])
            li.setData(Qt.ItemDataRole.UserRole + 1, a["file_path"])
            self._att_list.addItem(li)

    def _add_attachment(self):
        if self._drawing_id is None:
            return
        dlg = AttachmentDialog(self)
        if dlg.exec():
            v = dlg.values()
            try:
                self.db.add_attachment(self._drawing_id, v["file_path"], v["description"])
                self._load_attachments()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_attachment(self):
        li = self._att_list.currentItem()
        if not li:
            return
        ok = QMessageBox.question(self, "Confirm", "Delete this attachment?")
        if ok == QMessageBox.StandardButton.Yes:
            self.db.delete_attachment(li.data(Qt.ItemDataRole.UserRole))
            self._load_attachments()

    def _open_attachment(self):
        li = self._att_list.currentItem()
        if not li:
            return
        p = Path(li.data(Qt.ItemDataRole.UserRole + 1))
        if p.exists():
            os.startfile(str(p))
        else:
            QMessageBox.warning(self, "Not Found", f"File not found:\n{p}")


# ================================================================== #
#  DRAWINGS PANEL (list + detail)                                      #
# ================================================================== #
class DrawingsPanel(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._rows: list = []          # current list rows
        self._selected_id: int | None = None
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- top toolbar ----
        bar = QFrame()
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"background:{C_SURFACE};border-bottom:1px solid {C_BORDER};")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(12, 0, 12, 0)
        bar_lay.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search drawings…")
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self._do_search)

        self._flt_proj = QComboBox(); self._flt_proj.setFixedWidth(140)
        self._flt_cat  = QComboBox(); self._flt_cat.setFixedWidth(130)
        self._flt_status = QComboBox(); self._flt_status.setFixedWidth(110)
        self._flt_type   = QComboBox(); self._flt_type.setFixedWidth(90)

        for combo in (self._flt_proj, self._flt_cat, self._flt_status, self._flt_type):
            combo.currentIndexChanged.connect(self._do_search)

        self._btn_add  = QPushButton("＋ Add Drawing")
        self._btn_add.setStyleSheet(
            f"background:{C_ACCENT};color:{C_SIDEBAR};font-weight:bold;"
            "border:none;border-radius:5px;padding:5px 14px;"
        )
        self._btn_add.clicked.connect(self._add_drawing)

        bar_lay.addWidget(QLabel("Search:"))
        bar_lay.addWidget(self._search)
        bar_lay.addWidget(QLabel("Project:"))
        bar_lay.addWidget(self._flt_proj)
        bar_lay.addWidget(QLabel("Category:"))
        bar_lay.addWidget(self._flt_cat)
        bar_lay.addWidget(QLabel("Status:"))
        bar_lay.addWidget(self._flt_status)
        bar_lay.addWidget(QLabel("Type:"))
        bar_lay.addWidget(self._flt_type)
        bar_lay.addStretch()
        bar_lay.addWidget(self._btn_add)

        root.addWidget(bar)

        # ---- main splitter ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- drawing list ----
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Drawing #", "Title", "Rev", "Category", "Status", "Type", "Modified"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.setStyleSheet(
            f"QTableWidget{{background:{C_SURFACE};selection-background-color:{C_SURFACE2};}}"
        )
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._open_external)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)

        # action buttons below list
        act_bar = QHBoxLayout()
        act_bar.setContentsMargins(6, 4, 6, 4)
        self._btn_edit    = QPushButton("Edit")
        self._btn_version = QPushButton("New Version")
        self._btn_history = QPushButton("History")
        self._btn_del     = QPushButton("Delete")
        self._btn_export  = QPushButton("Export ZIP")

        for b in (self._btn_edit, self._btn_version, self._btn_history,
                  self._btn_del, self._btn_export):
            b.setEnabled(False)
            act_bar.addWidget(b)
        act_bar.addStretch()

        self._btn_edit.clicked.connect(self._edit_drawing)
        self._btn_version.clicked.connect(self._new_version)
        self._btn_history.clicked.connect(self._show_history)
        self._btn_del.clicked.connect(self._delete_drawing)
        self._btn_export.clicked.connect(self._export_drawing)

        left_lay.addWidget(self._table)
        left_lay.addLayout(act_bar)

        # ---- detail panel ----
        self._detail = DrawingDetailPanel(self.db)

        splitter.addWidget(left)
        splitter.addWidget(self._detail)
        splitter.setSizes([520, 480])

        root.addWidget(splitter)

    # ------------------------------------------------------------------ #
    #  Filter combos population                                           #
    # ------------------------------------------------------------------ #
    def _populate_filters(self):
        self._flt_proj.blockSignals(True)
        self._flt_cat.blockSignals(True)
        self._flt_status.blockSignals(True)
        self._flt_type.blockSignals(True)

        self._flt_proj.clear()
        self._flt_proj.addItem("All Projects", None)
        for p in self.db.get_projects():
            self._flt_proj.addItem(p["name"], p["id"])

        self._flt_cat.clear()
        self._flt_cat.addItem("All Categories", None)
        for c in self.db.get_categories():
            self._flt_cat.addItem(c["name"], c["id"])

        self._flt_status.clear()
        self._flt_status.addItem("All Statuses", None)
        for s in ("Draft", "Released", "Obsolete"):
            self._flt_status.addItem(s, s)

        self._flt_type.clear()
        self._flt_type.addItem("All Types", None)
        seen: set = set()
        for r in self.db.get_all_drawings():
            ft = (r["file_type"] or "").upper()
            if ft and ft not in seen:
                seen.add(ft)
                self._flt_type.addItem(ft, ft.lower())

        self._flt_proj.blockSignals(False)
        self._flt_cat.blockSignals(False)
        self._flt_status.blockSignals(False)
        self._flt_type.blockSignals(False)

    # ------------------------------------------------------------------ #
    #  Refresh / search                                                    #
    # ------------------------------------------------------------------ #
    def refresh(self):
        self._populate_filters()
        self._do_search()

    def _do_search(self):
        q          = self._search.text().strip()
        proj_id    = self._flt_proj.currentData()
        cat_id     = self._flt_cat.currentData()
        status     = self._flt_status.currentData()
        file_type  = self._flt_type.currentData()

        self._rows = self.db.search(
            query=q,
            project_id=proj_id,
            category_id=cat_id,
            status=status,
            file_type=file_type,
        )
        self._populate_table(self._rows)

    def _populate_table(self, rows):
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            status = row["status"] or "Draft"
            col    = STATUS_COLORS.get(status, C_SUB)

            def _cell(text):
                item = QTableWidgetItem(str(text or ""))
                item.setForeground(QColor(C_TEXT))
                return item

            self._table.setItem(r, 0, _cell(row["drawing_number"]))
            self._table.setItem(r, 1, _cell(row["title"]))
            self._table.setItem(r, 2, _cell(row["current_revision"]))
            self._table.setItem(r, 3, _cell(row["category_name"] or ""))
            status_item = _cell(status)
            status_item.setForeground(QColor(col))
            self._table.setItem(r, 4, status_item)
            self._table.setItem(r, 5, _cell((row["file_type"] or "").upper()))
            self._table.setItem(r, 6, _cell((row["modified_at"] or "")[:10]))
            self._table.setRowHeight(r, 26)

        self._table.resizeColumnToContents(0)
        self._table.resizeColumnToContents(2)
        self._table.resizeColumnToContents(4)
        self._table.resizeColumnToContents(5)
        self._table.resizeColumnToContents(6)

    # ------------------------------------------------------------------ #
    #  Selection                                                           #
    # ------------------------------------------------------------------ #
    def _on_selection_changed(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._rows):
            self._selected_id = None
            self._detail.clear()
            self._set_action_btns(False)
            return
        self._selected_id = self._rows[row]["id"]
        self._detail.load_drawing(self._selected_id)
        self._set_action_btns(True)

    def _set_action_btns(self, yes: bool):
        for b in (self._btn_edit, self._btn_version, self._btn_history,
                  self._btn_del, self._btn_export):
            b.setEnabled(yes)

    # ------------------------------------------------------------------ #
    #  Actions                                                             #
    # ------------------------------------------------------------------ #
    def _add_drawing(self):
        dlg = AddDrawingDialog(self.db, self)
        if dlg.exec():
            v = dlg.values()
            try:
                self.db.add_drawing(**v)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _edit_drawing(self):
        if self._selected_id is None:
            return
        d = dict(self.db.get_drawing(self._selected_id))
        dlg = EditDrawingDialog(self.db, d, self)
        if dlg.exec():
            v = dlg.values()
            try:
                self.db.update_drawing(self._selected_id, **v)
                self._detail.load_drawing(self._selected_id)
                self._do_search()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _new_version(self):
        if self._selected_id is None:
            return
        d = self.db.get_drawing(self._selected_id)
        dlg = NewVersionDialog(self, d["current_revision"] or "A")
        if dlg.exec():
            v = dlg.values()
            try:
                self.db.add_version(
                    self._selected_id, v["file_path"], v["revision"], v["change_note"]
                )
                self._detail.load_drawing(self._selected_id)
                self._do_search()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _show_history(self):
        if self._selected_id is None:
            return
        d = self.db.get_drawing(self._selected_id)
        dlg = VersionHistoryDialog(self.db, self._selected_id, d["drawing_number"], self)
        if dlg.exec():
            self._detail.load_drawing(self._selected_id)
            self._do_search()

    def _delete_drawing(self):
        if self._selected_id is None:
            return
        d = self.db.get_drawing(self._selected_id)
        ok = QMessageBox.question(
            self, "Confirm Delete",
            f"Permanently delete '{d['drawing_number']} – {d['title']}'?\n"
            "This will remove all versions and attachments.",
        )
        if ok == QMessageBox.StandardButton.Yes:
            self.db.delete_drawing(self._selected_id)
            self._selected_id = None
            self._detail.clear()
            self.refresh()

    def _export_drawing(self):
        if self._selected_id is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Drawing ZIP", "", "ZIP files (*.zip)"
        )
        if path:
            try:
                out = self.db.export_to_zip([self._selected_id], path)
                QMessageBox.information(self, "Exported", f"Saved to:\n{out}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _open_external(self, idx):
        row = idx.row()
        if row < 0 or row >= len(self._rows):
            return
        d = self.db.get_drawing(self._rows[row]["id"])
        fp = d["current_file_path"] if d else None
        if fp and Path(fp).exists():
            os.startfile(str(fp))
        else:
            QMessageBox.warning(self, "Not Found", "File not found on disk.")

    def _context_menu(self, pos):
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        self._table.selectRow(row)
        menu = QMenu(self)
        menu.addAction("Open (external)").triggered.connect(lambda: self._open_external(self._table.currentIndex()))
        menu.addAction("Edit").triggered.connect(self._edit_drawing)
        menu.addAction("New Version").triggered.connect(self._new_version)
        menu.addAction("Version History").triggered.connect(self._show_history)
        menu.addSeparator()
        menu.addAction("Export ZIP").triggered.connect(self._export_drawing)
        menu.addSeparator()
        menu.addAction("Delete").triggered.connect(self._delete_drawing)
        menu.exec(self._table.viewport().mapToGlobal(pos))


# ================================================================== #
#  SETTINGS PANEL                                                      #
# ================================================================== #
class SettingsPanel(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Settings & Management")
        title.setStyleSheet(f"font-size:22px;font-weight:bold;color:{C_TEXT};")
        root.addWidget(title)

        # Projects / Categories management
        mgmt = QHBoxLayout()
        btn_proj = QPushButton("Manage Projects")
        btn_cat  = QPushButton("Manage Categories")
        btn_proj.setFixedWidth(180)
        btn_cat.setFixedWidth(180)
        btn_proj.clicked.connect(lambda: ManageListDialog(self.db, "project", self).exec())
        btn_cat.clicked.connect( lambda: ManageListDialog(self.db, "category", self).exec())
        mgmt.addWidget(btn_proj)
        mgmt.addWidget(btn_cat)
        mgmt.addStretch()
        root.addLayout(mgmt)

        # Backup
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{C_BORDER};")
        root.addWidget(sep)

        root.addWidget(QLabel("Backup & Export"))
        bk_row = QHBoxLayout()
        self._bk_path = QLineEdit()
        self._bk_path.setPlaceholderText("Backup destination folder…")
        btn_bk_browse = QPushButton("Browse")
        btn_bk_browse.setFixedWidth(72)
        btn_bk_run    = QPushButton("Run Backup")
        btn_bk_browse.clicked.connect(self._browse_backup)
        btn_bk_run.clicked.connect(self._run_backup)
        bk_row.addWidget(self._bk_path)
        bk_row.addWidget(btn_bk_browse)
        bk_row.addWidget(btn_bk_run)
        root.addLayout(bk_row)

        # Export all
        exp_row = QHBoxLayout()
        btn_exp_all = QPushButton("Export All Drawings to ZIP")
        btn_exp_all.clicked.connect(self._export_all)
        exp_row.addWidget(btn_exp_all)
        exp_row.addStretch()
        root.addLayout(exp_row)

        root.addStretch()

    def _browse_backup(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
        if folder:
            self._bk_path.setText(folder)

    def _run_backup(self):
        folder = self._bk_path.text().strip()
        if not folder:
            QMessageBox.warning(self, "Validation", "Please choose a backup folder.")
            return
        try:
            out = self.db.backup_database(folder)
            QMessageBox.information(self, "Backup Complete", f"Backup saved to:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _export_all(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export All Drawings", "", "ZIP files (*.zip)"
        )
        if path:
            try:
                all_ids = [r["id"] for r in self.db.get_all_drawings()]
                out = self.db.export_to_zip(all_ids, path)
                QMessageBox.information(self, "Exported", f"Saved to:\n{out}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))


# ================================================================== #
#  MAIN WINDOW                                                         #
# ================================================================== #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.setWindowTitle("SolTerra Drawing Manager")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Sidebar ----
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"background:{C_SIDEBAR};border-right:1px solid {C_BORDER};")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(8, 16, 8, 16)
        sb_lay.setSpacing(4)

        logo = QLabel("SolTerra\nDrawing Mgr")
        logo.setStyleSheet(
            f"color:{C_ACCENT};font-size:16px;font-weight:bold;"
            "padding-left:12px;padding-bottom:12px;"
        )
        sb_lay.addWidget(logo)

        self._nav_btns: list[QPushButton] = []
        nav_items = [
            ("🏠  Dashboard",  0),
            ("📄  Drawings",   1),
            ("⚙️   Settings",  2),
        ]
        for label, idx in nav_items:
            btn = _sidebar_btn(label)
            btn.clicked.connect(lambda _, i=idx: self._switch_panel(i))
            sb_lay.addWidget(btn)
            self._nav_btns.append(btn)

        sb_lay.addStretch()
        sb_lay.addWidget(QLabel(
            "v1.0  –  Local only",
            alignment=Qt.AlignmentFlag.AlignCenter,
        ))

        # ---- Content stack ----
        self._stack = QStackedWidget()
        self._dash     = DashboardPanel(self.db)
        self._drawings = DrawingsPanel(self.db)
        self._settings = SettingsPanel(self.db)

        self._stack.addWidget(self._dash)
        self._stack.addWidget(self._drawings)
        self._stack.addWidget(self._settings)

        root.addWidget(sidebar)
        root.addWidget(self._stack)

        self._switch_panel(0)

    def _switch_panel(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        if idx == 0:
            self._dash.refresh()
        elif idx == 1:
            self._drawings.refresh()
