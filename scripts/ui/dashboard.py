"""仪表盘主页面模块

整合综合评分环形图、核心指标卡片等组件，实现响应式布局
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

from widgets.circular_progress import CircularProgressWidget
from widgets.indicator_card import IndicatorCard, SmallIndicatorCard


class DashboardWidget(QWidget):
    """
    仪表盘主页面
    
    包含以下核心组件：
    1. 综合评分环形图
    2. 核心指标卡片（6个）
    3. 体成分指标网格
    4. 风险预警列表
    5. 健康建议区域
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data_loaded = False
        self.init_ui()
        self.load_demo_data()

    def init_ui(self):
        """初始化UI布局"""
        # 设置全局字体
        font = QFont("Microsoft YaHei", 10)
        self.setFont(font)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        
        # 第一行：标题区域
        title_label = QLabel("健康监测仪表盘")
        title_label.setObjectName("section_title_label")
        scroll_layout.addWidget(title_label)
        
        # 第二行：综合评分卡片 + 核心指标卡片
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(20)
        
        # 综合评分卡片
        score_card = QFrame()
        score_card.setObjectName("score_card_frame")
        score_card.setMinimumWidth(280)
        score_card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        score_layout = QVBoxLayout(score_card)
        score_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.score_widget = CircularProgressWidget()
        score_layout.addWidget(self.score_widget)
        
        top_row_layout.addWidget(score_card)
        
        # 核心指标卡片（3个一行）
        core_cards_layout = QVBoxLayout()
        core_cards_layout.setSpacing(16)
        
        # 第一排核心指标
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(16)
        
        self.spo2_card = IndicatorCard()
        row1_layout.addWidget(self.spo2_card)
        
        self.heart_rate_card = IndicatorCard()
        row1_layout.addWidget(self.heart_rate_card)
        
        self.body_fat_card = IndicatorCard()
        row1_layout.addWidget(self.body_fat_card)
        
        core_cards_layout.addLayout(row1_layout)
        
        # 第二排核心指标
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(16)
        
        self.bmi_card = IndicatorCard()
        row2_layout.addWidget(self.bmi_card)
        
        self.pi_card = IndicatorCard()
        row2_layout.addWidget(self.pi_card)
        
        self.hrv_card = IndicatorCard()
        row2_layout.addWidget(self.hrv_card)
        
        core_cards_layout.addLayout(row2_layout)
        
        top_row_layout.addLayout(core_cards_layout)
        top_row_layout.setStretch(1, 2)
        
        scroll_layout.addLayout(top_row_layout)
        
        # 第三行：体成分指标网格
        body_composition_frame = QFrame()
        body_composition_frame.setObjectName("card_frame")
        
        bc_layout = QVBoxLayout(body_composition_frame)
        
        bc_title = QLabel("体成分指标")
        bc_title.setObjectName("title_label")
        bc_layout.addWidget(bc_title)
        
        bc_grid = QGridLayout()
        bc_grid.setSpacing(12)
        
        self.muscle_card = SmallIndicatorCard()
        bc_grid.addWidget(self.muscle_card, 0, 0)
        
        self.skeletal_card = SmallIndicatorCard()
        bc_grid.addWidget(self.skeletal_card, 0, 1)
        
        self.bone_card = SmallIndicatorCard()
        bc_grid.addWidget(self.bone_card, 0, 2)
        
        self.water_card = SmallIndicatorCard()
        bc_grid.addWidget(self.water_card, 1, 0)
        
        self.protein_card = SmallIndicatorCard()
        bc_grid.addWidget(self.protein_card, 1, 1)
        
        self.bmr_card = SmallIndicatorCard()
        bc_grid.addWidget(self.bmr_card, 1, 2)
        
        bc_layout.addLayout(bc_grid)
        scroll_layout.addWidget(body_composition_frame)
        
        # 第四行：风险预警 + 健康建议
        bottom_row_layout = QHBoxLayout()
        bottom_row_layout.setSpacing(20)
        
        # 风险预警区域
        alerts_frame = QFrame()
        alerts_frame.setObjectName("card_frame")
        alerts_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        alerts_layout = QVBoxLayout(alerts_frame)
        
        alerts_title = QLabel("风险预警")
        alerts_title.setObjectName("title_label")
        alerts_layout.addWidget(alerts_title)
        
        self.alerts_list = QWidget()
        self.alerts_layout = QVBoxLayout(self.alerts_list)
        self.alerts_layout.setSpacing(8)
        
        alerts_layout.addWidget(self.alerts_list)
        bottom_row_layout.addWidget(alerts_frame)
        bottom_row_layout.setStretch(0, 1)
        
        # 健康建议区域
        advice_frame = QFrame()
        advice_frame.setObjectName("card_frame")
        advice_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        advice_layout = QVBoxLayout(advice_frame)
        
        advice_title = QLabel("健康建议")
        advice_title.setObjectName("title_label")
        advice_layout.addWidget(advice_title)
        
        self.advice_text = QLabel()
        self.advice_text.setWordWrap(True)
        self.advice_text.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
                color: #2E7D32;
                background-color: #E8F5E9;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        advice_layout.addWidget(self.advice_text)
        bottom_row_layout.addWidget(advice_frame)
        bottom_row_layout.setStretch(1, 1)
        
        scroll_layout.addLayout(bottom_row_layout)
        
        # 底部提示
        hint_label = QLabel("提示：本评估结果为保健级参考值，不可用于临床诊断。如有不适请咨询医生。")
        hint_label.setObjectName("hint_text")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(hint_label)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def load_demo_data(self):
        """加载演示数据"""
        QTimer.singleShot(500, self._update_demo_data)

    def _update_demo_data(self):
        """更新演示数据"""
        # 更新综合评分（带动画）
        self.score_widget.value = 85
        
        # 更新核心指标卡片
        self.spo2_card.update_card(
            name="血氧饱和度(SpO₂)",
            value=98.5,
            unit="%",
            trend_value=0.8,
            trend_type=IndicatorCard.TREND_UP,
            status=IndicatorCard.STATUS_NORMAL
        )
        
        self.heart_rate_card.update_card(
            name="心率",
            value=72,
            unit="BPM",
            trend_value=1.2,
            trend_type=IndicatorCard.TREND_UP,
            status=IndicatorCard.STATUS_NORMAL
        )
        
        self.body_fat_card.update_card(
            name="体脂率",
            value=18.2,
            unit="%",
            trend_value=2.5,
            trend_type=IndicatorCard.TREND_DOWN,
            status=IndicatorCard.STATUS_NORMAL
        )
        
        self.bmi_card.update_card(
            name="BMI",
            value=23.5,
            unit="",
            trend_value=0.5,
            trend_type=IndicatorCard.TREND_STABLE,
            status=IndicatorCard.STATUS_NORMAL
        )
        
        self.pi_card.update_card(
            name="灌注指数(PI)",
            value=2.3,
            unit="%",
            trend_value=1.5,
            trend_type=IndicatorCard.TREND_UP,
            status=IndicatorCard.STATUS_NORMAL
        )
        
        self.hrv_card.update_card(
            name="心率变异性(HRV)",
            value=45,
            unit="ms",
            trend_value=3.2,
            trend_type=IndicatorCard.TREND_UP,
            status=IndicatorCard.STATUS_NORMAL
        )
        
        # 更新体成分指标
        self.muscle_card.update_card("肌肉量", 42.5, "kg")
        self.skeletal_card.update_card("骨骼肌量", 28.3, "kg")
        self.bone_card.update_card("骨量", 3.8, "kg")
        self.water_card.update_card("水分率", 58.5, "%")
        self.protein_card.update_card("蛋白质率", 16.2, "%")
        self.bmr_card.update_card("基础代谢", 1580, "Kcal")
        
        # 更新风险预警
        self._update_alerts([
            {
                "name": "体脂率偏高",
                "severity": "medium",
                "action": "建议控制饮食、增加运动",
                "evidence_level": "B"
            },
            {
                "name": "心率略高于平均水平",
                "severity": "low",
                "action": "建议保持规律作息，适当放松",
                "evidence_level": "C"
            }
        ])
        
        # 更新健康建议
        self.advice_text.setText("""
1. 您的体脂率为18.2%，处于正常范围，请继续保持健康的生活方式。
2. 心率72 BPM，属于正常范围，建议保持每周3-5次有氧运动。
3. 建议每天饮水量保持在1.5-2升，有助于维持身体水分平衡。
4. 注意饮食均衡，蛋白质摄入量建议保持在体重的1.2-1.5倍。
        """)
        
        self._data_loaded = True

    def _update_alerts(self, alerts):
        """更新风险预警列表"""
        # 清空现有预警
        while self.alerts_layout.count():
            child = self.alerts_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not alerts:
            no_alerts_label = QLabel("暂无风险预警")
            no_alerts_label.setStyleSheet("color: #78909C; font-size: 12px;")
            self.alerts_layout.addWidget(no_alerts_label)
            return
        
        for alert in alerts:
            alert_widget = QFrame()
            alert_widget.setStyleSheet("""
                QFrame {
                    background-color: #FFF3E0;
                    border-radius: 6px;
                    padding: 8px;
                }
            """)
            
            alert_layout = QVBoxLayout(alert_widget)
            alert_layout.setContentsMargins(8, 8, 8, 8)
            
            header_layout = QHBoxLayout()
            
            severity_label = QLabel(self._get_severity_text(alert["severity"]))
            severity_label.setStyleSheet(self._get_severity_style(alert["severity"]))
            header_layout.addWidget(severity_label)
            
            evidence_label = QLabel(f"证据等级: {alert['evidence_level']}")
            evidence_label.setStyleSheet("font-size: 11px; color: #78909C;")
            header_layout.addWidget(evidence_label)
            
            header_layout.addStretch(1)
            alert_layout.addLayout(header_layout)
            
            name_label = QLabel(alert["name"])
            name_label.setStyleSheet("font-weight: 600; color: #37474F;")
            alert_layout.addWidget(name_label)
            
            action_label = QLabel(alert["action"])
            action_label.setStyleSheet("font-size: 12px; color: #546E7A;")
            alert_layout.addWidget(action_label)
            
            self.alerts_layout.addWidget(alert_widget)

    def _get_severity_text(self, severity):
        """获取严重程度文本"""
        severity_map = {
            "high": "高风险",
            "medium": "中风险",
            "low": "低风险"
        }
        return severity_map.get(severity, "未知")

    def _get_severity_style(self, severity):
        """获取严重程度样式"""
        style_map = {
            "high": "background-color: #FFEBEE; color: #C62828; padding: 2px 8px; border-radius: 4px; font-size: 11px;",
            "medium": "background-color: #FFF3E0; color: #EF6C00; padding: 2px 8px; border-radius: 4px; font-size: 11px;",
            "low": "background-color: #E3F2FD; color: #1565C0; padding: 2px 8px; border-radius: 4px; font-size: 11px;"
        }
        return style_map.get(severity, "")

    def update_data(self, processed_data, assessment):
        """根据实际数据更新仪表盘"""
        if processed_data.overall_score is not None:
            self.score_widget.value = processed_data.overall_score
        
        if processed_data.spo2 is not None:
            status = self._determine_spo2_status(processed_data.spo2)
            self.spo2_card.update_card(
                name="血氧饱和度(SpO₂)",
                value=processed_data.spo2,
                unit="%",
                status=status
            )
        
        if processed_data.heart_rate is not None:
            status = self._determine_heart_rate_status(processed_data.heart_rate)
            self.heart_rate_card.update_card(
                name="心率",
                value=processed_data.heart_rate,
                unit="BPM",
                status=status
            )
        
        if processed_data.body_fat_rate is not None:
            status = self._determine_body_fat_status(processed_data.body_fat_rate)
            self.body_fat_card.update_card(
                name="体脂率",
                value=processed_data.body_fat_rate,
                unit="%",
                status=status
            )
        
        if processed_data.bmi is not None:
            status = self._determine_bmi_status(processed_data.bmi)
            self.bmi_card.update_card(
                name="BMI",
                value=processed_data.bmi,
                unit="",
                status=status
            )
        
        if assessment.alerts:
            self._update_alerts(assessment.alerts)
        
        if assessment.recommendations:
            self.advice_text.setText("\n".join(assessment.recommendations))

    def _determine_spo2_status(self, spo2):
        """确定血氧状态"""
        if spo2 >= 95:
            return IndicatorCard.STATUS_NORMAL
        elif spo2 >= 91:
            return IndicatorCard.STATUS_WARNING
        else:
            return IndicatorCard.STATUS_DANGER

    def _determine_heart_rate_status(self, hr):
        """确定心率状态"""
        if 60 <= hr <= 100:
            return IndicatorCard.STATUS_NORMAL
        elif 50 <= hr < 60 or 100 < hr <= 120:
            return IndicatorCard.STATUS_WARNING
        else:
            return IndicatorCard.STATUS_DANGER

    def _determine_body_fat_status(self, body_fat):
        """确定体脂率状态（简化判断）"""
        if 10 <= body_fat <= 25:
            return IndicatorCard.STATUS_NORMAL
        elif body_fat < 10:
            return IndicatorCard.STATUS_WARNING
        else:
            return IndicatorCard.STATUS_WARNING

    def _determine_bmi_status(self, bmi):
        """确定BMI状态"""
        if 18.5 <= bmi < 25:
            return IndicatorCard.STATUS_NORMAL
        elif 25 <= bmi < 30:
            return IndicatorCard.STATUS_WARNING
        else:
            return IndicatorCard.STATUS_DANGER


if __name__ == "__main__":
    """测试入口"""
    from PyQt6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    
    # 加载样式表
    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "styles.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    
    window = QMainWindow()
    window.setWindowTitle("HealthMan - 健康监测仪表盘")
    window.setGeometry(100, 100, 1200, 800)
    
    dashboard = DashboardWidget()
    window.setCentralWidget(dashboard)
    
    window.show()
    sys.exit(app.exec())
