import sys
import os
import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QTextEdit, QPushButton, 
                             QSplitter, QFrame, QLineEdit, QCheckBox, 
                             QProgressBar, QTabWidget, QComboBox, QMessageBox,
                             QScrollArea, QInputDialog, QToolButton, QFileDialog,
                             QListWidget, QAbstractItemView, QSpinBox) 
from PyQt6.QtGui import QAction, QDesktopServices, QColor, QIcon
from PyQt6.QtCore import Qt, QUrl

from config_manager import ConfigManager
from options_dialog import OptionsDialog
from param_dialog import ModelParamsDialog
from workers import ArenaWorker, JudgeWorker, SearchWorker

AVAILABLE_MODELS = [
    "deepseek-ai/DeepSeek-R1",
    "deepseek-ai/DeepSeek-V3",
    "Qwen/Qwen2.5-72B-Instruct",
    "Qwen/Qwen3-VL-32B-Thinking",
    "Pro/moonshotai/Kimi-K2-Thinking",
    "deepseek-ai/deepseek-vl2"
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg_mgr = ConfigManager()
        
        self.active_workers = [] 
        self.results_buffer = {}
        self.total_contestants = 0
        self.uploaded_files = [] 
        self.model_params_map = {} 
        self.judge_params = {"temperature": 0.2, "top_p": 0.9, "max_tokens": 2048, "frequency_penalty": 0.0}

        self.init_ui()
        self.restore_state()
        self.load_presets_to_ui()
        self.load_user_presets_to_ui()

    def init_ui(self):
        self.setWindowTitle("【模型开会】 作者公众号：叶草凡的日记本 邮箱：yp.work@foxmail.com")
        
        # --- 【修改点 1】设置窗口图标 ---
        # 尝试加载同目录下的 icon.ico
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # --- 菜单栏 ---
        menu_bar = self.menuBar()
        opt_action = QAction("⚙️ 设置 (Settings)", self)
        opt_action.triggered.connect(self.open_options)
        menu_bar.addAction(opt_action)
        menu_bar.addSeparator()

        doc_action = QAction("📚 使用教程", self)
        doc_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://mp.weixin.qq.com/s/YrVm0asyPHQjThmIAcwmgQ")))
        menu_bar.addAction(doc_action)

        list_action = QAction("📋 可用模型列表", self)
        list_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://docs.siliconflow.cn/quickstart/models")))
        menu_bar.addAction(list_action)
        
        invite_action = QAction("🎁 注册SiliconFlow领取免费Tokens", self)
        invite_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://cloud.siliconflow.cn/i/j7F36Uco")))
        menu_bar.addAction(invite_action)

        # --- 主界面 ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === 左侧面板 ===
        left_panel = QFrame()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        left_layout.addWidget(QLabel("<b>SiliconFlow API Key:</b>"))
        key_layout = QHBoxLayout()
        key_layout.setSpacing(2)
        self.api_key_combo = QComboBox()
        self.api_key_combo.setToolTip("选择或添加 API Key")
        self.api_key_combo.currentIndexChanged.connect(self.on_api_key_changed)
        key_layout.addWidget(self.api_key_combo)
        btn_add_key = QToolButton()
        btn_add_key.setText("增") #稍微美化了一下符号
        btn_add_key.setToolTip("添加新的 API Key")
        btn_add_key.clicked.connect(self.add_api_key_action)
        key_layout.addWidget(btn_add_key)
        btn_del_key = QToolButton()
        btn_del_key.setText("删")
        btn_del_key.setToolTip("删除当前选中的 API Key")
        btn_del_key.clicked.connect(self.del_api_key_action)
        key_layout.addWidget(btn_del_key)
        left_layout.addLayout(key_layout)
        # 初始化加载 Key
        self.refresh_api_key_list()
        
        left_layout.addWidget(QLabel("<b>选手模型 :</b>"))
        self.model_checkboxes = [] 
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(2)
        
        for model in AVAILABLE_MODELS:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            cb = QCheckBox(model.split("/")[-1])
            cb.setProperty("full_name", model)
            btn_gear = QToolButton()
            btn_gear.setText("⚙") 
            btn_gear.clicked.connect(lambda checked, m=model: self.open_param_dialog(m, is_judge=False))
            row_layout.addWidget(cb)
            row_layout.addStretch()
            row_layout.addWidget(btn_gear)
            scroll_layout.addWidget(row_widget)
            self.model_checkboxes.append(cb)
            
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        left_panel.setLayout(left_layout)

        # === 右侧面板 ===
        right_panel = QFrame()
        right_layout = QVBoxLayout()
        
        # 1. 顶部栏
        header_layout = QHBoxLayout()
        # header_layout.addWidget(QLabel("场景预设:"))
        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        header_layout.addWidget(self.preset_combo)
        
        btn_save_preset = QPushButton("存"); btn_save_preset.setMaximumWidth(40)
        btn_save_preset.clicked.connect(self.save_current_as_preset)
        header_layout.addWidget(btn_save_preset)
        
        btn_del_preset = QPushButton("删"); btn_del_preset.setMaximumWidth(40)
        btn_del_preset.clicked.connect(self.delete_current_preset)
        header_layout.addWidget(btn_del_preset)
        
        header_layout.addStretch()
        header_layout.addWidget(QLabel("裁判模型:"))
        self.judge_selector = QComboBox()
        
        # --- 【修改点 2】添加“不启用裁判”选项 ---
        self.judge_selector.addItem("🚫 不启用裁判 (Skip Judge)", None) 
        
        for model in AVAILABLE_MODELS:
            self.judge_selector.addItem(model.split("/")[-1], model)
            
        # 默认选中列表中的第一个真实模型（索引为1），如果想默认不启用，设为 0
        self.judge_selector.setCurrentIndex(1) 
        
        header_layout.addWidget(self.judge_selector)
        
        self.btn_judge_gear = QToolButton(); self.btn_judge_gear.setText("⚙")
        # 注意：这里加了个检查，防止对 None 调用配置
        self.btn_judge_gear.clicked.connect(lambda: self.open_param_dialog(self.judge_selector.currentData(), is_judge=True) if self.judge_selector.currentData() else None)
        header_layout.addWidget(self.btn_judge_gear)
        right_layout.addLayout(header_layout)

        # 2. 输入区域
        input_split = QSplitter(Qt.Orientation.Vertical)
        
        # 裁判 Prompt
        judge_frame = QWidget()
        j_layout = QVBoxLayout(judge_frame); j_layout.setContentsMargins(0,0,0,0)
        j_layout.addWidget(QLabel("<b>裁判指令 (System Prompt):</b>"))
        self.judge_input = QTextEdit()
        self.judge_input.setPlainText("你是一个公正的AI裁判。请对比各模型回答，指出优缺点，并整合生成一个最完美的答案。")
        self.judge_input.setMaximumHeight(80)
        j_layout.addWidget(self.judge_input)
        input_split.addWidget(judge_frame)
        
        # 用户输入区
        user_frame = QWidget()
        u_layout = QVBoxLayout(user_frame); u_layout.setContentsMargins(0,0,0,0)
        
        tool_layout = QHBoxLayout()
        self.btn_search = QPushButton("🌐 联网搜索"); self.btn_search.setCheckable(True)
        self.btn_search.setToolTip("开启后，将先进行Bing搜索。请在设置中配置 Cookie 以获得最佳效果。")
        self.btn_search.setStyleSheet("""
            QPushButton:checked { background-color: #4CAF50; color: white; border: 1px solid #3e8e41; }
        """)
        tool_layout.addWidget(self.btn_search)
        
        self.spin_search_count = QSpinBox(); self.spin_search_count.setRange(1, 10); self.spin_search_count.setValue(5)
        self.spin_search_count.setSuffix(" 条")
        tool_layout.addWidget(self.spin_search_count)
        
        tool_layout.addWidget(QFrame(frameShape=QFrame.Shape.VLine))
        
        self.btn_upload = QPushButton("📎 添加文件"); self.btn_upload.clicked.connect(self.upload_file_action)
        tool_layout.addWidget(self.btn_upload)
        self.btn_remove_file = QPushButton("❌ 移除"); self.btn_remove_file.clicked.connect(self.remove_file_action)
        tool_layout.addWidget(self.btn_remove_file)
        
        tool_layout.addStretch()
        
        self.user_preset_combo = QComboBox(); self.user_preset_combo.setMinimumWidth(100)
        self.user_preset_combo.currentTextChanged.connect(self.apply_user_preset)
        tool_layout.addWidget(self.user_preset_combo)
        
        btn_u_save = QPushButton("存"); btn_u_save.setMaximumWidth(30); btn_u_save.clicked.connect(self.save_user_preset_action)
        tool_layout.addWidget(btn_u_save)
        btn_u_del = QPushButton("删"); btn_u_del.setMaximumWidth(30); btn_u_del.clicked.connect(self.delete_user_preset_action)
        tool_layout.addWidget(btn_u_del)
        
        u_layout.addLayout(tool_layout)
        
        self.file_list_widget = QListWidget(); self.file_list_widget.setMaximumHeight(50)
        u_layout.addWidget(self.file_list_widget)
        
        self.user_input = QTextEdit(); self.user_input.setPlaceholderText("在此输入任务...")
        u_layout.addWidget(self.user_input)
        input_split.addWidget(user_frame)
        
        right_layout.addWidget(input_split)

        # 3. 控制栏
        ctrl_layout = QHBoxLayout()
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        ctrl_layout.addWidget(self.progress_bar)
        
        self.start_btn = QPushButton("开始竞技 (Start Arena)"); self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_arena)
        ctrl_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("🛑 中止 (Stop)"); self.stop_btn.setMinimumHeight(40); self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: white; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """)
        self.stop_btn.clicked.connect(self.stop_arena)
        ctrl_layout.addWidget(self.stop_btn)
        
        self.export_btn = QPushButton("📂 导出结果"); self.export_btn.setMinimumHeight(40)
        self.export_btn.clicked.connect(self.export_results)
        ctrl_layout.addWidget(self.export_btn)
        
        right_layout.addLayout(ctrl_layout)

        # 4. 结果展示
        self.result_tabs = QTabWidget()
        self.tab_fusion = QTextEdit(); self.tab_fusion.setReadOnly(True)
        self.result_tabs.addTab(self.tab_fusion, "🏆 融合结果")
        self.tab_verdict = QTextEdit(); self.tab_verdict.setReadOnly(True)
        self.result_tabs.addTab(self.tab_verdict, "⚖️ 裁判分析")
        self.tab_raw = QTextEdit(); self.tab_raw.setReadOnly(True)
        self.result_tabs.addTab(self.tab_raw, "📝 原始回答")
        right_layout.addWidget(self.result_tabs)

        right_panel.setLayout(right_layout)

        splitter.addWidget(left_panel); splitter.addWidget(right_panel)
        splitter.setSizes([280, 920])
        self.setCentralWidget(splitter)
    # --- 逻辑部分 ---
    # --- 新增的 API Key 管理逻辑 (请补全这部分) ---

    def mask_key(self, key):
        """脱敏显示 Key"""
        if len(key) < 10: return key
        return f"{key[:3]}...{key[-4:]}"

    def refresh_api_key_list(self):
        """从配置刷新 Key 列表"""
        self.api_key_combo.blockSignals(True)
        self.api_key_combo.clear()
        
        # 注意：这里需要 config_manager.py 也已经更新支持 get_api_keys
        if hasattr(self.cfg_mgr, 'get_api_keys'):
            keys = self.cfg_mgr.get_api_keys()
        else:
            keys = []
            
        for k in keys:
            # 文本显示脱敏版，User Data 存真实版
            self.api_key_combo.addItem(self.mask_key(k), k)
            
        # 恢复上次选中的索引
        if hasattr(self.cfg_mgr, 'get_current_key_index'):
            saved_idx = self.cfg_mgr.get_current_key_index()
            if saved_idx < self.api_key_combo.count():
                self.api_key_combo.setCurrentIndex(saved_idx)
        elif self.api_key_combo.count() > 0:
            self.api_key_combo.setCurrentIndex(0)
            
        self.api_key_combo.blockSignals(False)

    def add_api_key_action(self):
        text, ok = QInputDialog.getText(self, "添加 API Key", "请输入 SiliconFlow API Key (sk-...):")
        if ok and text.strip():
            key = text.strip()
            # 确保 config_manager.py 已实现 add_api_key
            if hasattr(self.cfg_mgr, 'add_api_key'):
                self.cfg_mgr.add_api_key(key)
                self.refresh_api_key_list()
                # 自动选中刚添加的
                self.api_key_combo.setCurrentIndex(self.api_key_combo.count() - 1)
            else:
                QMessageBox.critical(self, "错误", "ConfigManager 尚未更新，无法添加 Key。")

    def del_api_key_action(self):
        idx = self.api_key_combo.currentIndex()
        if idx == -1: return
        
        reply = QMessageBox.question(self, "确认删除", "确定要删除当前选中的 API Key 吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.cfg_mgr, 'remove_api_key'):
                self.cfg_mgr.remove_api_key(idx)
                self.refresh_api_key_list()

    def on_api_key_changed(self, index):
        """记录选中的索引"""
        if hasattr(self.cfg_mgr, 'set_current_key_index'):
            self.cfg_mgr.set_current_key_index(index)

    def start_arena(self):
        # 修改：不再从 LineEdit 获取，而是从 ComboBox 的 Data 获取
        api_key = self.api_key_combo.currentData() 
        if not api_key:
            QMessageBox.warning(self, "错误", "请先添加并选择一个有效的 API Key！")
            return
        
        user_prompt = self.user_input.toPlainText().strip()
        if not user_prompt: return

        self.selected_workers_data = []
        for cb in self.model_checkboxes:
            if cb.isChecked():
                m_name = cb.property("full_name")
                config = {"name": m_name}
                config.update(self.model_params_map.get(m_name, {}))
                self.selected_workers_data.append(config)
        
        if not self.selected_workers_data:
            QMessageBox.warning(self, "提示", "请选择至少一个模型。")
            return

        self.set_ui_busy(True)
        self.tab_raw.clear(); self.tab_fusion.clear(); self.tab_verdict.clear()
        
        if self.btn_search.isChecked():
            self.start_search_phase(user_prompt)
        else:
            self.start_contest_phase(user_prompt, search_context="")

    def start_search_phase(self, user_prompt):
        self.start_btn.setText("正在搜索...")
        cookie = self.cfg_mgr.get_bing_cookie()
        worker = SearchWorker(user_prompt, self.spin_search_count.value(), cookie)
        worker.finished_signal.connect(lambda res: self.on_search_finished(res, user_prompt))
        self.active_workers.append(worker)
        worker.start()

    def on_search_finished(self, result_text, user_prompt):
        self.tab_raw.append(f"{result_text}\n\n")
        self.start_contest_phase(user_prompt, search_context=result_text)

    def start_contest_phase(self, user_prompt, search_context):
        self.start_btn.setText("模型思考中...")
        final_prompt = user_prompt
        if search_context:
            final_prompt = f"{user_prompt}\n\n【联网搜索参考资料】\n{search_context}"

        self.results_buffer = {}
        self.total_contestants = len(self.selected_workers_data)
        self.progress_bar.setRange(0, self.total_contestants + 1)
        self.progress_bar.setValue(0)
        
        vision_models = self.cfg_mgr.get_vision_models()
        
        # 修改：获取当前的 API Key
        current_api_key = self.api_key_combo.currentData()

        for model_conf in self.selected_workers_data:
            worker = ArenaWorker(
                current_api_key, # 传入 Key
                model_conf, 
                final_prompt, 
                file_paths=self.uploaded_files,
                vision_models=vision_models
            )
            worker.finished_signal.connect(self.on_contestant_finish)
            self.active_workers.append(worker)
            worker.start()

    def on_contestant_finish(self, model_name, content, full_response):
        self.results_buffer[model_name] = content
        short = model_name.split("/")[-1]
        self.tab_raw.append(f"=== {short} ===\n{content}\n\n")
        self.progress_bar.setValue(len(self.results_buffer))
        
        if len(self.results_buffer) == self.total_contestants:
            self.start_judge_phase()

    def start_judge_phase(self):
        # 修改：获取当前的 API Key
        current_api_key = self.api_key_combo.currentData()
        judge_model = self.judge_selector.currentData()

        # --- 【修改点 3】如果不启用裁判，直接结束 ---
        if not judge_model:
            self.set_ui_busy(False)
            self.progress_bar.setValue(self.total_contestants + 1)
            self.tab_fusion.setPlainText("[裁判未启用]\n仅展示各模型的原始回答，请切换到“原始回答”标签页查看。")
            self.tab_verdict.setPlainText("[裁判未启用]")
            self.result_tabs.setCurrentIndex(2) # 自动跳转到原始回答页
            return
            
        self.start_btn.setText("裁判思考中...")
        
        judge_worker = JudgeWorker(
            current_api_key, # 传入 Key
            judge_model,
            self.judge_input.toPlainText(),
            self.user_input.toPlainText(),
            self.results_buffer
        )
        judge_worker.result_signal.connect(self.on_judge_finish)
        self.active_workers.append(judge_worker)
        judge_worker.start()

    def on_judge_finish(self, result_json):
        self.set_ui_busy(False)
        self.progress_bar.setValue(self.total_contestants + 1)
        
        if "error" in result_json:
            self.tab_fusion.setPlainText(f"裁判出错: {result_json['error']}\n{result_json.get('raw_output')}")
            return

        self.tab_fusion.setPlainText(f"最佳模型: {result_json.get('best_model')}\n\n{result_json.get('fusion_result')}")
        
        reviews = result_json.get("reviews", [])
        v_text = ""
        for r in reviews:
            v_text += f"模型: {r.get('model')}\n评分: {r.get('score')}\n点评: {r.get('comment')}\n----------------\n"
        self.tab_verdict.setPlainText(v_text)
        self.result_tabs.setCurrentIndex(0)

    def stop_arena(self):
        for w in self.active_workers:
            if hasattr(w, 'stop'): w.stop()
            try: w.finished_signal.disconnect() 
            except: pass
            try: w.result_signal.disconnect()
            except: pass
            if isinstance(w, SearchWorker) and w.isRunning(): w.terminate() 
        
        self.active_workers.clear()
        self.set_ui_busy(False)
        self.tab_fusion.append("\n[用户已中止进程]")

    def set_ui_busy(self, busy):
        self.start_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.progress_bar.setVisible(busy)
        if not busy: self.start_btn.setText("开始竞技 (Start Arena)")


    def upload_file_action(self):
        file_filter = (
            "Supported Files (*.docx *.txt *.md *.py *.json *.js *.html *.css *.c *.cpp *.h *.java *.log *.jpg *.jpeg *.png *.bmp *.webp);;"
            "Word Document (*.docx);;"
            "Images (*.jpg *.jpeg *.png *.bmp *.webp);;"
            "Text/Code (*.txt *.md *.py *.json *.js *.html *.css *.c *.cpp *.h *.java *.log);;"
            "All Files (*)"
        )
        
        fnames, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", file_filter)
        if fnames:
            for f in fnames:
                if f not in self.uploaded_files:
                    # 再次进行简单的后缀名防呆检查（可选，防止用户选All Files强行传PDF）
                    ext = os.path.splitext(f)[1].lower()
                    if ext in ['.pdf', '.pptx', '.ppt', '.xlsx', '.xls']:
                        QMessageBox.warning(self, "格式不支持", f"已停止支持 {ext} 格式，请仅上传 .docx、图片或纯文本。")
                        continue
                        
                    self.uploaded_files.append(f)
                    self.file_list_widget.addItem(os.path.basename(f))

    def remove_file_action(self):
        for item in self.file_list_widget.selectedItems():
            row = self.file_list_widget.row(item)
            self.file_list_widget.takeItem(row)
            if row < len(self.uploaded_files): self.uploaded_files.pop(row)

    def open_options(self):
        dlg = OptionsDialog(self.cfg_mgr, self)
        if dlg.exec(): self.apply_theme()

    def open_param_dialog(self, name, is_judge=False):
        params = self.judge_params if is_judge else self.model_params_map.get(name, {})
        dlg = ModelParamsDialog(name, params, self)
        if dlg.exec():
            new_p = dlg.get_params()
            if is_judge: self.judge_params = new_p
            else: self.model_params_map[name] = new_p

    def load_presets_to_ui(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("- 裁判预设 -")
        self.preset_combo.addItems(self.cfg_mgr.get_preset_names())
        self.preset_combo.blockSignals(False)
        
    def save_current_as_preset(self):
        name, ok = QInputDialog.getText(self, "保存", "预设名称:")
        if ok and name:
            sel = []
            for cb in self.model_checkboxes:
                if cb.isChecked():
                    n = cb.property("full_name")
                    sel.append({"name": n, "params": self.model_params_map.get(n, {})})
            self.cfg_mgr.save_preset(name, self.judge_selector.currentData(), self.judge_params, self.judge_input.toPlainText(), sel)
            self.load_presets_to_ui()

    def delete_current_preset(self):
        self.cfg_mgr.delete_current_preset(self.preset_combo.currentText())
        self.load_presets_to_ui()

    def apply_preset(self, name):
        p = self.cfg_mgr.get_preset_by_name(name)
        if not p: return
        self.judge_input.setPlainText(p.get("judge_prompt", ""))
        idx = self.judge_selector.findData(p.get("judge_model"))
        if idx >= 0: self.judge_selector.setCurrentIndex(idx)
        self.judge_params = p.get("judge_params", {})
        saved_names = [m["name"] for m in p.get("selected_models", [])]
        for cb in self.model_checkboxes:
            full = cb.property("full_name")
            cb.setChecked(full in saved_names)
            if full in saved_names:
                for m in p["selected_models"]:
                    if m["name"] == full: self.model_params_map[full] = m.get("params", {})

    def load_user_presets_to_ui(self):
        self.user_preset_combo.blockSignals(True)
        self.user_preset_combo.clear()
        self.user_preset_combo.addItem("- 提示词预设 -")
        self.user_preset_combo.addItems(self.cfg_mgr.get_user_preset_names())
        self.user_preset_combo.blockSignals(False)

    def save_user_preset_action(self):
        name, ok = QInputDialog.getText(self, "保存", "问题名称:")
        if ok and name:
            self.cfg_mgr.save_user_preset(name, self.user_input.toPlainText())
            self.load_user_presets_to_ui()

    def delete_user_preset_action(self):
        self.cfg_mgr.delete_user_preset(self.user_preset_combo.currentText())
        self.load_user_presets_to_ui()

    def apply_user_preset(self, name):
        c = self.cfg_mgr.get_user_preset_content(name)
        if c: self.user_input.setPlainText(c)

    def export_results(self):
        txt = self.tab_fusion.toPlainText()
        if not txt: return
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(os.getcwd(), f"Arena_Result_{now}.txt")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"问题: {self.user_input.toPlainText()}\n\n=== 融合结果 ===\n{txt}\n\n=== 裁判 ===\n{self.tab_verdict.toPlainText()}\n\n=== 原始 ===\n{self.tab_raw.toPlainText()}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.getcwd()))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    # --- 【关键修复】恢复完整的状态保存与加载逻辑 ---
    def restore_state(self):
        state = self.cfg_mgr.get_window_state()
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])
        self.apply_theme()
        
        last = self.cfg_mgr.get_last_session()
        if not last: return

        # 恢复各个输入框
        if "judge_prompt" in last: self.judge_input.setPlainText(last["judge_prompt"])
        if "user_prompt" in last: self.user_input.setPlainText(last["user_prompt"])
        
        # 恢复裁判选择
        if "judge_model" in last:
            idx = self.judge_selector.findData(last["judge_model"])
            if idx >= 0: self.judge_selector.setCurrentIndex(idx)
        
        # 恢复参数
        if "judge_params" in last: self.judge_params = last["judge_params"]
        if "model_params_map" in last: self.model_params_map = last["model_params_map"]
            
        # 恢复模型勾选状态
        saved_selected = last.get("selected_models", [])
        for cb in self.model_checkboxes:
            full_name = cb.property("full_name")
            cb.setChecked(full_name in saved_selected)
        
        # 恢复搜索设置
        if "search_enabled" in last:
            self.btn_search.setChecked(last["search_enabled"])
        if "search_max_results" in last:
            self.spin_search_count.setValue(int(last["search_max_results"]))

    def closeEvent(self, e):
        geo = self.geometry()
        self.cfg_mgr.set_window_state(geo.x(), geo.y(), geo.width(), geo.height())
        
        # 【关键修复】保存完整状态
        selected_models_list = []
        for cb in self.model_checkboxes:
            if cb.isChecked():
                selected_models_list.append(cb.property("full_name"))

        session_data = {
            "judge_model": self.judge_selector.currentData(),
            "judge_params": self.judge_params,
            "judge_prompt": self.judge_input.toPlainText(),
            "selected_models": selected_models_list,
            "model_params_map": self.model_params_map, 
            "user_prompt": self.user_input.toPlainText(),
            "search_enabled": self.btn_search.isChecked(),
            "search_max_results": self.spin_search_count.value()
        }
        
        self.cfg_mgr.set_last_session(session_data)
        super().closeEvent(e)
        
    def adjust_color(self, hex_color, amount=10):
        if not QColor.isValidColor(hex_color): return hex_color
        c = QColor(hex_color)
        h, s, v, a = c.getHsv()
        if v < 128: v = min(255, v + amount * 2) 
        else: v = max(0, v - amount)
        return QColor.fromHsv(h, s, v, a).name()

    def apply_theme(self):
        theme = self.cfg_mgr.get_theme()
        bg = theme["background_color"]
        fg = theme["text_color"]
        font_size = theme["font_size"]
        input_bg = self.adjust_color(bg, 10)
        
        qss = f"""
            QMainWindow, QWidget {{ background-color: {bg}; color: {fg}; font-size: {font_size}px; }}
            QTextEdit, QLineEdit, QListWidget, QScrollArea {{ background-color: {input_bg}; border: 1px solid #555; border-radius: 4px; }}
            QTabWidget::pane {{ border: 1px solid #444; }}
            QTabBar::tab {{ background: {input_bg}; padding: 5px 10px; border: 1px solid #333; border-bottom: none; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
            QTabBar::tab:selected {{ background: #666; font-weight: bold; }}
            QPushButton, QToolButton {{ background-color: #4a90e2; color: white; border-radius: 4px; padding: 4px 8px; border: 1px solid #357abd; }}
            QPushButton:hover, QToolButton:hover {{ background-color: #357abd; }}
            QPushButton:pressed {{ background-color: #2a5a8d; }}
            QPushButton[text="🛑 中止 (Stop)"] {{ background-color: #d9534f; border-color: #d43f3a; }}
            QPushButton[text="🛑 中止 (Stop)"]:hover {{ background-color: #c9302c; }}
            QPushButton[text="🛑 中止 (Stop)"]:disabled {{ background-color: #555; border-color: #444; color: #888; }}
            QComboBox {{ background-color: {input_bg}; border: 1px solid #555; border-radius: 4px; padding: 2px; }}
            QProgressBar {{ border: 1px solid #555; border-radius: 4px; text-align: center; background-color: {input_bg}; }}
            QProgressBar::chunk {{ background-color: #4CAF50; }}
            QListWidget::item:selected {{ background-color: #357abd; }}
        """
        self.setStyleSheet(qss)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # --- 【修改点 4】设置应用程序级别的图标（用于任务栏） ---
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    icon_path = os.path.join(base_dir, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    w = MainWindow()
    w.show()
    sys.exit(app.exec())