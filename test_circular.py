"""环形进度图组件测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))

try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
    from PyQt6.QtGui import QFont
    from PyQt6.QtCore import Qt
    
    from ui.widgets.circular_progress import CircularProgressWidget
    
    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("环形进度图测试")
    window.setGeometry(100, 100, 600, 500)
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    score_widget = CircularProgressWidget()
    score_widget.setFixedSize(300, 300)
    layout.addWidget(score_widget)
    
    btn = QPushButton("点击测试动画")
    def test_animation():
        score_widget.value = 78
    
    btn.clicked.connect(test_animation)
    layout.addWidget(btn)
    
    window.show()
    
    sys.exit(app.exec())
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
