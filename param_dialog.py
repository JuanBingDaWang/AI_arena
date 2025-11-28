# param_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QDoubleSpinBox, QSpinBox, QDialogButtonBox, QFrame,
                             QLineEdit)

class ModelParamsDialog(QDialog):
    def __init__(self, model_name, current_params, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"参数: {model_name.split('/')[-1]}")
        self.setMinimumWidth(400)
        self.original_name = model_name
        self.params = current_params.copy() if current_params else {}
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>自定义模型ID (覆盖默认):</b>"))
        self.edit_id = QLineEdit()
        self.edit_id.setText(self.params.get("custom_model_name", ""))
        self.edit_id.setPlaceholderText(model_name)
        layout.addWidget(self.edit_id)
        
        layout.addLayout(self.mk_spin("Temperature:", "temperature", 0.0, 2.0, 0.1, 0.7, True))
        layout.addLayout(self.mk_spin("Top_P:", "top_p", 0.0, 1.0, 0.1, 0.9, True))
        layout.addLayout(self.mk_spin("Max Tokens:", "max_tokens", 1, 32000, 100, 2048, False))
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)

    def mk_spin(self, label, key, minv, maxv, step, default, is_float):
        l = QHBoxLayout(); l.addWidget(QLabel(label))
        spin = QDoubleSpinBox() if is_float else QSpinBox()
        spin.setRange(minv, maxv); spin.setSingleStep(step)
        val = self.params.get(key, default)
        spin.setValue(val)
        spin.valueChanged.connect(lambda v: self.params.update({key: v}))
        l.addWidget(spin)
        return l

    def save(self):
        txt = self.edit_id.text().strip()
        if txt and txt != self.original_name: self.params["custom_model_name"] = txt
        elif "custom_model_name" in self.params: del self.params["custom_model_name"]
        self.accept()

    def get_params(self): return self.params