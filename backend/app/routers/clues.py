"""线索路由：线索管理、采集、分析

基于 news-extractor skill 的反爬策略：
- curl_cffi: 浏览器指纹模拟，绕过反爬检测
- tenacity: 智能重试机制（3次重试，指数退避）
- parsel: XPath 解析，比 BeautifulSoup 更高效
"""
import json
import asyncio
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import time
import random
import re
import logging
from urllib.parse import quote_plus, urlparse
from typing import Optional, List

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from starlette.concurrency import run_in_threadpool
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from app.core.config import get_settings
from app.database import get_db
from app.models.article import Article
from app.models.clue import Clue
from app.models.user import User
from app.routers.auth import get_current_user

settings = get_settings()
router = APIRouter(prefix="/api/clues", tags=["Clues"])
logger = logging.getLogger(__name__)


def _can_view_all_clues(user: User) -> bool:
    """管理员可以查看全站线索，其余账号只看自己的线索。"""
    return user.role == "admin"


def _scope_clue_query(query, user: User):
    """按当前账号隔离线索数据，避免不同账号互相看到线索。"""
    if _can_view_all_clues(user):
        return query
    return query.filter(Clue.creator_id == user.id)


def _get_accessible_clue(db: Session, clue_id: int, user: User) -> Clue:
    clue = _scope_clue_query(db.query(Clue).filter(Clue.id == clue_id), user).first()
    if not clue:
        raise HTTPException(status_code=404, detail="线索不存在")
    return clue


# =============================================================================
# curl_cffi 浏览器指纹会话（来自 news-extractor skill）
# =============================================================================

def _create_session() -> cffi_requests.Session:
    """创建带浏览器指纹的 HTTP 会话，模拟 Chrome 浏览器。"""
    session = cffi_requests.Session(impersonate="chrome")
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    })
    return session


# 每个线程独立会话，避免并发采集时共享 curl_cffi Session。
_session_local = threading.local()


def _get_session() -> cffi_requests.Session:
    """获取当前线程的浏览器会话。"""
    session = getattr(_session_local, "session", None)
    if session is None:
        session = _create_session()
        _session_local.session = session
    return session


# =============================================================================
# tenacity 重试策略（来自 news-extractor skill）
# =============================================================================

def _is_retryable(exc: Exception) -> bool:
    """判断异常是否可重试。"""
    if isinstance(exc, (cffi_requests.errors.RequestsError,
                        cffi_requests.errors.ConnectionError)):
        return True
    s = str(exc)
    retryable_keywords = ["timeout", "timed out", "connection", "reset", "503", "502", "429"]
    return any(kw in s.lower() for kw in retryable_keywords)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(cffi_requests.errors.RequestsError),
    reraise=True,
)
def _safe_get(url: str, params: dict = None, headers: dict = None, timeout: int = 10) -> cffi_requests.Response:
    """带重试的安全 GET 请求（curl_cffi 浏览器指纹）。"""
    session = _get_session()
    resp = session.get(url, params=params, headers=headers, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return resp


# =============================================================================
# 信源配置（精简版：只保留最稳定的信源）
# =============================================================================

# RSS/API 源（只保留当前实现中具备有效抓取地址的来源）
_RSS_FEEDS: dict[str, dict] = {
    "tencent": {
        "name": "腾讯新闻",
        "feeds": [
            "https://pacaio.match.qq.com/irs/rcd?cid=56&ext=news&token=prode&page=0",
        ],
        "hot": "https://news.qq.com/",
        "category": "新闻门户",
    },
    "netease": {
        "name": "网易新闻",
        "feeds": [],
        "hot": "https://news.163.com/",
        "category": "新闻门户",
    },
    "sina": {
        "name": "新浪新闻",
        "feeds": [
            "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=20&page=1",
        ],
        "hot": "https://news.sina.com.cn/",
        "category": "新闻门户",
    },
}

# API/JSON 源（2个最稳定的）
_API_FEEDS: dict[str, dict] = {
    "zhihu_daily": {
        "url": "https://news-at.zhihu.com/api/4/news/latest",
        "name": "知乎日报",
        "category": "综合",
        "type": "zhihu",
    },
    "bilibili_hot": {
        "url": "https://api.bilibili.com/x/web-interface/popular?ps=20",
        "name": "B站热门",
        "category": "娱乐",
        "type": "bilibili",
    },
}

# 科技媒体源：通过 Bing site: 定向搜索实现，确保选择后能按关键词返回结果。
_TECH_SEARCH_SITES: dict[str, dict] = {
    "ithome": {"name": "IT之家", "domain": "ithome.com"},
    "36kr": {"name": "36氪", "domain": "36kr.com"},
    "sspai": {"name": "少数派", "domain": "sspai.com"},
    "oschina": {"name": "开源中国", "domain": "oschina.net"},
    "geekpark": {"name": "极客公园", "domain": "geekpark.net"},
}

# 搜索源（统一走 Bing HTML + RSS 兜底；站点类源使用 site: 定向查询）
_SEARCH_SOURCES: dict[str, dict] = {
    "bing_search": {"name": "Bing搜索", "type": "bing_html_rss", "category": "综合搜索"},
    **{
        key: {"name": config["name"], "type": "bing_site_search", "category": "科技媒体"}
        for key, config in _TECH_SEARCH_SITES.items()
    },
    "social": {"name": "社交平台搜索", "type": "bing_site_search", "category": "社交媒体"},
    "government": {"name": "政府网站搜索", "type": "bing_site_search", "category": "政府公告"},
}


# =============================================================================
# 关键词处理函数
# =============================================================================

def _split_keywords(keyword: str) -> List[str]:
    """拆分中文关键词为2字以上的词组，用于模糊匹配。"""
    kw = keyword.strip()
    if not kw:
        return []
    if all(ord(c) < 128 for c in kw):
        return [kw.lower()]
    parts = [kw]
    for i in range(len(kw) - 1):
        for length in [2, 3, 4]:
            if i + length <= len(kw):
                chunk = kw[i:i+length]
                if len(chunk) >= 2 and chunk not in parts:
                    parts.append(chunk)
    return parts


def _title_matches_keyword(title: str, keyword: str) -> bool:
    """检查标题是否包含关键词。"""
    if not keyword or not title:
        return False
    kw = keyword.strip().lower()
    title_lower = title.lower()
    if any(ord(c) > 127 for c in kw):
        return kw in title_lower
    try:
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', title_lower))
    except re.error:
        return kw in title_lower


# ── Bing URL 解析 & 辅助 ─────────────────────────────────────
def _resolve_bing_url(href: str) -> str:
    """解析 Bing 搜索结果中的真实跳转 URL。"""
    if not href:
        return ""
    try:
        from urllib.parse import parse_qs, unquote
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        for param in ["url", "targetUrl", "u"]:
            if param in qs:
                val = unquote(qs[param][0])
                if val.startswith("http"):
                    return val
        if href.startswith("http"):
            return unquote(href)
    except Exception:
        pass
    return href if href.startswith("http") else ""


def _extract_domain(url: str) -> str:
    """从 URL 提取域名。"""
    try:
        return urlparse(url).netloc.replace("www.", "").replace("m.", "")
    except Exception:
        return url


_DOMAIN_SOURCE_NAMES: dict[str, str] = {
    "baike.baidu.com": "百度百科",
    "zhidao.baidu.com": "百度知道",
    "baijiahao.baidu.com": "百家号",
    "ithome.com": "IT之家",
    "36kr.com": "36氪",
    "sspai.com": "少数派",
    "oschina.net": "开源中国",
    "geekpark.net": "极客公园",
    "zhihu.com": "知乎",
    "weibo.com": "微博",
    "xiaohongshu.com": "小红书",
    "bilibili.com": "B站",
    "qq.com": "腾讯新闻",
    "sina.com.cn": "新浪新闻",
    "163.com": "网易新闻",
    "thepaper.cn": "澎湃新闻",
    "gov.cn": "政府网站",
}


def _source_name_from_url(url: str) -> str:
    """根据结果 URL 识别真实来源站点，避免把搜索通道显示成来源。"""
    domain = _extract_domain(url).lower()
    if not domain:
        return ""
    for key, name in _DOMAIN_SOURCE_NAMES.items():
        if domain == key or domain.endswith(f".{key}"):
            return name
    return domain


def _is_weibo_url(url: str) -> bool:
    """判断是否为微博站内链接。"""
    if not url or not isinstance(url, str):
        return False
    low = url.lower()
    if not low.startswith("http"):
        return False
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return "weibo.com" in host or host.endswith("weibo.cn") or ".weibo.cn" in host
    except Exception:
        return "weibo.com" in low or "weibo.cn" in low


def _weibo_site_search_url(keyword: str) -> str:
    """微博官方站内搜索 URL。"""
    from urllib.parse import quote
    q = (keyword or "").strip()
    return f"https://s.weibo.com/weibo?q={quote(q)}" if q else "https://s.weibo.com/"


def _filter_and_rank_results(results: List[dict], keyword: str) -> List[dict]:
    """
    过滤和排序搜索结果，提高相关性（来自 ttt 项目验证策略）。
    支持空格和逗号分隔的多关键词。
    """
    if not results:
        return []

    # 分词：先逗号分割，再空格分割
    raw_kws = []
    comma_parts = [k.strip() for k in keyword.split(',')]
    for part in comma_parts:
        space_parts = [k.strip() for k in part.split(' ')]
        raw_kws.extend(space_parts)
    keywords = list(set([k for k in raw_kws if k]))
    if not keywords:
        keywords = [keyword]

    scored = []
    for result in results:
        score = 0
        raw_title = (result.get('title') or '').strip()
        title = raw_title.lower()
        content = (result.get('snippet') or result.get('content') or '').lower()

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in title:
                score += 5
            if kw_lower in content:
                score += 2

        content_len = len(content)
        if content_len > 50:
            score += 1
        elif content_len == 0:
            score += 1

        # 来源可靠性加分
        source = (result.get('source') or '').lower()
        reliable = ['新浪', '腾讯', '网易', '央视', '人民日报', '新华社', '澎湃', '凤凰网', '微博', 'it之家', '36氪']
        for r in reliable:
            if r.lower() in source:
                score += 3
                break

        if '微博' in source or 'weibo' in source:
            score += 2
        if _is_weibo_url(result.get('url', '') or result.get('source_url', '')):
            score += 4

        # 搜索引擎已按关键词检索：有标题则至少保留
        if score < 1 and raw_title:
            score = 1

        if score >= 1:
            result['relevance_score'] = score
            scored.append(result)

    scored.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    return scored


def _calculate_relevance(keyword: str, title: str, snippet: str = "") -> float:
    """计算关键词匹配度分数（0-100）。"""
    if not keyword or not title:
        return 0.0
    kw = keyword.strip().lower()
    title_lower = title.lower()
    snippet_lower = (snippet or "").lower()
    if kw in title_lower:
        return 100.0
    sub_kws = _split_keywords(kw)
    title_score = 0.0
    for sub in sub_kws:
        if sub in title_lower:
            weight = min(len(sub) / len(kw), 1.0)
            title_score = max(title_score, 60.0 + weight * 20.0)
    snippet_score = 0.0
    if kw in snippet_lower:
        snippet_score = 40.0
    else:
        for sub in sub_kws:
            if sub in snippet_lower:
                weight = min(len(sub) / len(kw), 1.0)
                snippet_score = max(snippet_score, 20.0 + weight * 10.0)
    return max(title_score, snippet_score)


def _filter_by_keyword(items: List[dict], keyword: str, min_score: float = 20.0) -> List[dict]:
    """过滤并按关键词匹配度排序结果。"""
    if not keyword:
        return items
    scored = []
    for item in items:
        score = _calculate_relevance(keyword, item.get("title", ""), item.get("snippet", ""))
        if score >= min_score:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]


# =============================================================================
# RSS 采集（curl_cffi 浏览器指纹）
# =============================================================================

def _fetch_rss_feed(source: str, keyword: str = "", max_results: int = 10) -> List[dict]:
    """从 RSS/API 源获取新闻线索。支持 XML RSS、ATOM、JSON API 三种格式。"""
    config = _RSS_FEEDS.get(source)
    if not config:
        return []

    feed_urls = config.get("feeds", [])
    if not feed_urls:
        return []  # 无 feed 的源（如微博）走搜索兜底

    results: List[dict] = []
    for feed_url in feed_urls:
        try:
            time.sleep(random.uniform(0.5, 1.5))
            resp = _safe_get(feed_url, timeout=10)

            # 尝试 XML RSS/ATOM 解析
            xml_items = _parse_xml_feed(resp, source, config, keyword, max_results)
            if xml_items:
                results = xml_items
                break

            # 兜底：尝试 JSON API 解析（如新浪、腾讯）
            json_items = _parse_json_feed(resp, source, config, keyword, max_results)
            if json_items:
                results = json_items
                break

            # 最终兜底：HTML中提取链接
            html_items = _parse_html_fallback(resp, source, config, keyword, max_results)
            if html_items:
                results = html_items
                break

        except Exception as e:
            logger.warning(f"RSS fetch error [{source}@{feed_url}]: {e}")
            continue

    return results[:max_results]


# ── RSS/API 解析辅助函数 ─────────────────────────────────────

def _parse_xml_feed(resp, source: str, config: dict, keyword: str, max_results: int) -> List[dict]:
    """解析 XML RSS/ATOM 格式的 feed。"""
    try:
        root = ET.fromstring(resp.content)
        results: List[dict] = []
        content_type = resp.headers.get("content-type", "")

        # 检测 ATOM
        is_atom = "atom" in content_type.lower() or "http://www.w3.org/2005/Atom" in resp.text[:500]
        entries = []

        if is_atom:
            ns = "http://www.w3.org/2005/Atom"
            entries = root.findall(f"{{{ns}}}entry")
            for entry in entries[:max_results * 2]:
                title_el = entry.find(f"{{{ns}}}title")
                link_el = entry.find(f"{{{ns}}}link") or entry.find(f'{{{ns}}}link[@rel="alternate"]')
                summary_el = entry.find(f"{{{ns}}}summary") or entry.find(f"{{{ns}}}content")
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.get("href") if link_el is not None else ""
                summary = re.sub(r"<[^>]+>", "", summary_el.text or "")[:300] if summary_el is not None else ""
                if title and len(title) >= 5 and link:
                    if _match_keyword(title, summary, keyword):
                        results.append({
                            "title": title, "url": link, "snippet": summary,
                            "source": config["name"], "category": config["category"], "pub_date": "",
                        })
                        if len(results) >= max_results:
                            break
        else:
            # RSS 2.0
            entries = root.findall(".//item")
            for entry in entries[:max_results * 2]:
                title_el = entry.find("title")
                link_el = entry.find("link")
                desc_el = entry.find("description") or entry.find("{http://purl.org/rss/1.0/modules/content/}encoded")
                pub_date_el = entry.find("pubDate")
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                pub_date = pub_date_el.text.strip() if pub_date_el is not None and pub_date_el.text else ""
                if desc:
                    desc = re.sub(r"<[^>]+>", "", desc).strip()[:300]
                if title and len(title) >= 5 and link:
                    if _match_keyword(title, desc, keyword):
                        results.append({
                            "title": title, "url": link, "snippet": desc,
                            "source": config["name"], "category": config["category"], "pub_date": pub_date,
                        })
                        if len(results) >= max_results:
                            break

        if results:
            logger.info(f"XML [{source}] 获取 {len(results)} 条")
        return results
    except ET.ParseError:
        return []
    except Exception as e:
        logger.debug(f"XML parse error [{source}]: {e}")
        return []


def _parse_json_feed(resp, source: str, config: dict, keyword: str, max_results: int) -> List[dict]:
    """解析 JSON API 格式的 feed（新浪、腾讯等）。"""
    try:
        data = resp.json()
        results: List[dict] = []
        items = data.get("result", {}).get("data", []) or data.get("data", []) or data.get("list", []) or []
        for item in items[:max_results * 2]:
            title = item.get("title", "")
            url = item.get("url", "") or item.get("link", "") or item.get("article_url", "")
            intro = (item.get("intro", "") or item.get("desc", "") or item.get("abstract", ""))[:300]
            if title and len(title) >= 5 and url:
                if _match_keyword(title, intro, keyword):
                    results.append({
                        "title": title, "url": url, "snippet": intro,
                        "source": config["name"], "category": config["category"], "pub_date": "",
                    })
                    if len(results) >= max_results:
                        break
        if results:
            logger.info(f"JSON [{source}] 获取 {len(results)} 条")
        return results
    except Exception as e:
        logger.debug(f"JSON parse error [{source}]: {e}")
        return []


def _parse_html_fallback(resp, source: str, config: dict, keyword: str, max_results: int) -> List[dict]:
    """从 HTML 中提取链接作为最终兜底。"""
    try:
        soup = BeautifulSoup(resp.content, "html.parser")
        results: List[dict] = []
        for a in soup.select("a[href]"):
            text = a.get_text(" ", strip=True)
            href = (a.get("href") or "").strip()
            if not text or len(text) < 5 or not href.startswith("http"):
                continue
            if _match_keyword(text, "", keyword):
                results.append({
                    "title": text, "url": href, "snippet": "",
                    "source": config["name"], "category": config["category"], "pub_date": "",
                })
                if len(results) >= max_results:
                    break
        if results:
            logger.info(f"HTML [{source}] 获取 {len(results)} 条")
        return results
    except Exception as e:
        logger.debug(f"HTML fallback error [{source}]: {e}")
        return []


def _match_keyword(title: str, snippet: str, keyword: str) -> bool:
    """三级匹配：精确标题匹配 → 子词/摘要评分≥30 → 丢弃。无关键词时全通过。"""
    if not keyword:
        return True
    if _title_matches_keyword(title, keyword):
        return True
    score = _calculate_relevance(keyword, title, snippet)
    return score >= 30


# =============================================================================
# API 采集（curl_cffi 浏览器指纹）
# =============================================================================

def _fetch_api_feed(source: str, keyword: str = "", max_results: int = 10) -> List[dict]:
    """从 API/JSON 源获取新闻线索。"""
    config = _API_FEEDS.get(source)
    if not config:
        return []

    results: List[dict] = []
    try:
        time.sleep(random.uniform(0.5, 1.5))
        extra_headers = {}
        if config["type"] == "bilibili":
            extra_headers = {"Referer": "https://www.bilibili.com/", "Accept": "application/json"}

        resp = _safe_get(config["url"], headers=extra_headers, timeout=10)
        data = resp.json()

        if config["type"] == "zhihu":
            stories = data.get("stories", [])
            for story in stories:
                title = story.get("title", "")
                if not title:
                    continue
                results.append({
                    "title": title,
                    "url": story.get("url", ""),
                    "snippet": story.get("hint", ""),
                    "source": config["name"],
                    "category": config["category"],
                    "pub_date": data.get("date", ""),
                })
                if len(results) >= max_results:
                    break

        elif config["type"] == "bilibili":
            videos = data.get("data", {}).get("list", [])
            for v in videos:
                title = v.get("title", "")
                if not title:
                    continue
                bvid = v.get("bvid", "")
                stat = v.get("stat", {})
                results.append({
                    "title": title,
                    "url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
                    "snippet": f"播放:{stat.get('view', 0)} 弹幕:{stat.get('danmaku', 0)}",
                    "source": config["name"],
                    "category": config["category"],
                    "pub_date": str(v.get("pubdate", "")),
                })
                if len(results) >= max_results:
                    break

        logger.info(f"API [{source}] 获取 {len(results)} 条")
        return results
    except Exception as e:
        logger.warning(f"API fetch error [{source}]: {e}")
        return []


# =============================================================================
# 搜索源采集（Bing HTML 抓取 + RSS 兜底 — 来自 ttt 项目验证策略）
# =============================================================================
# Google 在中国不可用；百度/360/搜狗/头条返回 JS 渲染页面无法抓取。
# Bing 是唯一可静态抓取的中文搜索来源。方案：优先 HTML 解析（结果更全），
# 失败时回退 RSS（更稳定），二者都在内部做关键词精确子串匹配。


def _fetch_bing_html_search(keyword: str, max_results: int = 10, match_keyword: str = "") -> List[dict]:
    """Bing HTML 页面搜索，解析 .b_algo 结果条目（来自 ttt 验证）。
    
    Args:
        keyword: 传给 Bing 的完整搜索词（可含 site: operator 等）
        match_keyword: 用于标题匹配的关键词。为空时使用 keyword。
    """
    query = keyword.strip()
    if not query:
        return []

    # 标题匹配关键词：match_keyword 传入为空时用原始 query
    match_kw = (match_keyword or keyword).strip()

    results: List[dict] = []
    try:
        time.sleep(random.uniform(1.0, 2.5))
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        resp = _safe_get(
            "https://www.bing.com/search",
            params={"q": query, "mkt": "zh-CN", "setlang": "zh-hans"},
            headers=headers, timeout=12,
        )
        soup = BeautifulSoup(resp.text, "lxml")

        # Bing 搜索结果 DOM 选择器（多个备选，兼容不同版本）
        algo_candidates = [
            soup.select("li.b_algo"),
            soup.select("ol#b_results > li.b_algo"),
            soup.select(".b_algo"),
        ]
        algo_items = []
        for candidate in algo_candidates:
            if candidate:
                algo_items = candidate
                break

        if not algo_items:
            # 降级：尝试所有 h2 下的链接
            for h2 in soup.select("h2 a[href]"):
                href = (h2.get("href") or "").strip()
                if not href.startswith("http"):
                    continue
                title = h2.get_text(" ", strip=True)
                if title and len(title) >= 4:
                    algo_items.append(h2)
            if not algo_items:
                logger.warning(f"Bing HTML [{query}]: 未找到 .b_algo 条目，页面可能已改版")
                return results

        for el in algo_items:
            if len(results) >= max_results:
                break

            # 提取标题和链接
            title_link = el.select_one("h2 a[href]")
            if title_link is None:
                continue
            href = (title_link.get("href") or "").strip()
            title = title_link.get_text(" ", strip=True)
            if not title or len(title) < 4:
                continue

            # 解析真实 URL（Bing 链接为跳转链接）
            real_url = _resolve_bing_url(href)

            # 提取摘要
            snippet = ""
            snippet_el = el.select_one(".b_caption p, .b_algoSlug, .b_lineclamp2, .b_caption .b_snippet")
            if snippet_el:
                snippet = snippet_el.get_text(" ", strip=True)[:300]

            # 精确关键词匹配（用 match_kw 而非完整 search query）
            if not _title_matches_keyword(title, match_kw):
                continue

            source_name = _source_name_from_url(real_url) or "Bing搜索"
            results.append({
                "title": title,
                "url": real_url or f"https://www.bing.com/search?q={quote_plus(query)}",
                "snippet": snippet,
                "source": source_name,
                "category": "综合",
            })

        logger.info(f"Bing HTML [{query}]: {len(results)} 条")
    except Exception as e:
        logger.warning(f"Bing HTML search error [{query}]: {e}")

    return results


def _fetch_bing_social_search(keyword: str, max_results: int = 10) -> List[dict]:
    """
    Bing 社交媒体定向搜索（来自 ttt 项目验证策略）。
    针对 weibo/zhihu/xiaohongshu 等做 site: 限定查询。
    """
    query = keyword.strip()
    if not query:
        return []

    platform_queries = [
        (f"{query} site:weibo.com", "微博"),
        (f"{query} site:zhihu.com", "知乎"),
        (f"{query} site:xiaohongshu.com", "小红书"),
    ]

    results: List[dict] = []
    for search_q, platform_name in platform_queries:
        if len(results) >= max_results:
            break
        try:
            time.sleep(random.uniform(1.5, 3.0))
            # 优先 HTML 解析（传入原关键词用于标题匹配）
            html_results = _fetch_bing_html_search(search_q, max_results=5, match_keyword=query)
            for item in html_results:
                item["source"] = platform_name
                item["category"] = "社交媒体"
                if item not in results:
                    results.append(item)
            if not html_results:
                # HTML 失败时回退 RSS
                rss_results = _fetch_bing_rss_search(search_q, max_results=5)
                for item in rss_results:
                    item["source"] = platform_name
                    item["category"] = "社交媒体"
                    if item not in results:
                        results.append(item)
        except Exception as e:
            logger.warning(f"Bing social [{platform_name}/{query}]: {e}")

    logger.info(f"Bing 社交搜索 [{query}]: {len(results)} 条")
    return results[:max_results]


def _fetch_bing_gov_search(keyword: str, max_results: int = 10) -> List[dict]:
    """Bing 政府网站搜索（site:gov.cn）。"""
    query = keyword.strip()
    if not query:
        return []

    search_q = f"{query} site:gov.cn"
    results: List[dict] = []
    try:
        time.sleep(random.uniform(1.5, 3.0))
        html_results = _fetch_bing_html_search(search_q, max_results=max_results, match_keyword=query)
        for item in html_results:
            item["source"] = "政府网站"
            item["category"] = "政府公告"
            results.append(item)

        if not html_results:
            rss_results = _fetch_bing_rss_search(search_q, max_results=max_results)
            for item in rss_results:
                item["source"] = "政府网站"
                item["category"] = "政府公告"
                results.append(item)
    except Exception as e:
        logger.warning(f"Bing gov search [{query}]: {e}")

    logger.info(f"Bing 政府搜索 [{query}]: {len(results)} 条")
    return results[:max_results]


def _fetch_bing_site_search(keyword: str, source_key: str, max_results: int = 10) -> List[dict]:
    """Bing 指定站点搜索，用于科技媒体等没有稳定公开 RSS 的来源。"""
    query = keyword.strip()
    site = _TECH_SEARCH_SITES.get(source_key)
    if not query or not site:
        return []

    site_name = site["name"]
    search_q = f"{query} site:{site['domain']}"
    results: List[dict] = []
    try:
        time.sleep(random.uniform(1.0, 2.0))
        html_results = _fetch_bing_html_search(search_q, max_results=max_results, match_keyword=query)
        for item in html_results:
            item["source"] = site_name
            item["category"] = "科技媒体"
            results.append(item)

        if not html_results:
            rss_results = _fetch_bing_rss_search(search_q, max_results=max_results)
            for item in rss_results:
                item["source"] = site_name
                item["category"] = "科技媒体"
                results.append(item)
    except Exception as e:
        logger.warning(f"Bing site search [{source_key}/{query}]: {e}")

    logger.info(f"Bing 站内搜索 [{site_name}/{query}]: {len(results)} 条")
    return results[:max_results]


def _fetch_bing_rss_search(keyword: str, max_results: int = 10) -> List[dict]:
    """Bing RSS 搜索接口（作为 HTML 抓取的兜底方案）。"""
    query = keyword.strip()
    if not query:
        return []

    results: List[dict] = []
    try:
        time.sleep(random.uniform(0.8, 2.0))
        resp = _safe_get(
            "https://www.bing.com/search",
            params={"q": query, "format": "rss", "mkt": "zh-CN"},
            timeout=10,
        )
        root = ET.fromstring(resp.text)

        for item in root.findall(".//item"):
            title_el = item.find("title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link_el = item.find("link")
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            desc_el = item.find("description")
            snippet = (desc_el.text or "").strip()[:200] if desc_el is not None else ""

            if not title:
                continue
            if not _title_matches_keyword(title, keyword.strip()):
                continue

            results.append({
                "title": title,
                "url": link,
                "snippet": snippet,
                "source": _source_name_from_url(link) or "Bing搜索",
                "category": "综合",
            })
            if len(results) >= max_results:
                break

        logger.debug(f"Bing RSS [{query}]: {len(results)} 条")
    except Exception as e:
        logger.warning(f"Bing RSS error [{query}]: {e}")

    return results


# ── 旧函数名兼容 ─────────────────────────────────────────────
_fetch_bing_search = _fetch_bing_rss_search


# =============================================================================
# 统一采集入口（增强版：RSS → API → Bing HTML → 社交 → 政府）
# =============================================================================

def _fetch_web_results(keyword: str, source: str = "all", max_results: int = 10) -> List[dict]:
    """统一采集入口：多渠道接入，支持定向搜索。"""
    query = keyword.strip()
    all_items: List[dict] = []
    is_rss_source = source in _RSS_FEEDS
    is_api_source = source in _API_FEEDS
    is_search_source = source in _SEARCH_SOURCES
    is_unknown_source = source not in ("all", "rss", "api", "search") and not is_rss_source and not is_api_source and not is_search_source

    # ── 1. RSS 源 ──
    if source in ("all", "rss") or is_rss_source:
        for rss_key in _RSS_FEEDS:
            if source not in ("all", "rss") and source != rss_key:
                continue
            try:
                all_items.extend(_fetch_rss_feed(rss_key, query, max_results))
            except Exception as e:
                logger.warning(f"RSS error [{rss_key}]: {e}")

    # ── 2. API热搜源（仅无关键词时调用）──
    if not query and (source in ("all", "api") or is_api_source):
        for api_key in _API_FEEDS:
            if source not in ("all", "api") and source != api_key:
                continue
            try:
                all_items.extend(_fetch_api_feed(api_key, "", max_results))
            except Exception as e:
                logger.warning(f"API error [{api_key}]: {e}")

    if not query:
        return all_items[:max_results]

    # 明确选择新闻门户或 API 源时，不做搜索引擎兜底，避免来源串台。
    if is_rss_source or is_api_source or source in ("rss", "api"):
        return _filter_and_rank_results(all_items, query)[:max_results]

    # ── 3a. 科技媒体定向搜索 ──
    if source in _TECH_SEARCH_SITES:
        try:
            logger.info(f"💻 科技媒体搜索 [{source}/{query}]")
            tech_items = _fetch_bing_site_search(query, source, max_results=max_results)
            all_items.extend(tech_items)
        except Exception as e:
            logger.warning(f"科技媒体搜索 error [{source}]: {e}")

    # ── 3b. weibo 专用渠道：社交搜索 + 微博站内检索 ──
    elif source == "weibo" or (is_unknown_source and "weibo" in source.lower()):
        try:
            logger.info(f"🔍 微博专用搜索 [{query}]")
            social_items = _fetch_bing_social_search(query, max_results=max_results)
            all_items.extend(social_items)
        except Exception as e:
            logger.warning(f"微博搜索 error: {e}")

    # ── 3c. government / 政务专用渠道 ──
    elif source == "government" or (is_unknown_source and "gov" in source.lower()):
        try:
            logger.info(f"🏛 政务专用搜索 [{query}]")
            gov_items = _fetch_bing_gov_search(query, max_results=max_results)
            all_items.extend(gov_items)
        except Exception as e:
            logger.warning(f"政府搜索 error: {e}")

    # ── 3d. social / zhihu / xiaohongshu 专用渠道 ──
    elif source in ("social", "zhihu", "xiaohongshu") or (is_unknown_source and any(s in source.lower() for s in ("social", "zhihu", "xiaohongshu"))):
        try:
            logger.info(f"💬 社交搜索 [{source}/{query}]")
            social_items = _fetch_bing_social_search(query, max_results=max_results)
            all_items.extend(social_items)
        except Exception as e:
            logger.warning(f"社交搜索 error: {e}")

    # ── 3e. Bing 搜索（通用/all/search）：HTML 优先 → RSS 兜底 ──
    if source in ("all", "search", "bing_search") or (is_search_source and source not in _TECH_SEARCH_SITES and not all_items) or (is_unknown_source and not all_items):
        try:
            if is_unknown_source and not all_items:
                logger.info(f"🔄 [{source}] 无直接结果，Bing HTML 搜索兜底: {query}")

            html_results = _fetch_bing_html_search(query, max_results=max_results)
            if html_results:
                all_items.extend(html_results)
            else:
                # HTML 失败，RSS 兜底
                logger.info(f"🔄 Bing HTML 无结果 [{query}]，回退 RSS")
                rss_results = _fetch_bing_rss_search(query, max_results=max_results)
                all_items.extend(rss_results)
        except Exception as e:
            logger.warning(f"Bing 搜索 error: {e}")

    # ── 4. 排序：用 ttt 验证过的评分策略 ──
    if query:
        all_items = _filter_and_rank_results(all_items, query)

    return all_items[:max_results]


async def _fetch_collection_jobs(keyword_list: List[str], channel_list: List[str], max_results: int):
    """在线程池中并发执行外部采集，避免阻塞 FastAPI 事件循环。"""
    limiter = asyncio.Semaphore(4)

    async def fetch_one(keyword: str, channel: str):
        async with limiter:
            return await run_in_threadpool(_fetch_web_results, keyword, channel, max_results)

    tasks = [fetch_one(keyword, channel) for keyword in keyword_list for channel in channel_list]
    job_keys = [(keyword, channel) for keyword in keyword_list for channel in channel_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return list(zip(job_keys, results))


# =============================================================================
# 辅助函数
# =============================================================================

def _normalize_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _ensure_source_name(source: str) -> str:
    mapping = {
        "ithome": "IT之家", "36kr": "36氪", "solidot": "奇客Solidot",
        "sspai": "少数派", "oschina": "开源中国",
        "ifanr": "爱范儿", "tmtpost": "钛媒体",
        "geekpark": "极客公园", "freebuf": "FreeBuf",
        "zhihu_daily": "知乎日报", "bilibili_hot": "B站热门",
        "bing_search": "Bing搜索", "social": "社交平台搜索",
        "government": "政府网站搜索",
    }
    return mapping.get(source, source or "全网资讯")


def _display_source_name(source: str, url: str = "") -> str:
    """序列化和入库时使用的展示来源；Bing 搜索结果优先展示真实站点。"""
    source_name = (source or "").strip()
    if source_name in ("Bing搜索", "bing_search", "全网资讯", ""):
        return _source_name_from_url(url) or _ensure_source_name(source_name)
    return _ensure_source_name(source_name)


def _score_clue(title: str, snippet: str) -> tuple:
    base = min(90.0, max(35.0, len(title.strip()) * 1.8))
    if snippet:
        base += min(10.0, len(snippet) / 80.0)
    return round(min(base, 100.0), 1), round(min(base - 5.0, 100.0), 1)


def _to_beijing(dt):
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone(timedelta(hours=8))).isoformat()


def _serialize_clue(clue: Clue) -> dict:
    status_map = {
        "new": "pending", "processing": "pending", "verified": "processed",
        "pending": "pending", "processed": "processed", "archived": "archived",
    }
    try:
        keywords = json.loads(clue.keywords) if clue.keywords else []
    except Exception:
        keywords = [k.strip() for k in (clue.keywords or "").split(",") if k.strip()]
    return {
        "id": clue.id, "title": clue.title, "content": clue.content,
        "source": _display_source_name(clue.source or "", clue.source_url or ""),
        "source_url": clue.source_url or "",
        "keywords": keywords,
        "news_value_score": clue.news_value_score or 0,
        "propagation_potential": clue.propagation_potential or 0,
        "status": status_map.get(clue.status or "", clue.status or "pending"),
        "created_at": _to_beijing(clue.created_at) if clue.created_at else "",
        "processed_at": _to_beijing(clue.processed_at) if clue.processed_at else None,
        "category": clue.category or "",
        "creator_id": clue.creator_id,
    }


# =============================================================================
# Pydantic 模型
# =============================================================================

class ClueCreate(BaseModel):
    title: str
    content: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    keywords: Optional[List[str]] = None


class ClueUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    keywords: Optional[List[str]] = None
    status: Optional[str] = None
    news_value_score: Optional[float] = None
    propagation_potential: Optional[float] = None


class SearchInfoRequest(BaseModel):
    keyword: str = ""
    source: Optional[str] = "all"
    max_results: int = 15
    exact_match: bool = False
    engine: Optional[str] = None


def _parse_datetime_filter(value: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if end_of_day and "T" not in raw and len(raw) <= 10:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    except ValueError:
        return None


# =============================================================================
# API 路由
# =============================================================================

@router.get("")
async def list_clues(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    exclude_status: Optional[str] = None,
    creator_id: Optional[int] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    search_fields: Optional[str] = None,
    search_mode: Optional[str] = "fuzzy",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取线索列表。"""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    q = _scope_clue_query(db.query(Clue), current_user)
    if status:
        q = q.filter(Clue.status == status)
    if exclude_status:
        for es in [s.strip() for s in exclude_status.split(",") if s.strip()]:
            q = q.filter(Clue.status != es)
    if category:
        q = q.filter(Clue.category == category)
    start_dt = _parse_datetime_filter(start_date)
    end_dt = _parse_datetime_filter(end_date, end_of_day=True)
    if start_dt:
        q = q.filter(Clue.created_at >= start_dt)
    if end_dt:
        q = q.filter(Clue.created_at <= end_dt)
    # 管理员可以显式筛选创建者；普通账号固定只能看自己的。
    if creator_id is not None and _can_view_all_clues(current_user):
        q = q.filter(Clue.creator_id == creator_id)

    if search:
        keywords = [k.strip() for k in search.split(",") if k.strip()]
        if keywords:
            mode = (search_mode or "fuzzy").lower()
            fields = [f.strip() for f in (search_fields or "").split(",") if f.strip()] if search_fields else []

            try:
                if mode == "exact":
                    for kw in keywords:
                        conditions = []
                        if not fields or "title" in fields:
                            conditions.append(Clue.title == kw)
                        if not fields or "content" in fields:
                            conditions.append(Clue.content == kw)
                        if not fields or "keywords" in fields:
                            conditions.append(Clue.keywords.like(f"%{kw}%"))
                        if not fields or "source" in fields:
                            conditions.append(Clue.source == kw)
                        if not fields or "category" in fields:
                            conditions.append(Clue.category == kw)
                        if conditions:
                            q = q.filter(or_(*conditions))
                elif mode == "smart":
                    from sqlalchemy import case
                    score_cases = []
                    for kw in keywords:
                        like_kw = f"%{kw}%"
                        if not fields or "title" in fields:
                            score_cases.append((Clue.title.ilike(like_kw), 10))
                            score_cases.append((Clue.title == kw, 50))
                        if not fields or "content" in fields:
                            score_cases.append((Clue.content.ilike(like_kw), 5))
                        if not fields or "keywords" in fields:
                            score_cases.append((Clue.keywords.ilike(like_kw), 8))
                        if not fields or "source" in fields:
                            score_cases.append((Clue.source.ilike(like_kw), 3))

                    if score_cases:
                        try:
                            score_expr = case(*score_cases, else_=0).label("relevance_score")
                            conditions = [c[0] for c in score_cases]
                            q = q.filter(or_(*conditions))
                            q = q.order_by(desc(score_expr))
                        except Exception:
                            for kw in keywords:
                                like_kw = f"%{kw}%"
                                q = q.filter(Clue.title.ilike(like_kw) | Clue.content.ilike(like_kw))
                else:
                    for kw in keywords:
                        like_kw = f"%{kw}%"
                        conditions = []
                        if not fields or "title" in fields:
                            conditions.append(Clue.title.ilike(like_kw))
                        if not fields or "content" in fields:
                            conditions.append(Clue.content.ilike(like_kw))
                        if not fields or "keywords" in fields:
                            conditions.append(Clue.keywords.ilike(like_kw))
                        if not fields or "source" in fields:
                            conditions.append(Clue.source.ilike(like_kw))
                        if not fields or "category" in fields:
                            conditions.append(Clue.category.ilike(like_kw))
                        if conditions:
                            q = q.filter(or_(*conditions))
            except Exception as e:
                logger.error(f"搜索异常: {str(e)[:200]}")
                like = f"%{keywords[0]}%"
                q = q.filter(Clue.title.ilike(like) | Clue.content.ilike(like))

    total = q.count()
    items = q.order_by(desc(Clue.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 200, "data": [_serialize_clue(item) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get("/sources")
async def list_sources():
    """返回实际可用信源列表。

    只暴露当前采集逻辑可以直接返回线索的来源：
    - RSS 源必须有 feed URL，避免把仅有首页但无法稳定解析的来源展示给前端。
    - API 源保留可直接请求的 JSON 接口。
    - 搜索源保留后端已实现分发逻辑的搜索方向。
    """
    sources = []
    for key, config in _RSS_FEEDS.items():
        feeds = config.get("feeds", [])
        if not feeds:
            continue
        sources.append({"key": key, "name": config["name"], "type": "rss", "category": config["category"], "url": feeds[0], "status": "active"})
    for key, config in _API_FEEDS.items():
        sources.append({"key": key, "name": config["name"], "type": "api", "category": config["category"], "url": config["url"], "status": "active"})
    for key, config in _SEARCH_SOURCES.items():
        sources.append({"key": key, "name": config["name"], "type": "search", "category": config.get("category", "综合"), "url": "", "status": "active"})
    return {"code": 200, "data": {"rss": [s for s in sources if s["type"] == "rss"], "api": [s for s in sources if s["type"] == "api"], "search": [s for s in sources if s["type"] == "search"], "all": sources}}


@router.post("/sources/verify")
async def verify_source(body: dict):
    """验证单个信源是否可访问。"""
    url = (body.get("url") or "").strip()
    source_type = body.get("type", "rss")
    if not url:
        raise HTTPException(status_code=400, detail="url不能为空")
    try:
        start = time.time()
        resp = _safe_get(url, timeout=8)
        elapsed = round((time.time() - start) * 1000)
        content_type = resp.headers.get("content-type", "")
        is_valid = False
        if source_type == "rss":
            is_valid = "xml" in content_type or "<rss" in resp.text or "<feed" in resp.text
        elif source_type == "api":
            try:
                resp.json()
                is_valid = True
            except Exception:
                is_valid = False
        else:
            is_valid = True
        return {"code": 200, "data": {"accessible": True, "status_code": resp.status_code, "elapsed_ms": elapsed, "content_type": content_type, "format_valid": is_valid}}
    except cffi_requests.errors.ConnectionError:
        return {"code": 200, "data": {"accessible": False, "reason": "连接失败"}}
    except cffi_requests.errors.Timeout:
        return {"code": 200, "data": {"accessible": False, "reason": "请求超时"}}
    except Exception as e:
        return {"code": 200, "data": {"accessible": False, "reason": str(e)}}


@router.get("/collect/multichannel")
@router.post("/collect/multichannel")
async def collect_multichannel(
    keywords: str = "",
    channels: str = "",
    max_results: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """多渠道并发采集新闻线索。"""
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    channel_list = [c.strip() for c in channels.split(",") if c.strip()] if channels else ["all"]

    if not keyword_list:
        raise HTTPException(status_code=400, detail="关键词不能为空")

    logger.info(f"🔍 开始采集 | 关键词: {keyword_list} | 渠道: {channel_list}")

    items: List[dict] = []
    fetch_errors: List[str] = []
    successful_sources: List[str] = []
    total_raw = 0

    fetch_jobs = await _fetch_collection_jobs(keyword_list, channel_list, max_results)
    for (_, ch), result in fetch_jobs:
        if isinstance(result, Exception):
            fetch_errors.append(f"{ch}: {str(result)[:50]}")
            logger.error(f"❌ {ch} 采集失败: {result}")
            continue
        total_raw += len(result)
        items.extend(result)
        if result:
            successful_sources.append(f"{ch}({len(result)}条)")
            logger.info(f"✅ {ch} 采集成功，获取{len(result)}条")
        else:
            fetch_errors.append(f"{ch}: 无结果")
            logger.warning(f"⚠️ {ch} 无结果")

    # 入库
    created = []
    try:
        for item in items[:max_results]:
            title = str(item.get("title", "")).strip()
            url = _normalize_url(str(item.get("url", "")))
            snippet = str(item.get("snippet", ""))[:300]
            category = str(item.get("category", ""))
            source = _display_source_name(str(item.get("source", "")), url)

            news_score, prop_score = _score_clue(title, snippet)
            clue = Clue(
                title=title, content=snippet or title,
                source=source, source_url=url,
                keywords=json.dumps(keyword_list, ensure_ascii=False),
                status="pending",
                news_value_score=news_score, propagation_potential=prop_score,
                creator_id=current_user.id,
                collected_by=current_user.nickname or current_user.full_name or current_user.username,
                category=category,
                processed_at=datetime.now(timezone(timedelta(hours=8))),
            )
            db.add(clue)
            created.append(clue)

        db.commit()
        for clue in created:
            db.refresh(clue)
    except Exception as e:
        logger.error(f"❌ 数据库错误: {e}")
        db.rollback()
        created = []

    if created:
        message = f"✅ 成功采集 {len(created)} 条线索"
        if successful_sources:
            message += f"（来源: {'、'.join(successful_sources[:3])}）"
        status_code = 200
    elif total_raw > 0:
        message = "⚠️ 采集到内容但入库失败"
        status_code = 200
    else:
        message = f"❌ 采集失败。失败原因: {'; '.join(fetch_errors[:3])}"
        status_code = 202

    logger.info(f"🎉 采集完成！获取{total_raw}条，入库{len(created)}条")

    return {
        "code": status_code, "message": message,
        "data": {
            "created": len(created), "fetched": total_raw,
            "items": [_serialize_clue(item) for item in created],
            "sources": successful_sources, "errors": fetch_errors[:5],
            "keywords": keyword_list, "channels": channel_list,
        },
    }


@router.post("/batch-delete")
async def batch_delete_clue(
    ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _scope_clue_query(db.query(Clue).filter(Clue.id.in_(ids)), current_user)
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return {"code": 200, "message": f"已删除 {deleted} 条"}


@router.post("/{clue_id}/search-info")
async def search_clue_info(
    clue_id: int,
    body: SearchInfoRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """基于当前线索检索相关资料，仅返回结果，不写入别人的线索库。"""
    clue = _get_accessible_clue(db, clue_id, current_user)
    keyword = (body.keyword or clue.title or "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="关键词不能为空")

    max_results = min(max(body.max_results or 15, 1), 50)
    source = body.source or "all"
    if source == "news":
        source = "all"

    results = await run_in_threadpool(_fetch_web_results, keyword, source, max_results)
    if body.exact_match:
        lowered = keyword.lower()
        results = [
            item
            for item in results
            if lowered in (item.get("title") or "").lower()
            or lowered in (item.get("snippet") or "").lower()
        ]

    return {
        "code": 200,
        "message": f"检索到 {len(results)} 条资料",
        "data": {
            "keyword": keyword,
            "source": source,
            "total": len(results),
            "results": results[:max_results],
        },
    }


@router.get("/{clue_id}")
async def get_clue(
    clue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clue = _get_accessible_clue(db, clue_id, current_user)
    return {"code": 200, "data": _serialize_clue(clue)}


@router.post("")
async def create_clue(body: ClueCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    clue = Clue(
        title=body.title, content=body.content,
        source=body.source, source_url=body.source_url,
        keywords=json.dumps(body.keywords or [], ensure_ascii=False),
        status="pending",
        creator_id=current_user.id,
    )
    clue.news_value_score, clue.propagation_potential = _score_clue(body.title, body.content)
    db.add(clue)
    db.commit()
    db.refresh(clue)
    return {"code": 200, "message": "创建成功", "data": _serialize_clue(clue)}


@router.put("/{clue_id}")
async def update_clue(
    clue_id: int,
    body: ClueUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clue = _get_accessible_clue(db, clue_id, current_user)
    payload = body.model_dump(exclude_none=True)
    if "keywords" in payload:
        payload["keywords"] = json.dumps(payload["keywords"] or [], ensure_ascii=False)
    for k, v in payload.items():
        setattr(clue, k, v)
    db.commit()
    db.refresh(clue)
    return {"code": 200, "message": "更新成功", "data": _serialize_clue(clue)}


@router.delete("/{clue_id}")
async def delete_clue(
    clue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clue = _get_accessible_clue(db, clue_id, current_user)
    db.delete(clue)
    db.commit()
    return {"code": 200, "message": "删除成功"}


@router.post("/{clue_id}/analyze")
async def analyze_clue(
    clue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clue = _get_accessible_clue(db, clue_id, current_user)
    score, prop = _score_clue(clue.title, clue.content or "")
    clue.news_value_score = score
    clue.propagation_potential = prop
    clue.processed_at = datetime.now(timezone.utc)
    clue.status = "processed"
    db.commit()
    db.refresh(clue)
    return {"code": 200, "message": "分析完成", "data": {"clue_id": clue_id, "news_value_score": score, "propagation_potential": prop}}
