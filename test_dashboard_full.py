"""完整仪表盘测试脚本"""
import sys
import os

# 添加scripts目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))

try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
    from PyQt6.QtGui import QFont
    from PyQt6.QtCore import Qt
    
    # 导入仪表盘组件
    from ui.widgets.circular_progress import CircularProgressWidget
    from ui.widgets.indicator_card import IndicatorCard, SmallIndicatorCard
    
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 加载样式表
    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "ui", "resources", "styles.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
            print("样式表加载成功")
    
    # 创建主窗口
    window = QMainWindow()
    window.setWindowTitle("HealthMan - 健康监测仪表盘")
    window.setGeometry(100, 100, 1200, 800)
    
    # 创建中央组件
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(20)
    
    # 测试环形进度图
    print("创建环形进度图...")
    score_widget = CircularProgressWidget()
    score_widget.setFixedSize(300, 300)
    layout.addWidget(score_widget)
    
    # 测试核心指标卡片
    print("创建核心指标卡片...")
    card = IndicatorCard()
    card.update_card(
        name="血氧饱和度(SpO₂)",
        value=98.5,
        unit="%",
        trend_value=0.8,
        trend_type=IndicatorCard.TREND_UP,
        status=IndicatorCard.STATUS_NORMAL
    )
    layout.addWidget(card)
    
    # 测试小型指标卡片
    print("创建小型指标卡片...")
    small_card = SmallIndicatorCard()
    small_card.update_card("肌肉量", 42.5, "kg")
    layout.addWidget(small_card)
    
    # 启动数值动画
    print("启动数值动画...")
    score_widget.value = 85
    
    window.show()
    print("窗口显示成功")
    
    sys.exit(app.exec())
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
