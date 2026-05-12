"""线索路由：线索管理、采集、分析

基于 news-extractor skill 的反爬策略：
- curl_cffi: 浏览器指纹模拟，绕过反爬检测
- tenacity: 智能重试机制（3次重试，指数退避）
- parsel: XPath 解析，比 BeautifulSoup 更高效
"""
import json
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
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from app.core.config import get_settings
from app.database import get_db
from app.models.article import Article
from app.models.clue import Clue

settings = get_settings()
router = APIRouter(prefix="/api/clues", tags=["Clues"])
logger = logging.getLogger(__name__)


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


# 全局会话（复用连接池）
_browser_session: Optional[cffi_requests.Session] = None


def _get_session() -> cffi_requests.Session:
    """获取全局浏览器会话。"""
    global _browser_session
    if _browser_session is None:
        _browser_session = _create_session()
    return _browser_session


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

# RSS 源（3个最稳定的）
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
    "ifeng": {
        "name": "凤凰网",
        "feeds": [],
        "hot": "https://news.ifeng.com/",
        "category": "新闻门户",
    },
    "thepaper": {
        "name": "澎湃新闻",
        "feeds": [],
        "hot": "https://www.thepaper.cn/",
        "category": "新闻门户",
    },
    "weibo": {
        "name": "微博",
        "feeds": [],
        "hot": "https://s.weibo.com/weibo?q={keyword}",
        "category": "社交媒体",
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

# 搜索源（仅 Bing RSS，其余中文搜索引擎返回 JS 渲染页面无法抓取）
_SEARCH_SOURCES: dict[str, dict] = {
    "bing_search": {"name": "Bing搜索", "type": "bing_rss"},
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


def _normalize_for_dedup(title: str) -> str:
    """标准化标题用于去重。"""
    if not title:
        return ""
    return re.sub(r'\s+', ' ', title.strip()).lower()


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

            source_name = _extract_domain(real_url) if real_url else "Bing搜索"
            results.append({
                "title": title,
                "url": real_url or f"https://www.bing.com/search?q={quote_plus(query)}",
                "snippet": snippet,
                "source": "Bing搜索",
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
                "source": "Bing搜索",
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
    seen_titles: set = set()

    # ── 1. RSS 源 ──
    if source in ("all", "rss") or source in _RSS_FEEDS:
        for rss_key in _RSS_FEEDS:
            if source not in ("all", "rss") and source != rss_key:
                continue
            try:
                for item in _fetch_rss_feed(rss_key, query, max_results):
                    t = item.get("title", "")
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        all_items.append(item)
            except Exception as e:
                logger.warning(f"RSS error [{rss_key}]: {e}")

    # ── 2. API热搜源（仅无关键词时调用）──
    if not query and (source in ("all", "api") or source in _API_FEEDS):
        for api_key in _API_FEEDS:
            if source not in ("all", "api") and source != api_key:
                continue
            try:
                for item in _fetch_api_feed(api_key, "", max_results):
                    t = item.get("title", "")
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        all_items.append(item)
            except Exception as e:
                logger.warning(f"API error [{api_key}]: {e}")

    # ── 3. 定向渠道分发 ──
    has_explicit_source = source not in ("all", "rss", "api", "search") and source not in _SEARCH_SOURCES

    if not query:
        return all_items[:max_results]

    # ── 3a. weibo 专用渠道：社交搜索 + 微博站内检索 ──
    if source == "weibo" or (has_explicit_source and "weibo" in source.lower()):
        try:
            logger.info(f"🔍 微博专用搜索 [{query}]")
            social_items = _fetch_bing_social_search(query, max_results=max_results)
            for item in social_items:
                t = item.get("title", "")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    all_items.append(item)
        except Exception as e:
            logger.warning(f"微博搜索 error: {e}")

    # ── 3b. government / 政务专用渠道 ──
    elif source == "government" or (has_explicit_source and "gov" in source.lower()):
        try:
            logger.info(f"🏛 政务专用搜索 [{query}]")
            gov_items = _fetch_bing_gov_search(query, max_results=max_results)
            for item in gov_items:
                t = item.get("title", "")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    all_items.append(item)
        except Exception as e:
            logger.warning(f"政府搜索 error: {e}")

    # ── 3c. social / zhihu / xiaohongshu 专用渠道 ──
    elif source in ("social", "zhihu", "xiaohongshu") or (has_explicit_source and any(s in source.lower() for s in ("social", "zhihu", "xiaohongshu"))):
        try:
            logger.info(f"💬 社交搜索 [{source}/{query}]")
            social_items = _fetch_bing_social_search(query, max_results=max_results)
            for item in social_items:
                t = item.get("title", "")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    all_items.append(item)
        except Exception as e:
            logger.warning(f"社交搜索 error: {e}")

    # ── 3d. Bing 搜索（通用/all/search）：HTML 优先 → RSS 兜底 ──
    if source in ("all", "search") or source in _SEARCH_SOURCES or (has_explicit_source and not all_items):
        try:
            if has_explicit_source and not all_items:
                logger.info(f"🔄 [{source}] 无直接结果，Bing HTML 搜索兜底: {query}")

            html_results = _fetch_bing_html_search(query, max_results=max_results)
            if html_results:
                for item in html_results:
                    t = item.get("title", "")
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        all_items.append(item)
            else:
                # HTML 失败，RSS 兜底
                logger.info(f"🔄 Bing HTML 无结果 [{query}]，回退 RSS")
                rss_results = _fetch_bing_rss_search(query, max_results=max_results)
                for item in rss_results:
                    t = item.get("title", "")
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        all_items.append(item)
        except Exception as e:
            logger.warning(f"Bing 搜索 error: {e}")

    # ── 4. 排序：用 ttt 验证过的评分策略 ──
    if query:
        all_items = _filter_and_rank_results(all_items, query)

    return all_items[:max_results]


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
        "bing_search": "Bing搜索",
    }
    return mapping.get(source, source or "全网资讯")


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
        "source": clue.source or "", "source_url": clue.source_url or "",
        "keywords": keywords,
        "news_value_score": clue.news_value_score or 0,
        "propagation_potential": clue.propagation_potential or 0,
        "status": status_map.get(clue.status or "", clue.status or "pending"),
        "created_at": _to_beijing(clue.created_at) if clue.created_at else "",
        "processed_at": _to_beijing(clue.processed_at) if clue.processed_at else None,
        "category": clue.category or "",
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


# =============================================================================
# API 路由
# =============================================================================

@router.get("")
async def list_clues(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    search_fields: Optional[str] = None,
    search_mode: Optional[str] = "fuzzy",
    db: Session = Depends(get_db),
):
    """获取线索列表。"""
    q = db.query(Clue)
    if status:
        q = q.filter(Clue.status == status)

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
    """返回所有可用信源列表。"""
    sources = []
    for key, config in _RSS_FEEDS.items():
        feeds = config.get("feeds", [])
        sources.append({"key": key, "name": config["name"], "type": "rss", "category": config["category"], "url": feeds[0] if feeds else config.get("hot", ""), "status": "active" if feeds else "fallback"})
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
    db: Session = Depends(get_db),
):
    """多渠道并发采集新闻线索。"""
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    channel_list = [c.strip() for c in channels.split(",") if c.strip()] if channels else ["all"]

    if not keyword_list:
        raise HTTPException(status_code=400, detail="关键词不能为空")

    logger.info(f"🔍 开始采集 | 关键词: {keyword_list} | 渠道: {channel_list}")

    items: List[dict] = []
    seen_titles: set = set()
    fetch_errors: List[str] = []
    successful_sources: List[str] = []
    total_raw = 0

    for kw in keyword_list:
        for ch in channel_list:
            time.sleep(random.uniform(1.0, 2.0))
            try:
                results = _fetch_web_results(kw, ch, max_results)
                total_raw += len(results)
                new_count = 0
                for item in results:
                    t = item.get("title", "")
                    u = item.get("url", "")
                    norm_title = _normalize_for_dedup(t)
                    key = (norm_title, u)
                    if key in seen_titles:
                        continue
                    seen_titles.add(key)
                    items.append(item)
                    new_count += 1
                if results:
                    successful_sources.append(f"{ch}({new_count}条)")
                    logger.info(f"✅ {ch} 采集成功，新增{new_count}条")
                else:
                    fetch_errors.append(f"{ch}: 无结果")
                    logger.warning(f"⚠️ {ch} 无结果")
            except Exception as e:
                fetch_errors.append(f"{ch}: {str(e)[:50]}")
                logger.error(f"❌ {ch} 采集失败: {e}")

    # 入库
    created = []
    try:
        for item in items[:max_results]:
            title = _normalize_for_dedup(str(item.get("title", "")).strip())
            url = _normalize_url(str(item.get("url", "")))
            source = _ensure_source_name(str(item.get("source", "")))
            snippet = str(item.get("snippet", ""))[:300]
            category = str(item.get("category", ""))

            # TODO: DB 去重暂时禁用，避免误判。仅靠 seen_titles 防止同批次重复
            # existing = db.query(Clue).filter(Clue.title == title, Clue.source_url == url).first()
            # if existing:
            #     logger.info(f"⏭️ 跳过重复: {title[:50]}")
            #     continue

            news_score, prop_score = _score_clue(title, snippet)
            clue = Clue(
                title=title, content=snippet or title,
                source=source, source_url=url,
                keywords=json.dumps(keyword_list, ensure_ascii=False),
                status="pending",
                news_value_score=news_score, propagation_potential=prop_score,
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
        message = "⚠️ 采集到内容但均为重复"
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
async def batch_delete_clue(ids: List[int], db: Session = Depends(get_db)):
    db.query(Clue).filter(Clue.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"code": 200, "message": f"已删除 {len(ids)} 条"}


@router.get("/{clue_id}")
async def get_clue(clue_id: int, db: Session = Depends(get_db)):
    clue = db.query(Clue).filter(Clue.id == clue_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="线索不存在")
    return {"code": 200, "data": _serialize_clue(clue)}


@router.post("")
async def create_clue(body: ClueCreate, db: Session = Depends(get_db)):
    clue = Clue(
        title=body.title, content=body.content,
        source=body.source, source_url=body.source_url,
        keywords=json.dumps(body.keywords or [], ensure_ascii=False),
        status="pending",
    )
    clue.news_value_score, clue.propagation_potential = _score_clue(body.title, body.content)
    db.add(clue)
    db.commit()
    db.refresh(clue)
    return {"code": 200, "message": "创建成功", "data": _serialize_clue(clue)}


@router.put("/{clue_id}")
async def update_clue(clue_id: int, body: ClueUpdate, db: Session = Depends(get_db)):
    clue = db.query(Clue).filter(Clue.id == clue_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="线索不存在")
    payload = body.model_dump(exclude_none=True)
    if "keywords" in payload:
        payload["keywords"] = json.dumps(payload["keywords"] or [], ensure_ascii=False)
    for k, v in payload.items():
        setattr(clue, k, v)
    db.commit()
    db.refresh(clue)
    return {"code": 200, "message": "更新成功", "data": _serialize_clue(clue)}


@router.delete("/{clue_id}")
async def delete_clue(clue_id: int, db: Session = Depends(get_db)):
    clue = db.query(Clue).filter(Clue.id == clue_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="线索不存在")
    db.delete(clue)
    db.commit()
    return {"code": 200, "message": "删除成功"}


@router.post("/{clue_id}/analyze")
async def analyze_clue(clue_id: int, db: Session = Depends(get_db)):
    clue = db.query(Clue).filter(Clue.id == clue_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="线索不存在")
    score, prop = _score_clue(clue.title, clue.content or "")
    clue.news_value_score = score
    clue.propagation_potential = prop
    clue.processed_at = datetime.now(timezone.utc)
    clue.status = "processed"
    db.commit()
    db.refresh(clue)
    return {"code": 200, "message": "分析完成", "data": {"clue_id": clue_id, "news_value_score": score, "propagation_potential": prop}}
