import os
import sys
import json


def get_app_dir():
    """获取应用根目录：打包后为 exe 所在目录，开发时为项目根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(path=None):
    if path is None:
        path = os.path.join(get_app_dir(), "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config, path=None):
    if path is None:
        path = os.path.join(get_app_dir(), "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def format_file_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


SUPPORTED_FILTER = "文献文件 (*.pdf *.pptx *.ppt *.docx *.doc);;PDF (*.pdf);;PowerPoint (*.pptx *.ppt);;Word (*.docx *.doc);;所有文件 (*.*)"
