from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QPushButton, QHBoxLayout, QMessageBox, QLabel
)
from utils.helpers import load_config, save_config


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self.setWindowTitle("软件设置")
        self.setMinimumWidth(500)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.api_endpoint = QLineEdit()
        self.api_endpoint.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("API 端点:", self.api_endpoint)

        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("sk-...")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key:", self.api_key)

        self.model = QLineEdit()
        self.model.setPlaceholderText("gpt-4o")
        form.addRow("模型:", self.model)

        self.max_concurrency = QSpinBox()
        self.max_concurrency.setRange(1, 10)
        self.max_concurrency.setValue(2)
        form.addRow("最大并发数:", self.max_concurrency)

        self.library_root = QLineEdit()
        self.library_root.setPlaceholderText(r"F:\文献阅读")
        form.addRow("文库根目录:", self.library_root)

        layout.addLayout(form)
        layout.addSpacing(10)

        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_values(self):
        self.api_endpoint.setText(self.config.get("api_endpoint", ""))
        self.api_key.setText(self.config.get("api_key", ""))
        self.model.setText(self.config.get("model", ""))
        self.max_concurrency.setValue(self.config.get("max_concurrency", 2))
        self.library_root.setText(self.config.get("library_root", ""))

    def _on_save(self):
        endpoint = self.api_endpoint.text().strip()
        key = self.api_key.text().strip()
        model = self.model.text().strip()

        if not endpoint:
            QMessageBox.warning(self, "提示", "请输入 API 端点")
            return
        if not key:
            QMessageBox.warning(self, "提示", "请输入 API Key")
            return
        if not model:
            QMessageBox.warning(self, "提示", "请输入模型名称")
            return

        self.config["api_endpoint"] = endpoint
        self.config["api_key"] = key
        self.config["model"] = model
        self.config["max_concurrency"] = self.max_concurrency.value()
        self.config["library_root"] = self.library_root.text().strip()

        try:
            save_config(self.config)
            QMessageBox.information(self, "完成", "设置已保存")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def get_config(self):
        return self.config
