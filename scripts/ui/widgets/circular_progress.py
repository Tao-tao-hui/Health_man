"""综合评分环形进度图组件

使用QPainter自定义绘制环形进度图，支持动态加载和数值更新动画效果
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve


class CircularProgressWidget(QWidget):
    """
    环形进度图组件
    
    用于展示综合健康评分，支持：
    - 数值动画效果
    - 动态加载
    - 评分等级显示
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_value = 0.0
        self._target_value = 0.0
        self._max_value = 100.0
        self._ring_width = 20
        self._animation_duration = 1500
        self._animation = None
        
        self.setMinimumSize(200, 200)
        
    def get_value(self):
        """获取当前显示值"""
        return self._current_value

    def set_value(self, value):
        """设置目标值并启动动画"""
        self._target_value = max(0.0, min(float(value), self._max_value))
        
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"current_value")
        self._animation.setDuration(self._animation_duration)
        self._animation.setStartValue(self._current_value)
        self._animation.setEndValue(self._target_value)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

    value = pyqtProperty(float, get_value, set_value)

    def get_current_value(self):
        """获取当前动画值"""
        return self._current_value

    def set_current_value(self, value):
        """设置当前值（用于动画）"""
        self._current_value = value
        self.update()

    current_value = pyqtProperty(float, get_current_value, set_current_value)

    def paintEvent(self, event):
        """绘制环形进度图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center_x = rect.center().x()
        center_y = rect.center().y()
        
        size = min(rect.width(), rect.height()) - 40
        radius = size / 2
        inner_radius = radius - self._ring_width
        
        # 绘制背景圆环
        painter.setPen(QPen(QColor("#E0E5EC"), self._ring_width, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(
            int(center_x - radius),
            int(center_y - radius),
            int(size),
            int(size),
            0,
            360 * 16
        )
        
        # 绘制进度圆环
        progress = self._current_value / self._max_value
        angle = int(progress * 360 * 16)
        
        # 根据分数设置颜色
        color = self._get_score_color(self._current_value)
        gradient_pen = QPen(color, self._ring_width, Qt.PenStyle.SolidLine)
        gradient_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(gradient_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        painter.drawArc(
            int(center_x - radius),
            int(center_y - radius),
            int(size),
            int(size),
            90 * 16,
            -angle
        )
        
        # 绘制内圆背景
        inner_brush = QBrush(QColor("#FFFFFF"))
        painter.setBrush(inner_brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            int(center_x - inner_radius),
            int(center_y - inner_radius),
            int(inner_radius * 2),
            int(inner_radius * 2)
        )
        
        # 绘制分数值
        score_font = QFont("Consolas", 48, QFont.Weight.Bold)
        painter.setFont(score_font)
        painter.setPen(QColor("#1A237E"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(self._current_value)}")
        
        # 绘制单位
        unit_font = QFont("Microsoft YaHei", 14)
        painter.setFont(unit_font)
        painter.setPen(QColor("#78909C"))
        painter.drawText(
            center_x - 40,
            center_y + 35,
            80,
            30,
            Qt.AlignmentFlag.AlignCenter,
            "综合评分"
        )
        
        # 绘制评分等级
        level_font = QFont("Microsoft YaHei", 14, QFont.Weight.Bold)
        painter.setFont(level_font)
        level_color, level_text = self._get_score_level(self._current_value)
        painter.setPen(level_color)
        painter.drawText(
            center_x - 50,
            center_y + 60,
            100,
            30,
            Qt.AlignmentFlag.AlignCenter,
            level_text
        )
        
        painter.end()

    def _get_score_color(self, score):
        """根据分数获取颜色"""
        if score >= 80:
            return QColor("#43A047")
        elif score >= 60:
            return QColor("#1E88E5")
        elif score >= 40:
            return QColor("#FB8C00")
        else:
            return QColor("#E53935")

    def _get_score_level(self, score):
        """根据分数获取等级"""
        if score >= 90:
            return QColor("#43A047"), "优秀"
        elif score >= 80:
            return QColor("#1E88E5"), "良好"
        elif score >= 60:
            return QColor("#FB8C00"), "中等"
        else:
            return QColor("#E53935"), "较差"

    def set_ring_width(self, width):
        """设置圆环宽度"""
        self._ring_width = width
        self.update()

    def set_animation_duration(self, duration):
        """设置动画持续时间"""
        self._animation_duration = duration

    def set_max_value(self, max_value):
        """设置最大值"""
        self._max_value = max_value
        self.update()
