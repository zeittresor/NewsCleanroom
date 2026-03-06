from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(16, 20, 28))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(235, 239, 247))
    palette.setColor(QPalette.ColorRole.Base, QColor(12, 16, 23))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(24, 29, 40))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(30, 35, 48))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(235, 239, 247))
    palette.setColor(QPalette.ColorRole.Text, QColor(232, 236, 244))
    palette.setColor(QPalette.ColorRole.Button, QColor(26, 31, 43))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(235, 239, 247))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(76, 118, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(150, 160, 178))
    app.setPalette(palette)
    app.setStyleSheet(
        """
        QWidget {
            font-family: Segoe UI, Arial, sans-serif;
            font-size: 10pt;
        }
        QMainWindow, QDialog {
            background: #10141c;
        }
        QGroupBox {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            margin-top: 10px;
            padding-top: 12px;
            background: #111823;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #dfe6f4;
            font-weight: 600;
        }
        QPushButton, QComboBox, QLineEdit, QListWidget, QTableWidget, QTextBrowser, QSpinBox {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            background: #121a26;
            color: #e7ebf3;
            padding: 6px 8px;
        }
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #1c2740, stop:1 #162033);
            padding: 8px 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            border: 1px solid rgba(139,180,255,0.5);
            background: #1a2640;
        }
        QPushButton:pressed {
            background: #13203a;
        }
        QCheckBox {
            spacing: 8px;
            color: #e7ebf3;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 5px;
            border: 1px solid rgba(255,255,255,0.18);
            background: #101722;
        }
        QCheckBox::indicator:checked {
            background: #4c76ff;
            border: 1px solid #7aa2ff;
        }
        QHeaderView::section {
            background: #151d2a;
            color: #dfe6f4;
            border: none;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding: 8px;
            font-weight: 600;
        }
        QTableWidget {
            gridline-color: rgba(255,255,255,0.06);
            selection-background-color: #263b73;
            selection-color: #ffffff;
        }
        QTextBrowser {
            background:
                qradialgradient(cx:0.2, cy:0.0, radius:0.9, fx:0.2, fy:0.0, stop:0 rgba(74,109,255,0.12), stop:1 rgba(12,16,23,1)),
                #0c1017;
            border-radius: 14px;
            padding: 8px;
        }
        QStatusBar {
            background: #0d1219;
            color: #cfd7e8;
        }
        QScrollBar:vertical {
            width: 12px;
            background: #0f1520;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #24324d;
            min-height: 30px;
            border-radius: 6px;
        }
        """
    )
