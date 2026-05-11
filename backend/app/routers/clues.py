"""线索路由：线索管理、采集、分析"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import time
from urllib.parse import urlparse, parse_qs, unquote, quote_plus
from typing import Optional, List
import re
import concurrent.futures

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.core.config import get_settings
from app.database import get_db
from app.models.article import Article
from app.models.clue import Clue

settings = get_settings()
router = APIRouter(prefix="/api/clues", tags=["Clues"])

# RSS 源配置（保留稳定可用的中文 RSS 源）
_RSS_FEEDS: dict[str, dict] = {
    "ithome": {
        "url": "https://www.ithome.com/rss/",
        "name": "IT之家",
        "category": "科技",
    },
    "36kr": {
        "url": "https://36kr.com/feed",
        "name": "36氪",
        "category": "科技",
    },
    "sspai": {
        "url": "https://sspai.com/feed",
        "name": "少数派",
        "category": "科技",
    },
    "oschina": {
        "url": "https://www.oschina.net/news/rss",
        "name": "开源中国",
        "category": "科技",
    },
    "solidot": {
        "url": "https://www.solidot.org/index.rss",
        "name": "奇客Solidot",
        "category": "科技",
    },
    "ifanr": {
        "url": "https://www.ifanr.com/feed",
        "name": "爱范儿",
        "category": "科技",
    },
    "tmtpost": {
        "url": "https://www.tmtpost.com/rss.xml",
        "name": "钛媒体",
        "category": "科技·财经",
    },
    "geekpark": {
        "url": "https://www.geekpark.net/rss",
        "name": "极客公园",
        "category": "科技",
    },
    "freebuf": {
        "url": "https://www.freebuf.com/feed",
        "name": "FreeBuf",
        "category": "安全",
    },
}

# API/JSON 源配置（非 RSS 格式的 API 源）
_API_FEEDS: dict[str, dict] = {
    "zhihu_daily": {
        "url": "https://news-at.zhihu.com/api/4/news/latest",
        "name": "知乎日报",
        "category": "综合",
        "type": "json",
    },
    "baidu_hot": {
        "url": "https://top.baidu.com/api/board?platform=wise&tab=realtime",
        "name": "百度热搜",
        "category": "综合",
        "type": "baidu",
    },
    "toutiao_hot": {
        "url": "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
        "name": "今日头条",
        "category": "综合",
        "type": "toutiao",
    },
    "bilibili_hot": {
        "url": "https://api.bilibili.com/x/web-interface/popular?ps=20",
        "name": "B站热门",
        "category": "娱乐",
        "type": "bilibili",
    },
}


# 搜索引擎源配置（Bing RSS — 唯一可用的静态HTML搜索源）
_SEARCH_FEEDS: dict[str, dict] = {
    "bing_cn_news": {
        "name": "Bing新闻搜索",
        "category": "综合",
        "type": "bing",
    },
}


def _split_chinese_keywords(keyword: str) -> list[str]:
    """将中文关键词拆分为2字以上的词组，用于模糊匹配。
    例如: "人工智能技术" -> ["人工智能", "智能技术", "人工", "智能", "技术"]
    """
    kw = keyword.strip()
    if not kw:
        return []
    # 英文直接返回
    if all(ord(c) < 128 for c in kw):
        return [kw.lower()]
    
    parts = []
    # 完整关键词
    parts.append(kw)
    # 2字词组滑窗
    for i in range(len(kw) - 1):
        for length in [2, 3, 4]:
            if i + length <= len(kw):
                chunk = kw[i:i+length]
                if len(chunk) >= 2 and chunk not in parts:
                    parts.append(chunk)
    return parts


def _keyword_relevance(keyword: str, title: str, snippet: str = "") -> float:
    """计算关键词与标题/摘要的匹配度分数（0-100）。
    
    评分规则:
    - 标题完整包含关键词: 100
    - 标题包含2字以上词组: 60-80
    - 摘要完整包含关键词: 40
    - 摘要包含2字以上词组: 20-30
    - 无匹配: 0
    """
    if not keyword or not title:
        return 0.0
    
    kw = keyword.strip().lower()
    title_lower = title.lower()
    snippet_lower = (snippet or "").lower()
    
    # 标题完整包含关键词 → 最高分
    if kw in title_lower:
        return 100.0
    
    # 拆分关键词为子词组
    sub_kws = _split_chinese_keywords(kw)
    
    # 标题包含子词组
    title_score = 0.0
    for sub in sub_kws:
        if sub in title_lower:
            # 词组越长，分数越高
            weight = min(len(sub) / len(kw), 1.0)
            title_score = max(title_score, 60.0 + weight * 20.0)
    
    # 摘要匹配
    snippet_score = 0.0
    if kw in snippet_lower:
        snippet_score = 40.0
    else:
        for sub in sub_kws:
            if sub in snippet_lower:
                weight = min(len(sub) / len(kw), 1.0)
                snippet_score = max(snippet_score, 20.0 + weight * 10.0)
    
    return max(title_score, snippet_score)


def _filter_and_sort_by_relevance(items: list[dict], keyword: str, min_score: float = 15.0) -> list[dict]:
    """过滤并按关键词匹配度排序结果。
    
    Args:
        items: 原始结果列表
        keyword: 搜索关键词
        min_score: 最低匹配分数阈值（低于此分数的结果被过滤）
    
    Returns:
        按匹配度降序排列的结果列表
    """
    if not keyword:
        return items
    
    # 计算每条结果的匹配度
    scored = []
    for item in items:
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        score = _keyword_relevance(keyword, title, snippet)
        if score >= min_score:
            scored.append((score, item))
    
    # 按匹配度降序排列
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]


def _fetch_rss_feed(source: str, keyword: str = "", max_results: int = 10) -> list[dict]:
    """从 RSS 源获取新闻线索"""
    config = _RSS_FEEDS.get(source)
    if not config:
        return []

    try:
        # RSS 源超时缩短，避免个别慢源阻塞并发池（如 36kr 有反爬）
        rss_timeout = min(settings.CRAWLER_TIMEOUT, 8)
        # 添加随机延迟避免被封
        import random
        time.sleep(random.uniform(0.3, 1.0))
        resp = requests.get(
            config["url"],
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=rss_timeout,
        )
        resp.raise_for_status()

        # RSS 可能有格式问题（如 36kr 返回的不是标准 RSS 2.0），尝试多种解析方式
        results: list[dict] = []
        seen: set[str] = set()

        # 方式一：标准 RSS XML 解析
        items = []
        try:
            root = ET.fromstring(resp.content)
            items = root.findall('.//item')
        except ET.ParseError:
            # 方式二：用 BeautifulSoup 从 HTML 中找链接
            soup = BeautifulSoup(resp.content, 'html.parser')
            for a in soup.select('a[href]'):
                text = a.get_text(' ', strip=True)
                href = (a.get('href') or '').strip()
                if not text or len(text) < 5:
                    continue
                if not href.startswith('http'):
                    continue
                if text in seen:
                    continue
                seen.add(text)
                results.append({
                    "title": text,
                    "url": href,
                    "snippet": "",
                    "source": config["name"],
                    "category": config["category"],
                    "pub_date": "",
                })
                if len(results) >= max_results:
                    break
            return results

        for item in items:
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            pub_date_el = item.find('pubDate')

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
            pub_date = pub_date_el.text.strip() if pub_date_el is not None and pub_date_el.text else ""

            # 清理 HTML 标签
            if desc:
                desc = re.sub(r'<[^>]+>', '', desc).strip()
                desc = desc[:300]

            if not title or len(title) < 5:
                continue

            # 关键词过滤（匹配标题或描述）
            if keyword:
                keyword_lower = keyword.lower()
                if keyword_lower not in title.lower() and keyword_lower not in desc.lower():
                    continue

            if title in seen:
                continue
            seen.add(title)

            results.append({
                "title": title,
                "url": link,
                "snippet": desc,
                "source": config["name"],
                "category": config["category"],
                "pub_date": pub_date,
            })

            if len(results) >= max_results:
                break

        # 回退：关键词过滤无结果时，返回最新内容（不限关键词）
        if not results and keyword:
            for item in items:
                title_el = item.find('title')
                link_el = item.find('link')
                desc_el = item.find('description')

                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

                if desc:
                    desc = re.sub(r'<[^>]+>', '', desc).strip()[:300]

                if not title or len(title) < 5 or title in seen:
                    continue

                seen.add(title)
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": desc,
                    "source": config["name"],
                    "category": config["category"],
                    "pub_date": "",
                })
                if len(results) >= max_results:
                    break

        return results
    except Exception as e:
        print(f"RSS fetch error for {source}: {e}")
        return []

def _fetch_api_feed(source: str, keyword: str = "", max_results: int = 10) -> list[dict]:
    """从 API/JSON 源获取新闻线索"""
    config = _API_FEEDS.get(source)
    if not config:
        return []

    results: list[dict] = []
    try:
        api_timeout = min(settings.CRAWLER_TIMEOUT, 10)
        headers = {"User-Agent": settings.CRAWLER_USER_AGENT}
        # 添加随机延迟避免被封
        import random
        time.sleep(random.uniform(0.3, 1.0))
        # 部分 API 需要 Referer 头（使用主站域名而非 API 子域名）
        referer_map = {
            "toutiao": "https://www.toutiao.com/",
            "bilibili": "https://www.bilibili.com/",
            "baidu": "https://www.baidu.com/",
        }
        if config["type"] in referer_map:
            headers["Referer"] = referer_map[config["type"]]
            headers["Accept"] = "application/json, text/plain, */*"
        resp = requests.get(
            config["url"],
            headers=headers,
            timeout=api_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        seen: set[str] = set()

        if config["type"] == "json":
            # 知乎日报: 不按关键词过滤，返回当日全部故事
            stories = data.get("stories", [])
            for story in stories:
                title = story.get("title", "")
                url = story.get("url", "")
                if not title or title in seen:
                    continue
                seen.add(title)
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": story.get("hint", ""),
                    "source": config["name"],
                    "category": config["category"],
                    "pub_date": data.get("date", ""),
                })
                if len(results) >= max_results:
                    break

        elif config["type"] == "baidu":
            # 百度热搜: 不按关键词过滤，返回当前热榜
            cards = data.get("data", {}).get("cards", [])
            for card in cards:
                for content_block in card.get("content", []):
                    if isinstance(content_block, dict):
                        items = content_block.get("content", [])
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            word = item.get("word", "")
                            if not word or word in seen:
                                continue
                            seen.add(word)
                            results.append({
                                "title": word,
                                "url": item.get("url", ""),
                                "snippet": f"百度热搜 #{item.get('index', '')}",
                                "source": config["name"],
                                "category": config["category"],
                                "pub_date": "",
                            })
                            if len(results) >= max_results:
                                break
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break

        elif config["type"] == "toutiao":
            # 今日头条热搜: 不按关键词过滤，返回当前热榜
            items = data.get("data", [])
            for item in items:
                title = item.get("Title", "")
                if not title or title in seen:
                    continue
                seen.add(title)
                results.append({
                    "title": title,
                    "url": item.get("Url", ""),
                    "snippet": f"热度: {item.get('HotValue', 0)}, 标签: {item.get('Label', '')}",
                    "source": config["name"],
                    "category": config["category"],
                    "pub_date": "",
                })
                if len(results) >= max_results:
                    break

        elif config["type"] == "bilibili":
            # B站热门: 热搜榜不按关键词过滤，返回当前热榜
            videos = data.get("data", {}).get("list", [])
            for v in videos:
                title = v.get("title", "")
                if not title or title in seen:
                    continue
                seen.add(title)
                bvid = v.get("bvid", "")
                stat = v.get("stat", {})
                results.append({
                    "title": title,
                    "url": f"https://www.bilibili.com/video/{bvid}" if bvid else v.get("short_link_v2", ""),
                    "snippet": f"播放: {stat.get('view', 0)}, 弹幕: {stat.get('danmaku', 0)}, 描述: {(v.get('desc', '') or '')[:60]}",
                    "source": config["name"],
                    "category": config["category"],
                    "pub_date": str(v.get("pubdate", "")),
                })
                if len(results) >= max_results:
                    break

        return results
    except Exception as e:
        print(f"API fetch error for {source}: {e}")
        return []


def _fetch_all_rss(keyword: str = "", max_results: int = 20) -> list[dict]:
    """从所有 RSS 源并发获取新闻"""
    all_results: list[dict] = []
    seen: set[str] = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_RSS_FEEDS)) as executor:
        future_map = {executor.submit(_fetch_rss_feed, source, keyword, max_results): source for source in _RSS_FEEDS}
        timeout = settings.CRAWLER_TIMEOUT + 10
        for future in concurrent.futures.as_completed(future_map, timeout=timeout):
            try:
                results = future.result(timeout=5)
                for item in results:
                    title = item.get("title", "")
                    if title not in seen:
                        seen.add(title)
                        all_results.append(item)
            except concurrent.futures.TimeoutError:
                pass
            except Exception:
                pass

    return all_results


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


def _to_beijing(dt):
    """将 UTC datetime 转为东八区（北京时间）ISO 字符串"""
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    bj = dt.astimezone(timezone(timedelta(hours=8)))
    return bj.isoformat()


def _serialize_clue(clue: Clue) -> dict:
    status_map = {
        "new": "pending",
        "processing": "pending",
        "verified": "processed",
        "pending": "pending",
        "processed": "processed",
        "archived": "archived",
    }
    try:
        keywords = json.loads(clue.keywords) if clue.keywords else []
    except Exception:
        keywords = [k.strip() for k in (clue.keywords or "").split(",") if k.strip()]
    return {
        "id": clue.id,
        "title": clue.title,
        "content": clue.content,
        "source": clue.source or "",
        "source_url": clue.source_url or "",
        "keywords": keywords,
        "news_value_score": clue.news_value_score or 0,
        "propagation_potential": clue.propagation_potential or 0,
        "status": status_map.get(clue.status or "", clue.status or "pending"),
        "created_at": _to_beijing(clue.created_at) if clue.created_at else "",
        "processed_at": _to_beijing(clue.processed_at) if clue.processed_at else None,
        "category": clue.category or "",
    }


def _score_clue(title: str, snippet: str) -> tuple[float, float]:
    base = min(90.0, max(35.0, len(title.strip()) * 1.8))
    if snippet:
        base += min(10.0, len(snippet) / 80.0)
    return round(min(base, 100.0), 1), round(min(base - 5.0, 100.0), 1)


def _search_suffix(source: str) -> str:
    mapping = {
        "news": "",
        "all": "",
        "36kr": "36氪",
        "ithome": "IT之家",
        "sspai": "少数派",
        "oschina": "开源中国",
        "solidot": "奇客",
        "zhihu_daily": "知乎日报",
        "baidu_hot": "百度热搜",
        "toutiao_hot": "今日头条",
        "bilibili_hot": "B站热门",
    }
    return mapping.get(source, "")


def _normalize_result_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"https://duckduckgo.com{url}"
    return url


def _looks_like_error_page(title: str, snippet: str) -> bool:
    blob = f"{title} {snippet}".lower()
    bad_markers = [
        "404",
        "not found",
        "access denied",
        "forbidden",
        "error",
        "captcha",
        "机器人",
        "验证",
        "页面不存在",
        "找不到页面",
    ]
    return any(marker in blob for marker in bad_markers)


def _probe_url(url: str, quick: bool = True) -> tuple[bool, str, str, str]:
    """验证候选来源是否真能打开，避免把错误页当成线索。"quick=True" 时只快速检查状态码，不解析页面内容。"""
    if not url:
        return False, "", "", ""
    try:
        # 快速模式：只检查 HEAD，不超过 3 秒
        timeout = 3 if quick else settings.CRAWLER_TIMEOUT
        method = requests.head if quick else requests.get
        resp = method(
            url,
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code >= 400:
            return False, "", "", ""
        # 快速模式只检查可达性
        if quick:
            return True, "", "", resp.url
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return True, "", "", resp.url
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text = soup.get_text(" ", strip=True)[:500]
        if _looks_like_error_page(title, text):
            return False, title, text, resp.url
        if len(text) < 80 and "loading" in text.lower():
            return False, title, text, resp.url
        return True, title, text, resp.url
    except Exception:
        return False, "", "", ""


def _fetch_bing_search(keyword: str, max_results: int = 10) -> list[dict]:
    """通过 Bing 搜索 RSS 接口采集新闻线索（唯一可用的中文搜索引擎接口）。

    Bing 的 ?format=rss 参数返回真正的 RSS XML（非 JS 渲染），
    在搜狗/360/百度等主流中文搜索引擎均 JS 渲染的情况下，这是唯一的可用方案。
    """
    query = keyword.strip()
    if not query:
        return []
    try:
        import random
        time.sleep(random.uniform(0.5, 1.5))

        # Bing search RSS endpoint: 稳定返回 XML 格式结果
        resp = requests.get(
            "https://www.bing.com/search",
            params={
                "q": f"{query} 新闻",
                "format": "rss",
                "mkt": "zh-CN",
                "setlang": "zh-cn",
                "count": max_results + 10,  # 多取一些供过滤
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=8,
            allow_redirects=True,
        )
        resp.raise_for_status()

        # 解析 RSS XML
        soup = BeautifulSoup(resp.text, "xml")
        results: list[dict] = []
        seen: set[str] = set()

        for item in soup.find_all("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")

            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el.get_text(strip=True) if link_el else ""
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # 清理 HTML 标签
            desc = re.sub(r"<[^>]+>", " ", desc).strip()[:300]

            # 跳过非新闻类结果和聚合网站
            if not title or len(title) < 6 or len(title) > 200:
                continue
            if not link.startswith("http"):
                continue

            skip_domains = ["bing.com", "microsoft.com", "go.microsoft"]
            if any(d in link for d in skip_domains):
                continue

            # 跳过导航/百科/广告类
            skip_patterns = ["百度百科", "维基百科", "增值电信", "ICP备", "Cookie", "登录", "注册"]
            if any(p in title for p in skip_patterns):
                continue

            if title in seen:
                continue
            seen.add(title)

            results.append({
                "title": title,
                "url": link,
                "snippet": desc,
                "source": "Bing搜索",
                "category": "综合",
            })

            if len(results) >= max_results:
                break

        return results
    except Exception as e:
        print(f"Bing RSS search error: {e}")
        return []


def _fetch_web_results(keyword: str, source: str = "all", max_results: int = 10, exact_match: bool = False) -> list[dict]:
    query = keyword.strip()

    # RSS 源映射
    rss_source_map = {k: k for k in _RSS_FEEDS}

    # API 源映射
    api_source_map = {k: k for k in _API_FEEDS}

    # 如果指定了特定 RSS 源（不应用相关性过滤，因为已有两阶段回退机制）
    if source in rss_source_map:
        return _fetch_rss_feed(rss_source_map[source], query, max_results)

    # 如果指定了特定 API 源
    if source in api_source_map:
        return _fetch_api_feed(api_source_map[source], query, max_results)

    # 如果指定了特定搜索源
    if source in _SEARCH_FEEDS:
        if source == "bing_cn_news":
            return _filter_and_sort_by_relevance(_fetch_bing_search(query, max_results), query)
        return []

    # "all" 模式：聚合所有源，按搜索链顺序调用
    all_items: list[dict] = []
    seen_titles: set[str] = set()

    # 1. RSS 源（带关键词过滤）
    for rss_key in _RSS_FEEDS:
        try:
            rss_results = _fetch_rss_feed(rss_key, query, max_results)
            for item in rss_results:
                t = item.get("title", "")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    all_items.append(item)
        except Exception:
            pass

    # 2. API 源（热搜榜等，不按关键词过滤）
    for api_key in _API_FEEDS:
        try:
            api_results = _fetch_api_feed(api_key, query, max_results)
            for item in api_results:
                t = item.get("title", "")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    all_items.append(item)
        except Exception:
            pass

    # 3. 搜索引擎源（Bing RSS — 关键词精确搜索）
    if query:
        try:
            bing_results = _fetch_bing_search(query, max_results)
            for item in bing_results:
                t = item.get("title", "")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    all_items.append(item)
        except Exception:
            pass

    # 4. 关键词过滤 + 按匹配度排序
    if query:
        filtered = _filter_and_sort_by_relevance(all_items, query, min_score=15.0)
        if filtered:
            return filtered[:max_results]

    # 5. 回退：交叉排列各源结果
    from collections import defaultdict
    by_source: dict[str, list[dict]] = defaultdict(list)
    for item in all_items:
        by_source[item.get("source", "")].append(item)
    interleaved: list[dict] = []
    source_iters = {k: iter(v) for k, v in by_source.items()}
    while len(interleaved) < max_results and source_iters:
        exhausted = []
        for key, it in source_iters.items():
            try:
                interleaved.append(next(it))
                if len(interleaved) >= max_results:
                    break
            except StopIteration:
                exhausted.append(key)
        for key in exhausted:
            del source_iters[key]
    return interleaved


def _ensure_source_name(source: str) -> str:
    mapping = {
        "36kr": "36氪",
        "ithome": "IT之家",
        "sspai": "少数派",
        "oschina": "开源中国",
        "solidot": "奇客Solidot",
        "zhihu_daily": "知乎日报",
        "baidu_hot": "百度热搜",
        "toutiao_hot": "今日头条",
        "bilibili_hot": "B站热门",
    }
    return mapping.get(source, source or "全网资讯")


def _frontend_origin() -> str:
    origins = settings.get_cors_origins()
    preferred = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"]
    for target in preferred:
        if target in origins:
            return target
    return origins[0] if origins else "http://localhost:5173"


def _build_query_url(term: str) -> str:
    query = (term or "").strip()
    if not query:
        return ""
    return f"https://duckduckgo.com/?q={quote_plus(query)}"


def _local_search_results(db: Session, keyword: str, max_results: int = 10) -> list[dict]:
    kw = (keyword or "").strip()
    if not kw:
        return []
    like = f"%{kw}%"
    short_kw = kw[:4] if len(kw) > 4 else kw
    results: list[dict] = []
    seen = set()

    def _query_clues(pattern: str) -> list[Clue]:
        return (
            db.query(Clue)
            .filter((Clue.title.ilike(pattern)) | (Clue.content.ilike(pattern)))
            .order_by(desc(Clue.created_at))
            .limit(max_results * 2)
            .all()
        )

    clues = _query_clues(like)
    if not clues and short_kw != kw:
        clues = _query_clues(f"%{short_kw}%")

    for row in clues:
        url = (row.source_url or "").strip() or _build_query_url(row.title or kw)
        title = (row.title or "").strip()
        if not title:
            continue
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        snippet = (row.content or "").strip()[:220]
        results.append(
            {
                "title": title,
                "url": _normalize_result_url(url),
                "snippet": snippet,
                "source": row.source or "本地线索",
            }
        )
        if len(results) >= max_results:
            return results

    origin = _frontend_origin().rstrip("/")
    def _query_articles(pattern: str) -> list[Article]:
        return (
            db.query(Article)
            .filter((Article.title.ilike(pattern)) | (Article.content.ilike(pattern)))
            .order_by(desc(Article.updated_at))
            .limit(max_results * 2)
            .all()
        )

    articles = _query_articles(like)
    if not articles and short_kw != kw:
        articles = _query_articles(f"%{short_kw}%")
    for article in articles:
        title = (article.title or "").strip()
        if not title:
            continue
        url = f"{origin}/reader/article/{article.id}"
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        content = (article.summary or article.content or "").strip()
        results.append(
            {
                "title": title,
                "url": url,
                "snippet": content[:220],
                "source": "本地稿件",
            }
        )
        if len(results) >= max_results:
            break
    return results


@router.get("")
async def list_clues(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    search_fields: Optional[str] = None,  # title,content,keywords,source,category (逗号分隔)
    search_mode: Optional[str] = "fuzzy",  # fuzzy(模糊), exact(精确), smart(智能)
    db: Session = Depends(get_db),
):
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
                    from sqlalchemy import case, literal_column
                    score_cases = []
                    for kw in keywords:
                        like_kw = f"%{kw}%"
                        if not fields or "title" in fields:
                            score_cases.append((Clue.title.ilike(like_kw), 10))
                            score_cases.append((Clue.title == kw, 50))
                        if not fields or "content" in fields:
                            score_cases.append((Clue.content.ilike(like_kw), 5))
                            score_cases.append((Clue.content == kw, 25))
                        if not fields or "keywords" in fields:
                            score_cases.append((Clue.keywords.ilike(like_kw), 8))
                        if not fields or "source" in fields:
                            score_cases.append((Clue.source.ilike(like_kw), 3))
                        if not fields or "category" in fields:
                            score_cases.append((Clue.category.ilike(like_kw), 2))

                    if score_cases:
                        try:
                            score_expr = case(*score_cases, else_=0).label("relevance_score")
                            conditions = [c[0] for c in score_cases]
                            q = q.filter(or_(*conditions))
                            q = q.order_by(desc(score_expr))
                        except Exception as search_error:
                            import logging
                            logging.getLogger(__name__).warning(f"智能搜索降级为模糊搜索: {str(search_error)[:100]}")
                            # 降级到模糊搜索
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
                import logging
                logging.getLogger(__name__).error(f"搜索功能异常，使用基础搜索: {str(e)[:200]}")
                # 最终降级：只做简单的标题和内容模糊搜索
                like = f"%{keywords[0]}%"
                q = q.filter(Clue.title.ilike(like) | Clue.content.ilike(like))

    total = q.count()
    items = q.order_by(desc(Clue.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 200, "data": [_serialize_clue(item) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get("/collect")
@router.post("/collect")
async def collect_clue(
    url: str = "",
    time_range: Optional[str] = None,
    max_results: int = 10,
    db: Session = Depends(get_db),
):
    cleaned_url = url.strip()
    if cleaned_url:
        ok, _, _, final_url = _probe_url(cleaned_url)
        if not ok:
            raise HTTPException(status_code=400, detail="来源页面无法访问或疑似错误页")
        cleaned_url = final_url or cleaned_url
    title = url.strip() or "定向采集线索"
    clue = Clue(
        title=title,
        content=f"采集来源：{cleaned_url}" if cleaned_url else "通过定向采集创建",
        source="direct",
        source_url=cleaned_url or None,
        status="pending",
        news_value_score=60,
        propagation_potential=55,
    )
    db.add(clue)
    db.commit()
    db.refresh(clue)
    return {"code": 200, "message": "采集任务已提交", "data": {"created": 1, "items": [_serialize_clue(clue)]}}


@router.get("/sources")
async def list_sources():
    """返回所有可用信源列表（RSS + API），供前端动态渲染信源选择器"""
    sources: list[dict] = []

    for key, config in _RSS_FEEDS.items():
        sources.append({
            "key": key,
            "name": config["name"],
            "type": "rss",
            "category": config["category"],
            "url": config["url"],
            "status": "active",
        })

    for key, config in _API_FEEDS.items():
        sources.append({
            "key": key,
            "name": config["name"],
            "type": "api",
            "category": config["category"],
            "url": config["url"],
            "status": "active",
        })

    for key, config in _SEARCH_FEEDS.items():
        sources.append({
            "key": key,
            "name": config["name"],
            "type": "search",
            "category": config["category"],
            "url": "",
            "status": "active",
        })

    return {
        "code": 200,
        "data": {
            "rss": [s for s in sources if s["type"] == "rss"],
            "api": [s for s in sources if s["type"] == "api"],
            "search": [s for s in sources if s["type"] == "search"],
            "all": sources,
        },
    }


@router.post("/sources/verify")
async def verify_source(body: dict):
    """验证单个信源是否可访问。请求体: {"url": "...", "type": "rss|api", "key": "..."}"""
    url = (body.get("url") or "").strip()
    source_type = body.get("type", "rss")

    if not url:
        raise HTTPException(status_code=400, detail="url 不能为空")

    try:
        start = time.time()
        resp = requests.get(
            url,
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=8,
            allow_redirects=True,
        )
        elapsed = round((time.time() - start) * 1000)

        if resp.status_code >= 400:
            return {
                "code": 200,
                "data": {
                    "accessible": False,
                    "status_code": resp.status_code,
                    "elapsed_ms": elapsed,
                    "reason": f"HTTP {resp.status_code}",
                    "url": url,
                },
            }

        # 验证内容格式
        content_type = resp.headers.get("content-type", "")
        is_valid = False

        if source_type == "rss":
            is_valid = "xml" in content_type or "rss" in content_type or (
                resp.text.strip().startswith("<") and ("<rss" in resp.text or "<feed" in resp.text)
            )
        elif source_type == "api":
            try:
                resp.json()
                is_valid = True
            except Exception:
                is_valid = False
        else:
            is_valid = True

        return {
            "code": 200,
            "data": {
                "accessible": True,
                "status_code": resp.status_code,
                "elapsed_ms": elapsed,
                "content_type": content_type,
                "format_valid": is_valid,
                "item_count": _count_rss_items(resp.text) if source_type == "rss" else None,
                "url": url,
            },
        }
    except requests.ConnectionError:
        return {"code": 200, "data": {"accessible": False, "reason": "连接失败，源不可达", "url": url}}
    except requests.Timeout:
        return {"code": 200, "data": {"accessible": False, "reason": "请求超时", "url": url}}
    except Exception as e:
        return {"code": 200, "data": {"accessible": False, "reason": str(e), "url": url}}


def _count_rss_items(xml_text: str) -> int:
    """简单统计 RSS/Atom feed 中的条目数"""
    import re
    items = len(re.findall(r"<item[>\s]", xml_text))
    if items == 0:
        items = len(re.findall(r"<entry[>\s]", xml_text))
    return items


@router.get("/collect/multichannel")
@router.post("/collect/multichannel")
async def collect_multichannel(
    keywords: str = "",
    channels: str = "",
    max_results: int = 10,
    db: Session = Depends(get_db),
):
    import logging
    logger = logging.getLogger(__name__)

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    channel_list = [c.strip() for c in channels.split(",") if c.strip()]
    if not keyword_list:
        raise HTTPException(status_code=400, detail="关键词不能为空")

    logger.info(f"🔍 开始多渠道采集 | 关键词: {keyword_list} | 渠道: {channel_list or ['all']} | 上限: {max_results}")

    items: list[dict] = []
    seen_keys: set[str] = set()
    fetch_errors: list[str] = []
    successful_sources: list[str] = []

    # 顺序抓取各渠道（避免并发过高被封）
    import random
    tasks = [(k, c) for k in keyword_list for c in (channel_list or ["all"])]
    try:
        for idx, (kw, src) in enumerate(tasks):
            # 请求间隔 1-3 秒，避免被封
            if idx > 0:
                time.sleep(random.uniform(1.0, 3.0))
            try:
                results = _fetch_web_results(kw, src, max_results)
                if results:
                    for item in results:
                        key = (item.get("title"), item.get("url"))
                        if key not in seen_keys:
                            seen_keys.add(key)
                            items.append(item)
                    successful_sources.append(f"{src}({len(results)}条)")
                    logger.info(f"✅ {src} 成功采集 {len(results)} 条 (关键词: {kw})")
                else:
                    fetch_errors.append(f"{src}: 无结果")
                    logger.warning(f"⚠️ {src} 未找到相关内容 (关键词: {kw})")
            except Exception as e:
                error_msg = str(e)[:100]
                fetch_errors.append(f"{src}: {error_msg}")
                logger.error(f"❌ {src} 采集失败: {error_msg} (关键词: {kw})")
    except Exception as pool_error:
        logger.error(f"❌ 采集执行异常: {str(pool_error)[:200]}")
        fetch_errors.append(f"采集错误: {str(pool_error)[:50]}")

    created = []
    seen = set()
    try:
        for item in items[:max_results]:
            key = (item.get("title"), item.get("url"))
            if key in seen:
                continue
            seen.add(key)
            title = str(item.get("title") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            source = _ensure_source_name(str(item.get("source") or "all"))
            category = str(item.get("category") or "")
            source_url = str(item.get("url") or "").strip() or None
            
            # 数据库级别去重：检查是否已存在相同标题+来源的线索
            existing = db.query(Clue).filter(
                Clue.title == title,
                Clue.source == source
            ).first()
            if existing:
                continue
            
            news_score, prop_score = _score_clue(title, snippet)
            clue = Clue(
                title=title,
                content=snippet or title,
                source=source,
                source_url=source_url,
                keywords=json.dumps(keyword_list, ensure_ascii=False),
                status="pending",
                news_value_score=news_score,
                propagation_potential=prop_score,
                processed_at=datetime.now(timezone(timedelta(hours=8))),
            )
            if category:
                clue.category = category
            db.add(clue)
            created.append(clue)

        db.commit()
        for clue in created:
            db.refresh(clue)
    except Exception as db_error:
        logger.error(f"❌ 数据库操作失败: {str(db_error)[:200]}")
        db.rollback()
        created = []  # 清空已创建的列表，避免返回不一致的数据

    # 构建详细的响应信息
    total_fetched = len(items)
    total_created = len(created)

    if total_created > 0:
        message = f"✅ 成功采集 {total_created} 条线索"
        if successful_sources:
            message += f"（来源: {'、'.join(successful_sources[:3])}）"
        logger.info(f"🎉 采集完成！共获取 {total_fetched} 条，创建 {total_created} 条线索")
        status_code = 200
    elif total_fetched > 0:
        message = "⚠️ 采集到内容但均为重复线索"
        status_code = 200
        logger.warning(f"⚠️ 采集到 {total_fetched} 条但全部重复")
    else:
        error_details = []
        if fetch_errors:
            error_details.append(f"失败原因: {'; '.join(fetch_errors[:3])}")
        error_details.append("建议: 尝试其他渠道（如 IT之家、36氪）或更换关键词")

        message = f"❌ 未采集到有效线索。{' '.join(error_details)}"
        status_code = 202  # 使用 202 表示接受但无内容（非真正错误）
        logger.warning(f"😢 采集失败！未获取到任何有效内容")

    return {
        "code": status_code,
        "message": message,
        "data": {
            "created": total_created,
            "fetched": total_fetched,
            "items": [_serialize_clue(item) for item in created],
            "sources": successful_sources,
            "errors": fetch_errors[:5],  # 返回前5个错误供前端展示
            "keywords": keyword_list,
            "channels": channel_list,
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
        title=body.title,
        content=body.content,
        source=body.source,
        source_url=body.source_url,
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
    return {
        "code": 200,
        "message": "分析完成",
        "data": {
            "clue_id": clue_id,
            "analysis": f"AI分析完成，新闻价值 {score}，传播潜力 {prop}",
            "news_value_score": score,
            "propagation_potential": prop,
        },
    }


@router.post("/{clue_id}/search-info")
async def search_info(
    clue_id: int,
    body: dict,
    db: Session = Depends(get_db),
):
    clue = db.query(Clue).filter(Clue.id == clue_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="线索不存在")
    keyword = str(body.get("keyword") or clue.title or "").strip()
    source = str(body.get("source") or "all")
    max_results = int(body.get("max_results") or 10)
    exact_match = bool(body.get("exact_match") or False)
    results = _fetch_web_results(keyword, source=source, max_results=max_results, exact_match=exact_match)
    if not results:
        results = _local_search_results(db, keyword, max_results=max_results)
    if not results and clue.source_url:
        results = [
            {
                "title": clue.title,
                "url": _normalize_result_url(clue.source_url),
                "snippet": clue.content[:200] if clue.content else "",
                "source": clue.source or "all",
            }
        ]
    return {"code": 200, "data": {"keyword": keyword, "total": len(results), "results": results}}
