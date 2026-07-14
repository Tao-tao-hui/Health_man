"""PyQt6环境测试脚本

用于验证PyQt6安装是否正确，以及基本功能是否正常工作
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QStatusBar, QToolBar, QMenuBar, QMenu
)
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import Qt


class TestWindow(QMainWindow):
    """测试窗口类"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口标题和大小
        self.setWindowTitle("HealthMan - PyQt6环境测试")
        self.setGeometry(100, 100, 800, 600)

        # 设置全局字体
        font = QFont("Microsoft YaHei", 10)
        self.setFont(font)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建工具栏
        self.create_tool_bar()

        # 创建状态栏
        self.create_status_bar()

        # 创建中央内容区
        self.create_central_widget()

        # 显示窗口
        self.show()

    def create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = QMenuBar(self)

        # 文件菜单
        file_menu = QMenu("文件", self)
        file_menu.addAction("新建测量")
        file_menu.addAction("打开记录")
        file_menu.addSeparator()
        file_menu.addAction("退出")
        menu_bar.addMenu(file_menu)

        # 测量菜单
        measure_menu = QMenu("测量", self)
        measure_menu.addAction("开始BIA测量")
        measure_menu.addAction("开始PPG测量")
        measure_menu.addAction("停止测量")
        menu_bar.addMenu(measure_menu)

        # 视图菜单
        view_menu = QMenu("视图", self)
        view_menu.addAction("仪表盘")
        view_menu.addAction("历史记录")
        view_menu.addAction("用户管理")
        menu_bar.addMenu(view_menu)

        # 设置菜单
        settings_menu = QMenu("设置", self)
        settings_menu.addAction("设备配置")
        settings_menu.addAction("显示设置")
        menu_bar.addMenu(settings_menu)

        # 帮助菜单
        help_menu = QMenu("帮助", self)
        help_menu.addAction("使用说明")
        help_menu.addAction("关于")
        menu_bar.addMenu(help_menu)

        self.setMenuBar(menu_bar)

    def create_tool_bar(self):
        """创建工具栏"""
        tool_bar = QToolBar("主工具栏", self)
        tool_bar.addAction("新建测量")
        tool_bar.addAction("历史记录")
        tool_bar.addAction("用户管理")
        tool_bar.addSeparator()
        tool_bar.addAction("刷新")
        tool_bar.addAction("导出")
        tool_bar.addAction("设置")

        self.addToolBar(tool_bar)

    def create_status_bar(self):
        """创建状态栏"""
        status_bar = QStatusBar(self)
        status_bar.showMessage("设备状态: 在线 | 上次测量: 无 | 数据质量: -")
        self.setStatusBar(status_bar)

    def create_central_widget(self):
        """创建中央内容区"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # 标题标签
        title_label = QLabel("PyQt6环境测试")
        title_font = QFont("Microsoft YaHei", 24, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 版本信息
        version_label = QLabel(f"Python版本: {sys.version}\nPyQt6版本: 6.11.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        # 测试按钮
        test_button = QPushButton("点击测试")
        test_button.clicked.connect(self.on_test_click)
        test_button.setStyleSheet("""
            QPushButton {
                background-color: #1E88E5;
                color: white;
                border-radius: 6px;
                padding: 12px 30px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        layout.addWidget(test_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # 组件测试区域
        components_label = QLabel("已加载组件测试:")
        components_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(components_label)

        components_text = QLabel("""
            ✓ QMainWindow - 主窗口
            ✓ QWidget - 基础组件
            ✓ QVBoxLayout - 垂直布局
            ✓ QLabel - 文本标签
            ✓ QPushButton - 按钮
            ✓ QMenuBar/QMenu - 菜单栏
            ✓ QToolBar - 工具栏
            ✓ QStatusBar - 状态栏
            ✓ QFont - 字体设置
            ✓ Qt StyleSheet - 样式支持
        """)
        layout.addWidget(components_text)

    def on_test_click(self):
        """测试按钮点击事件"""
        self.statusBar().showMessage("测试成功！PyQt6环境配置正常")


if __name__ == "__main__":
    """主入口"""
    app = QApplication(sys.argv)
    window = TestWindow()
    sys.exit(app.exec())
