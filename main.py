"""
main.py - Entry point for SolTerra Drawing Manager
Run with: python main.py
"""
import sys
import os

# Ensure the app's working directory is always the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui import MainWindow, DARK_STYLE


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SolTerra Drawing Manager")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
