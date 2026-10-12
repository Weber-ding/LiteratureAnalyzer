import re
import requests
from bs4 import BeautifulSoup


def fetch_article(url):
    """获取微信公众号文章内容"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.encoding = "utf-8"
        html = resp.text
    except Exception as e:
        raise ConnectionError(f"获取文章失败: {e}")

    if not html or len(html) < 500:
        raise ValueError("获取到的文章内容为空，链接可能无效或需要登录")

    return _parse_article(html, url)


def _parse_article(html, url):
    """解析公众号文章 HTML，提取关键信息"""
    soup = BeautifulSoup(html, "html.parser")

    # 1. 标题
    title = ""
    for sel in [
        "h1.rich_media_title",
        "h2.rich_media_title",
        "#activity-name",
        "h1.rich_media_content_title",
    ]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break
    if not title:
        # 从 og:title 取
        og = soup.select_one("meta[property='og:title']")
        if og:
            title = og.get("content", "")
    if not title:
        title = url.split("/")[-1][:50]

    # 2. 作者 / 公众号名称
    author = ""
    for sel in ["#js_name", ".rich_media_meta_nickname", "#profile-name"]:
        el = soup.select_one(sel)
        if el:
            author = el.get_text(strip=True)
            break

    # 3. 发布时间
    pub_date = ""
    for sel in ["#publish_time", "em#publish_time", "#create_time"]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            if txt:
                pub_date = txt
                break
    if not pub_date:
        # 从页面 script 中提取时间戳
        m = re.search(r'create_time\s*[:=]\s*["\']?(\d{4}-\d{2}-\d{2})', html)
        if m:
            pub_date = m.group(1)
        m = re.search(r'ct\s*=\s*["\'](\d+)["\']', html)
        if m:
            import datetime
            ts = int(m.group(1))
            pub_date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

    # 4. 正文内容
    body_el = soup.select_one("#js_content")
    if not body_el:
        body_el = soup.select_one(".rich_media_content")

    body_text = ""
    if body_el:
        # 移除无用标签
        for tag in body_el.find_all(["script", "style"]):
            tag.decompose()
        # 提取纯文本
        body_text = body_el.get_text("\n", strip=True)
        # 过长截断
        if len(body_text) > 80000:
            body_text = body_text[:80000] + "\n[内容过长，已截断]"
    else:
        raise ValueError("无法定位文章正文，链接可能不是标准公众号文章")

    if not body_text.strip():
        raise ValueError("正文内容为空")

    # 5. 摘要（meta description）
    description = ""
    meta_desc = soup.select_one("meta[name='description']")
    if meta_desc:
        description = meta_desc.get("content", "")

    return {
        "title": title,
        "author": author,
        "date": pub_date,
        "description": description,
        "content": body_text,
        "url": url,
        "source": "微信公众号",
    }


def is_wechat_url(url):
    """判断链接是否为公众号文章"""
    patterns = [
        r"mp\.weixin\.qq\.com/s/",
        r"mp\.weixin\.qq\.com/s\?",
        r"weixin\.qq\.com/",
    ]
    return any(re.search(p, url) for p in patterns)
