from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QColorDialog, QDialogButtonBox, 
                             QLineEdit, QFrame)
from PyQt6.QtCore import Qt

class OptionsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.cfg_mgr = config_manager
        self.current_theme = self.cfg_mgr.get_theme()
        self.setWindowTitle("选项设置 (Options)")
        self.setMinimumWidth(500)
        
        # 暂存数据
        self.bg_color = self.current_theme["background_color"]
        self.text_color = self.current_theme["text_color"]
        self.font_size = self.current_theme["font_size"]
        self.bing_cookie = self.cfg_mgr.get_bing_cookie()

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        # 外观
        layout.addWidget(QLabel("<b>界面外观 (Appearance)</b>"))
        
        self.btn_bg = self.create_color_btn(self.bg_color, lambda: self.pick_color('bg'))
        layout.addLayout(self.create_row("窗口背景颜色:", self.btn_bg))
        
        self.btn_text = self.create_color_btn(self.text_color, lambda: self.pick_color('text'))
        layout.addLayout(self.create_row("主要文字颜色:", self.btn_text))
        
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("全局字体大小 (px):"))
        self.spin_font = QSpinBox()
        self.spin_font.setRange(10, 40)
        self.spin_font.setValue(self.font_size)
        font_layout.addWidget(self.spin_font)
        layout.addLayout(font_layout)
        
        # 搜索
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        layout.addWidget(QLabel("<b>联网搜索设置 (Search Settings)</b>"))
        layout.addWidget(QLabel("Bing Cookie (解决搜索结果不准/知乎聚合页的问题):"))
        self.cookie_input = QLineEdit()
        self.cookie_input.setPlaceholderText("在此粘贴 cn.bing.com 的 Cookie (MUID=...; ...)")
        self.cookie_input.setText(self.bing_cookie)
        layout.addWidget(self.cookie_input)
        
        layout.addStretch()
        
        # 底部按钮区
        btn_layout = QHBoxLayout()
        
        # 【恢复】恢复默认按钮
        reset_btn = QPushButton("恢复默认 (Reset Theme)")
        reset_btn.clicked.connect(self.restore_defaults)
        btn_layout.addWidget(reset_btn)
        
        btn_layout.addStretch()
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_all)
        buttons.rejected.connect(self.reject)
        btn_layout.addWidget(buttons)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def create_row(self, label, w):
        l = QHBoxLayout(); l.addWidget(QLabel(label)); l.addWidget(w)
        return l

    def create_color_btn(self, color, func):
        b = QPushButton(color)
        self.update_btn_style(b, color)
        b.clicked.connect(func)
        return b
        
    def update_btn_style(self, btn, color):
        btn.setText(color)
        btn.setStyleSheet(f"background-color: {color}; color: #888888; border: 1px solid #555;")

    def pick_color(self, target):
        c = QColorDialog.getColor(initial=Qt.GlobalColor.black if target=='bg' else Qt.GlobalColor.white, parent=self)
        if c.isValid():
            h = c.name()
            if target == 'bg': 
                self.bg_color = h
                self.update_btn_style(self.btn_bg, h)
            else: 
                self.text_color = h
                self.update_btn_style(self.btn_text, h)

    def restore_defaults(self):
        """【恢复】重置主题设置"""
        defaults = {"background_color": "#2b2b2b", "text_color": "#ffffff", "font_size": 14}
        self.bg_color = defaults["background_color"]
        self.text_color = defaults["text_color"]
        self.font_size = defaults["font_size"]
        
        self.update_btn_style(self.btn_bg, self.bg_color)
        self.update_btn_style(self.btn_text, self.text_color)
        self.spin_font.setValue(self.font_size)

    def save_all(self):
        self.cfg_mgr.set_theme(self.bg_color, self.text_color, self.spin_font.value())
        self.cfg_mgr.set_bing_cookie(self.cookie_input.text())
        self.accept()