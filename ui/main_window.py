import os
import re
import threading
from queue import Queue
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QLabel, QFileDialog, QMessageBox, QMenu,
    QAbstractItemView, QApplication, QTabWidget,
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QAction

from core.file_parser import extract_text, is_supported
from core.ai_service import AIService
from core.classifier import load_keyword_map, classify
from core.writer import write_md_file
from utils.helpers import load_config, format_file_size, SUPPORTED_FILTER
from ui.settings_dialog import SettingsDialog
from ui.wechat_tab import WechatTab


# ── 文件队列状态 ──
STATUS_WAITING = "等待中"
STATUS_PARSING = "解析中..."
STATUS_ANALYZING = "AI 分析中..."
STATUS_WRITING = "写入中..."
STATUS_DONE = "已完成"
STATUS_ERROR = "失败"


class WorkerSignals(QObject):
    progress = Signal(int, int)
    file_done = Signal(int, str, bool, str)
    finished = Signal()


class AnalysisWorker(QObject):
    def __init__(self, file_list, config, keyword_map):
        super().__init__()
        self.file_list = file_list
        self.config = config
        self.keyword_map = keyword_map
        self._is_paused = False
        self._is_cancelled = False
        self.signals = WorkerSignals()

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        ai_service = AIService(
            self.config["api_endpoint"],
            self.config["api_key"],
            self.config["model"]
        )

        total = len(self.file_list)
        for idx, (file_path, display_name) in enumerate(self.file_list):
            if self._is_cancelled:
                break

            while self._is_paused and not self._is_cancelled:
                QThread.msleep(200)

            if self._is_cancelled:
                break

            self.signals.progress.emit(idx, total)

            try:
                self.signals.file_done.emit(idx, display_name, True, STATUS_PARSING)
                content = extract_text(file_path)
                if not content.strip():
                    raise ValueError("未能提取到文本内容，文件可能为纯图片")

                basename = os.path.splitext(display_name)[0]
                category = classify(basename, content[:2000], self.keyword_map)

                self.signals.file_done.emit(idx, display_name, True, STATUS_ANALYZING)
                analysis = ai_service.analyze(basename, content)

                self.signals.file_done.emit(idx, display_name, True, STATUS_WRITING)
                write_md_file(file_path, analysis, category, self.config)

                self.signals.file_done.emit(idx, display_name, True, STATUS_DONE)

            except Exception as e:
                self.signals.file_done.emit(idx, display_name, False, f"{STATUS_ERROR}: {str(e)[:80]}")

        self.signals.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.keyword_map = load_keyword_map()
        self.file_queue = []
        self.worker_thread = None
        self.worker = None
        self.setWindowTitle("文献智能分析器")
        self.setMinimumSize(900, 650)
        self.setAcceptDrops(True)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # ═══ 标签页 ═══
        self.tabs = QTabWidget()

        # ── Tab 0: 文件分析 ──
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)
        file_layout.setContentsMargins(0, 8, 0, 0)

        # 工具栏
        tool_layout = QHBoxLayout()

        self.btn_select = QPushButton("选择文件")
        self.btn_select.clicked.connect(self._on_select_files)

        self.btn_clear = QPushButton("清空队列")
        self.btn_clear.clicked.connect(self._on_clear_queue)

        self.btn_start = QPushButton("开始分析")
        self.btn_start.clicked.connect(self._on_start_analysis)
        self.btn_start.setEnabled(False)

        self.btn_pause = QPushButton("暂停")
        self.btn_pause.clicked.connect(self._on_toggle_pause)
        self.btn_pause.setEnabled(False)

        self.btn_settings = QPushButton("设置")
        self.btn_settings.clicked.connect(self._on_open_settings)

        tool_layout.addWidget(self.btn_select)
        tool_layout.addWidget(self.btn_clear)
        tool_layout.addSpacing(20)
        tool_layout.addWidget(self.btn_start)
        tool_layout.addWidget(self.btn_pause)
        tool_layout.addStretch()
        tool_layout.addWidget(self.btn_settings)

        file_layout.addLayout(tool_layout)

        # 文件表格
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["文件名", "类型", "大小", "分类", "状态"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.verticalHeader().setVisible(False)
        file_layout.addWidget(self.table)

        self.tabs.addTab(file_tab, "文件分析")

        # ── Tab 1: 公众号文章 ──
        self.wechat_tab = WechatTab()
        self.tabs.addTab(self.wechat_tab, "公众号文章")

        main_layout.addWidget(self.tabs)

        # ═══ 底部进度（共享） ═══
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)

    # ─── 拖放支持 ───
    def dragEnterEvent(self, event: QDragEnterEvent):
        if self.tabs.currentIndex() == 0 and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if self.tabs.currentIndex() != 0:
            return
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and is_supported(path):
                files.append(path)
        self._add_files(files)

    # ─── 按钮事件 ───
    def _on_select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文献文件", "", SUPPORTED_FILTER
        )
        if files:
            self._add_files(files)

    def _on_clear_queue(self):
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认", "正在分析中，清空队列将取消当前任务，确认？"
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._cancel_worker()

        self.file_queue.clear()
        self.table.setRowCount(0)
        self.btn_start.setEnabled(False)
        self.status_label.setText("就绪")

    def _on_start_analysis(self):
        if not self.file_queue:
            return

        self.btn_select.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("暂停")

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.file_queue))
        self.progress_bar.setValue(0)

        for row in range(self.table.rowCount()):
            self.table.item(row, 4).setText(STATUS_WAITING)
            self.table.item(row, 4).setForeground(Qt.GlobalColor.gray)

        self.worker_thread = QThread()
        self.worker = AnalysisWorker(
            self.file_queue, self.config, self.keyword_map
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker.signals.progress.connect(self._on_progress)
        self.worker.signals.file_done.connect(self._on_file_done)
        self.worker.signals.finished.connect(self._on_all_done)

        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _on_toggle_pause(self):
        if not self.worker:
            return
        if self.btn_pause.text() == "暂停":
            self.worker.pause()
            self.btn_pause.setText("继续")
            self.status_label.setText("已暂停")
        else:
            self.worker.resume()
            self.btn_pause.setText("暂停")
            self.status_label.setText("分析中...")

    def _on_open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.config = dialog.get_config()
            self.wechat_tab.refresh_config()

    # ─── 辅助方法 ───
    def _add_files(self, file_paths):
        added = 0
        for fp in file_paths:
            if any(fp == item[0] for item in self.file_queue):
                continue

            display_name = os.path.basename(fp)
            self.file_queue.append((fp, display_name))

            row = self.table.rowCount()
            self.table.insertRow(row)

            ext = os.path.splitext(fp)[1].upper().replace(".", "")
            size = format_file_size(os.path.getsize(fp))

            basename = os.path.splitext(display_name)[0]
            category = classify(basename, basename, self.keyword_map)

            self.table.setItem(row, 0, QTableWidgetItem(display_name))
            self.table.setItem(row, 1, QTableWidgetItem(ext))
            self.table.setItem(row, 2, QTableWidgetItem(size))
            cat_item = QTableWidgetItem(category)
            cat_item.setToolTip(f"将归入 [{category}] 文件夹")
            self.table.setItem(row, 3, cat_item)
            self.table.setItem(row, 4, QTableWidgetItem(STATUS_WAITING))
            added += 1

        if added > 0:
            self.btn_start.setEnabled(True)
            self.status_label.setText(f"已添加 {added} 个文件，共 {len(self.file_queue)} 个")
        else:
            self.status_label.setText("未添加新文件（可能已存在队列中）")

    def _on_progress(self, current, total):
        self.progress_bar.setValue(current)
        self.status_label.setText(f"处理进度: {current}/{total}")

    def _on_file_done(self, row, name, success, message):
        item = self.table.item(row, 4)
        if item:
            item.setText(message)
            if success:
                if message == STATUS_DONE:
                    item.setText("已完成")
                    item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    item.setText(message)
                    item.setForeground(Qt.GlobalColor.blue)
            else:
                item.setForeground(Qt.GlobalColor.red)

    def _on_all_done(self):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.btn_select.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("暂停")

        self.status_label.setText("全部处理完成")

        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None

    def _cancel_worker(self):
        if self.worker:
            self.worker.cancel()
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker_thread = None
        self.worker = None

    # ─── 右键菜单 ───
    def _on_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        menu = QMenu(self)
        remove_action = QAction("移出队列", self)
        remove_action.triggered.connect(lambda: self._remove_file(row))
        menu.addAction(remove_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _remove_file(self, row):
        if 0 <= row < len(self.file_queue):
            self.file_queue.pop(row)
            self.table.removeRow(row)
            if not self.file_queue:
                self.btn_start.setEnabled(False)
                self.status_label.setText("队列已清空")

    def closeEvent(self, event):
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认退出", "正在分析中，退出将取消任务，确认？"
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._cancel_worker()
        event.accept()
