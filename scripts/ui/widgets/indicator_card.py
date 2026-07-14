"""核心指标卡片组件

用于展示关键业务指标，包含指标名称、当前数值、环比/同比变化趋势、状态指示色等元素
"""

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtGui import QFont, QColor, QPixmap, QPainter, QPen
from PyQt6.QtCore import Qt, QSize


class IndicatorCard(QFrame):
    """
    核心指标卡片组件
    
    展示关键业务指标，包含：
    - 指标名称
    - 当前数值
    - 单位
    - 环比/同比变化趋势及百分比
    - 状态指示色
    """

    STATUS_NORMAL = "normal"
    STATUS_WARNING = "warning"
    STATUS_DANGER = "danger"

    TREND_UP = "up"
    TREND_DOWN = "down"
    TREND_STABLE = "stable"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._indicator_name = ""
        self._value = 0.0
        self._unit = ""
        self._trend_value = 0.0
        self._trend_type = self.TREND_STABLE
        self._trend_label = "环比"
        self._status = self.STATUS_NORMAL
        
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setObjectName("card_frame")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(8)
        
        # 顶部：指标名称和状态标签
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.name_label = QLabel(self._indicator_name)
        self.name_label.setObjectName("title_label")
        top_layout.addWidget(self.name_label)
        
        self.status_label = QLabel()
        self.status_label.setFixedWidth(50)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.status_label)
        
        top_layout.addStretch(1)
        main_layout.addLayout(top_layout)
        
        # 中部：数值和单位
        value_layout = QHBoxLayout()
        value_layout.setSpacing(4)
        value_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.value_label = QLabel("0")
        self.value_label.setObjectName("value_label")
        value_layout.addWidget(self.value_label)
        
        self.unit_label = QLabel(self._unit)
        self.unit_label.setObjectName("unit_label")
        value_layout.addWidget(self.unit_label)
        
        main_layout.addLayout(value_layout)
        
        # 底部：趋势指示
        trend_layout = QHBoxLayout()
        trend_layout.setSpacing(4)
        trend_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.trend_icon = QLabel()
        self.trend_icon.setFixedSize(20, 20)
        trend_layout.addWidget(self.trend_icon)
        
        self.trend_label = QLabel()
        self.trend_label.setObjectName("trend_stable")
        trend_layout.addWidget(self.trend_label)
        
        main_layout.addLayout(trend_layout)

    def set_indicator_name(self, name):
        """设置指标名称"""
        self._indicator_name = name
        self.name_label.setText(name)

    def set_value(self, value, decimals=1):
        """设置数值"""
        self._value = value
        format_str = f"{{:.{decimals}f}}"
        self.value_label.setText(format_str.format(value))

    def set_unit(self, unit):
        """设置单位"""
        self._unit = unit
        self.unit_label.setText(unit)

    def set_trend(self, value, trend_type=TREND_STABLE, label="环比"):
        """设置趋势信息"""
        self._trend_value = value
        self._trend_type = trend_type
        self._trend_label = label
        
        if trend_type == self.TREND_UP:
            self.trend_label.setObjectName("trend_up")
            self.trend_label.setText(f"{label} ↑ {abs(value):.1f}%")
            self._draw_trend_icon("up")
        elif trend_type == self.TREND_DOWN:
            self.trend_label.setObjectName("trend_down")
            self.trend_label.setText(f"{label} ↓ {abs(value):.1f}%")
            self._draw_trend_icon("down")
        else:
            self.trend_label.setObjectName("trend_stable")
            self.trend_label.setText(f"{label} — {abs(value):.1f}%")
            self._draw_trend_icon("stable")
        
        self.trend_label.setStyleSheet(self.trend_label.styleSheet())

    def set_status(self, status):
        """设置状态"""
        self._status = status
        
        if status == self.STATUS_NORMAL:
            self.status_label.setObjectName("status_normal")
            self.status_label.setText("正常")
        elif status == self.STATUS_WARNING:
            self.status_label.setObjectName("status_warning")
            self.status_label.setText("警告")
        elif status == self.STATUS_DANGER:
            self.status_label.setObjectName("status_danger")
            self.status_label.setText("危险")
        
        self.status_label.setStyleSheet(self.status_label.styleSheet())

    def _draw_trend_icon(self, trend_type):
        """绘制趋势图标"""
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if trend_type == "up":
            color = QColor("#4CAF50")
            painter.setPen(QPen(color, 2))
            painter.drawLine(5, 15, 10, 5)
            painter.drawLine(10, 5, 15, 15)
        elif trend_type == "down":
            color = QColor("#F44336")
            painter.setPen(QPen(color, 2))
            painter.drawLine(5, 5, 10, 15)
            painter.drawLine(10, 15, 15, 5)
        else:
            color = QColor("#78909C")
            painter.setPen(QPen(color, 2))
            painter.drawLine(5, 10, 15, 10)
        
        painter.end()
        self.trend_icon.setPixmap(pixmap)

    def update_card(self, name, value, unit, trend_value=0, trend_type=TREND_STABLE, 
                   status=STATUS_NORMAL, trend_label="环比", decimals=1):
        """更新卡片所有信息"""
        self.set_indicator_name(name)
        self.set_value(value, decimals)
        self.set_unit(unit)
        self.set_trend(trend_value, trend_type, trend_label)
        self.set_status(status)


class SmallIndicatorCard(QFrame):
    """
    小型指标卡片组件
    
    用于展示次要指标，布局紧凑
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._indicator_name = ""
        self._value = 0.0
        self._unit = ""
        
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setObjectName("card_frame")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(4)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.name_label = QLabel(self._indicator_name)
        self.name_label.setObjectName("title_label")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.name_label)
        
        value_layout = QHBoxLayout()
        value_layout.setSpacing(2)
        value_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.value_label = QLabel("0")
        self.value_label.setObjectName("value_label_small")
        value_layout.addWidget(self.value_label)
        
        self.unit_label = QLabel(self._unit)
        self.unit_label.setObjectName("unit_label")
        value_layout.addWidget(self.unit_label)
        
        main_layout.addLayout(value_layout)

    def update_card(self, name, value, unit, decimals=1):
        """更新卡片信息"""
        self._indicator_name = name
        self.name_label.setText(name)
        
        self._value = value
        format_str = f"{{:.{decimals}f}}"
        self.value_label.setText(format_str.format(value))
        
        self._unit = unit
        self.unit_label.setText(unit)
