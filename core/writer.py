import os
import re
import shutil
from pathlib import Path
from datetime import date


def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def extract_keywords_from_analysis(text):
    """从 AI 分析结果中提取关键词列表"""
    keywords = []
    in_keyword_section = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## 六、关键词") or stripped.startswith("## 六、关键词"):
            in_keyword_section = True
            continue
        if in_keyword_section:
            if stripped.startswith("## "):
                break
            if stripped.startswith("- ") or stripped.startswith("* "):
                kw = stripped[2:].strip()
                if kw:
                    keywords.append(kw)
    return keywords


def find_related_mds(category_dir, skip_name, keywords, library_root):
    """扫描同分类目录，根据关键词找到相关文献，返回 Wiki 链接列表"""
    related = []
    if not os.path.isdir(category_dir):
        return related

    for fname in os.listdir(category_dir):
        if not fname.endswith(".md"):
            continue
        if fname == skip_name:
            continue
        if fname == "_Index.md":
            continue

        fpath = os.path.join(category_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content_text = f.read()
        except:
            continue

        score = 0
        for kw in keywords:
            if kw and kw.lower() in content_text.lower():
                score += 1
            name_part = fname.replace(".md", "")
            if kw and kw.lower() in name_part.lower():
                score += 2

        if score >= 2:
            related.append((score, fname.replace(".md", "")))

    related.sort(key=lambda x: -x[0])
    return [name for _, name in related]


def _update_index_file(target_dir, md_filename):
    """在目标文件夹的 _Index.md 中更新文献列表"""
    index_path = os.path.join(target_dir, "_Index.md")
    folder_name = os.path.basename(target_dir)
    link_line = f"- [[{md_filename.replace('.md', '')}]]"

    today = date.today().isoformat()

    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            text = f.read()

        if link_line in text:
            return

        marker = "## 文献列表"
        marker_pos = text.find(marker)
        if marker_pos == -1:
            text += f"\n\n{marker}\n\n{link_line}\n"
        else:
            after = text[marker_pos + len(marker):]
            after_lines = after.split("\n")
            link_lines = []
            other_lines = []
            in_list = True
            for line in after_lines:
                s = line.strip()
                if in_list and (s.startswith("- [[") or s == ""):
                    if s.startswith("- [["):
                        link_lines.append(s)
                else:
                    in_list = False
                    other_lines.append(line)

            if link_line not in link_lines:
                link_lines.append(link_line)
            link_lines.sort(key=lambda x: x.lower())

            new_after = "\n" + "\n".join(link_lines) + "\n" + "\n".join(other_lines)
            text = text[:marker_pos + len(marker)] + new_after

        text = re.sub(r'^updated:.*', f'updated: {today}', text, flags=re.MULTILINE)
        text = re.sub(r'最后更新:.*', f'最后更新: {today}', text)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        lines = [
            "---",
            "tags:",
            "  - MOC",
            "  - 索引",
            f"updated: {today}",
            "---",
            "",
            f"# {folder_name} - 文献索引",
            "",
            "> 本索引由文献智能分析器自动维护",
            "",
            "## 文献列表",
            "",
            link_line,
            "",
            "---",
            f"*最后更新: {today}*",
            "",
        ]
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def write_md_file(source_path, analysis_text, category, config):
    """生成 MD 文件并移动源文献"""
    library_root = config.get("library_root", "")
    output_dir = config.get("output_dir", "")

    basename = os.path.splitext(os.path.basename(source_path))[0]
    safe_name = sanitize_filename(basename)

    if category and library_root:
        target_dir = os.path.join(library_root, category)
    else:
        target_dir = output_dir

    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    md_filename = f"新未读_{safe_name}-快速整理.md"
    md_path = os.path.join(target_dir, md_filename)

    ai_keywords = extract_keywords_from_analysis(analysis_text)

    related_links = []
    if ai_keywords and os.path.isdir(target_dir):
        related_links = find_related_mds(target_dir, md_filename, ai_keywords, library_root)

    moved_path = move_source_file(source_path, target_dir)
    source_rel = os.path.relpath(moved_path, target_dir).replace("\\", "/")

    yaml_tags = ["分析笔记"]
    if category:
        yaml_tags.append(category)

    lines = ["---"]
    lines.append("tags:")
    for tag in yaml_tags:
        lines.append(f"  - {tag}")
    lines.append(f"title: {safe_name}")
    lines.append(f"分类: {category}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {safe_name}")
    lines.append("")
    lines.append(f"源文献：[{os.path.basename(source_path)}]({source_rel})")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(analysis_text.strip())
    lines.append("")

    if related_links:
        lines.append("---")
        lines.append("")
        lines.append("## 七、相关文献链接")
        lines.append("")
        lines.append("本目录下相关文献：")
        for link_name in related_links:
            lines.append(f"- [[{link_name}]]")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    _update_index_file(target_dir, md_filename)

    return md_path


def move_source_file(source_path, target_dir):
    """将源文献移动到目标目录，返回目标路径"""
    if not os.path.isfile(source_path):
        return source_path

    target_path = os.path.join(target_dir, os.path.basename(source_path))

    if os.path.exists(target_path):
        name, ext = os.path.splitext(target_path)
        counter = 1
        while os.path.exists(f"{name}_{counter}{ext}"):
            counter += 1
        target_path = f"{name}_{counter}{ext}"

    try:
        shutil.move(source_path, target_path)
        return target_path
    except Exception as e:
        raise IOError(f"移动源文件失败: {e}")


def write_article_md(article_info, analysis_text, category, config):
    """生成公众号文章 MD"""
    library_root = config.get("library_root", "")
    output_dir = config.get("output_dir", "")

    title = article_info.get("title", "未知文章")
    safe_name = sanitize_filename(title)
    article_url = article_info.get("url", "")
    author = article_info.get("author", "")
    pub_date = article_info.get("date", "")

    if category and library_root:
        target_dir = os.path.join(library_root, category)
    else:
        target_dir = output_dir

    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    md_filename = f"新未读_{safe_name}-快速整理.md"
    md_path = os.path.join(target_dir, md_filename)

    ai_keywords = extract_keywords_from_analysis(analysis_text)

    related_links = []
    if ai_keywords and os.path.isdir(target_dir):
        related_links = find_related_mds(target_dir, md_filename, ai_keywords, library_root)

    yaml_tags = ["分析笔记", "公众号文章"]
    if category:
        yaml_tags.append(category)

    lines = ["---"]
    lines.append("tags:")
    for tag in yaml_tags:
        lines.append(f"  - {tag}")
    lines.append(f"title: {safe_name}")
    lines.append(f"分类: {category}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {safe_name}")
    lines.append("")
    if author:
        lines.append(f"**作者：** {author}")
    if pub_date:
        lines.append(f"**日期：** {pub_date}")
    lines.append(f"**来源：** [原文链接]({article_url})")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(analysis_text.strip())
    lines.append("")

    if related_links:
        lines.append("---")
        lines.append("")
        lines.append("## 七、相关文献链接")
        lines.append("")
        lines.append("本目录下相关文献：")
        for link_name in related_links:
            lines.append(f"- [[{link_name}]]")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    _update_index_file(target_dir, md_filename)

    return md_path