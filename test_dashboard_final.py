"""完整仪表盘测试脚本（最终版）"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, 
        QHBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea,
        QSizePolicy
    )
    from PyQt6.QtGui import QFont
    from PyQt6.QtCore import Qt, QTimer
    
    from ui.widgets.circular_progress import CircularProgressWidget
    from ui.widgets.indicator_card import IndicatorCard, SmallIndicatorCard
    
    app = QApplication(sys.argv)
    
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "ui", "resources", "styles.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    
    window = QMainWindow()
    window.setWindowTitle("HealthMan - 健康监测仪表盘")
    window.setGeometry(100, 100, 1200, 800)
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(20)
    
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    scroll_content = QWidget()
    scroll_layout = QVBoxLayout(scroll_content)
    scroll_layout.setSpacing(20)
    
    title_label = QLabel("健康监测仪表盘")
    title_label.setObjectName("section_title_label")
    scroll_layout.addWidget(title_label)
    
    top_row_layout = QHBoxLayout()
    top_row_layout.setSpacing(20)
    
    score_card = QFrame()
    score_card.setObjectName("score_card_frame")
    score_card.setMinimumWidth(280)
    score_card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    
    score_layout = QVBoxLayout(score_card)
    score_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    score_widget = CircularProgressWidget()
    score_layout.addWidget(score_widget)
    
    top_row_layout.addWidget(score_card)
    
    core_cards_layout = QVBoxLayout()
    core_cards_layout.setSpacing(16)
    
    row1_layout = QHBoxLayout()
    row1_layout.setSpacing(16)
    
    spo2_card = IndicatorCard()
    spo2_card.update_card(
        name="血氧饱和度(SpO₂)",
        value=98.5,
        unit="%",
        trend_value=0.8,
        trend_type=IndicatorCard.TREND_UP,
        status=IndicatorCard.STATUS_NORMAL
    )
    row1_layout.addWidget(spo2_card)
    
    heart_rate_card = IndicatorCard()
    heart_rate_card.update_card(
        name="心率",
        value=72,
        unit="BPM",
        trend_value=1.2,
        trend_type=IndicatorCard.TREND_UP,
        status=IndicatorCard.STATUS_NORMAL
    )
    row1_layout.addWidget(heart_rate_card)
    
    body_fat_card = IndicatorCard()
    body_fat_card.update_card(
        name="体脂率",
        value=18.2,
        unit="%",
        trend_value=2.5,
        trend_type=IndicatorCard.TREND_DOWN,
        status=IndicatorCard.STATUS_NORMAL
    )
    row1_layout.addWidget(body_fat_card)
    
    core_cards_layout.addLayout(row1_layout)
    
    row2_layout = QHBoxLayout()
    row2_layout.setSpacing(16)
    
    bmi_card = IndicatorCard()
    bmi_card.update_card(
        name="BMI",
        value=23.5,
        unit="",
        trend_value=0.5,
        trend_type=IndicatorCard.TREND_STABLE,
        status=IndicatorCard.STATUS_NORMAL
    )
    row2_layout.addWidget(bmi_card)
    
    pi_card = IndicatorCard()
    pi_card.update_card(
        name="灌注指数(PI)",
        value=2.3,
        unit="%",
        trend_value=1.5,
        trend_type=IndicatorCard.TREND_UP,
        status=IndicatorCard.STATUS_NORMAL
    )
    row2_layout.addWidget(pi_card)
    
    hrv_card = IndicatorCard()
    hrv_card.update_card(
        name="心率变异性(HRV)",
        value=45,
        unit="ms",
        trend_value=3.2,
        trend_type=IndicatorCard.TREND_UP,
        status=IndicatorCard.STATUS_NORMAL
    )
    row2_layout.addWidget(hrv_card)
    
    core_cards_layout.addLayout(row2_layout)
    
    top_row_layout.addLayout(core_cards_layout)
    top_row_layout.setStretch(1, 2)
    
    scroll_layout.addLayout(top_row_layout)
    
    body_composition_frame = QFrame()
    body_composition_frame.setObjectName("card_frame")
    
    bc_layout = QVBoxLayout(body_composition_frame)
    
    bc_title = QLabel("体成分指标")
    bc_title.setObjectName("title_label")
    bc_layout.addWidget(bc_title)
    
    bc_grid = QGridLayout()
    bc_grid.setSpacing(12)
    
    muscle_card = SmallIndicatorCard()
    muscle_card.update_card("肌肉量", 42.5, "kg")
    bc_grid.addWidget(muscle_card, 0, 0)
    
    skeletal_card = SmallIndicatorCard()
    skeletal_card.update_card("骨骼肌量", 28.3, "kg")
    bc_grid.addWidget(skeletal_card, 0, 1)
    
    bone_card = SmallIndicatorCard()
    bone_card.update_card("骨量", 3.8, "kg")
    bc_grid.addWidget(bone_card, 0, 2)
    
    water_card = SmallIndicatorCard()
    water_card.update_card("水分率", 58.5, "%")
    bc_grid.addWidget(water_card, 1, 0)
    
    protein_card = SmallIndicatorCard()
    protein_card.update_card("蛋白质率", 16.2, "%")
    bc_grid.addWidget(protein_card, 1, 1)
    
    bmr_card = SmallIndicatorCard()
    bmr_card.update_card("基础代谢", 1580, "Kcal")
    bc_grid.addWidget(bmr_card, 1, 2)
    
    bc_layout.addLayout(bc_grid)
    scroll_layout.addWidget(body_composition_frame)
    
    scroll_area.setWidget(scroll_content)
    main_layout.addWidget(scroll_area)
    
    def update_data():
        score_widget.value = 85
    
    QTimer.singleShot(500, update_data)
    
    window.show()
    
    sys.exit(app.exec())
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
