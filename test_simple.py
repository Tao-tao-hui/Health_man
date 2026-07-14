"""简单测试脚本"""
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("简单测试")
window.setGeometry(100, 100, 400, 300)

layout = QVBoxLayout(window)
layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

label = QLabel("测试成功！")
font = QFont("Arial", 24)
label.setFont(font)
label.setAlignment(Qt.AlignmentFlag.AlignCenter)
layout.addWidget(label)

window.show()
sys.exit(app.exec())
