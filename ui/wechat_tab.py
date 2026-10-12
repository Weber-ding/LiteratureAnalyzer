import os
import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QLabel, QMessageBox, QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QObject

from core.wechat_fetcher import fetch_article, is_wechat_url
from core.ai_service import AIService
from core.classifier import classify, load_keyword_map
from core.writer import write_article_md
from utils.helpers import load_config


class WechatFetcherSignals(QObject):
    fetched = Signal(dict)         # article info
    error = Signal(str)            # error message
    analysis_done = Signal(str)    # md_path
    progress = Signal(str)         # status text


class WechatTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self.keyword_map = load_keyword_map()
        self.article_info = None
        self.signals = WechatFetcherSignals()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── 说明 ──
        hint = QLabel("粘贴微信公众号文章链接，自动获取全文并分析。")
        hint.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(hint)

        # ── URL 输入行 ──
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://mp.weixin.qq.com/s/...")
        self.url_input.setClearButtonEnabled(True)

        self.btn_fetch = QPushButton("获取文章")
        self.btn_fetch.clicked.connect(self._on_fetch)

        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.btn_fetch)
        layout.addLayout(url_layout)

        # ── 文章预览区 ──
        preview_label = QLabel("文章预览")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(preview_label)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("获取文章后将显示标题、作者和内容摘要...")
        self.preview.setMaximumHeight(250)
        layout.addWidget(self.preview)

        # ── 状态提示 ──
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        # ── 分析按钮 ──
        btn_layout = QHBoxLayout()
        self.btn_analyze = QPushButton("开始分析")
        self.btn_analyze.clicked.connect(self._on_analyze)
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setMinimumHeight(36)
        self.btn_analyze.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 6px 30px; }"
        )

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_analyze)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        # 信号连接
        self.signals.fetched.connect(self._on_fetched)
        self.signals.error.connect(self._on_error)
        self.signals.analysis_done.connect(self._on_analysis_done)
        self.signals.progress.connect(self.status_label.setText)

    def _on_fetch(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入公众号文章链接")
            return

        if not is_wechat_url(url):
            reply = QMessageBox.question(
                self, "确认",
                "链接看起来不是标准的公众号文章格式（mp.weixin.qq.com），仍尝试获取？"
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.btn_fetch.setEnabled(False)
        self.btn_analyze.setEnabled(False)
        self.preview.clear()
        self.status_label.setText("正在获取文章...")
        self.article_info = None

        def task():
            try:
                article = fetch_article(url)
                self.signals.fetched.emit(article)
            except Exception as e:
                self.signals.error.emit(str(e))

        threading.Thread(target=task, daemon=True).start()

    def _on_fetched(self, article):
        self.article_info = article
        self.btn_fetch.setEnabled(True)
        self.btn_analyze.setEnabled(True)

        title = article.get("title", "未知")
        author = article.get("author", "未知")
        date = article.get("date", "未知")
        content = article.get("content", "")
        preview_text = (
            f"【标题】{title}\n"
            f"【作者】{author}\n"
            f"【日期】{date}\n"
            f"【字数】{len(content)} 字\n"
            f"\n{'='*40}\n"
            f"{content[:600]}"
            f"{'...' if len(content) > 600 else ''}"
        )
        self.preview.setPlainText(preview_text)
        self.status_label.setText("文章获取成功，点击【开始分析】进行 AI 解读")

    def _on_error(self, msg):
        self.btn_fetch.setEnabled(True)
        self.status_label.setText("获取失败")
        QMessageBox.critical(self, "获取失败", msg)

    def _on_analyze(self):
        if not self.article_info:
            return

        self.btn_analyze.setEnabled(False)
        self.btn_fetch.setEnabled(False)
        self.status_label.setText("AI 分析中...")

        def task():
            try:
                title = self.article_info.get("title", "未知")
                content = self.article_info.get("content", "")

                # AI 分析
                ai = AIService(
                    self.config["api_endpoint"],
                    self.config["api_key"],
                    self.config["model"]
                )
                analysis = ai.analyze(title, content)

                # 分类
                category = classify(title, content[:2000], self.keyword_map)

                # 写入 MD
                md_path = write_article_md(
                    self.article_info, analysis, category, self.config
                )

                self.signals.analysis_done.emit(md_path)

            except Exception as e:
                self.signals.error.emit(f"分析失败: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _on_analysis_done(self, md_path):
        self.btn_analyze.setEnabled(True)
        self.btn_fetch.setEnabled(True)
        self.status_label.setText(f"分析完成，已保存至: {md_path}")
        QMessageBox.information(self, "完成", f"分析笔记已生成：\n{md_path}")
        self.article_info = None

    def refresh_config(self):
        """从配置文件重新加载配置"""
        self.config = load_config()
        self.keyword_map = load_keyword_map()
