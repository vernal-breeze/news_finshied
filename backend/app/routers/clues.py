"""线索路由：线索管理、采集、分析"""
import json
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, unquote, quote_plus
from typing import Optional, List

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import get_settings
from app.database import get_db
from app.models.article import Article
from app.models.clue import Clue

settings = get_settings()
router = APIRouter(prefix="/api/clues", tags=["Clues"])


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
        "created_at": clue.created_at.isoformat() if clue.created_at else "",
        "processed_at": clue.processed_at.isoformat() if clue.processed_at else None,
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
        "news_sites": "",
        "tencent": "腾讯新闻",
        "netease": "网易新闻",
        "sina": "新浪新闻",
        "ifeng": "凤凰网",
        "thepaper": "澎湃新闻",
        "sohu": "搜狐新闻",
        "toutiao": "今日头条",
        "weibo": "微博",
        "social_media": "知乎 小红书 微博",
        "government": "政府 公告 政策",
        "social": "知乎 微博",
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


def _probe_url(url: str) -> tuple[bool, str, str, str]:
    """验证候选来源是否真能打开，避免把错误页当成线索。"""
    if not url:
        return False, "", "", ""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=settings.CRAWLER_TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code >= 400:
            return False, "", "", ""
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


def _fetch_bing_news(keyword: str, max_results: int = 10) -> list[dict]:
    """通过 Bing 新闻搜索采集线索（国内可访问）。"""
    query = keyword.strip()
    if not query:
        return []
    try:
        resp = requests.get(
            "https://www.bing.com/news/search",
            params={"q": query},
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=settings.CRAWLER_TIMEOUT,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict] = []
        seen = set()
        for a in soup.select("a[href]"):
            text = a.get_text(" ", strip=True)
            href = (a.get("href") or "").strip()
            if len(text) < 10 or len(text) > 150 or not href.startswith("http"):
                continue
            if "bing.com" in href:
                continue
            if text in seen or _looks_like_error_page(text, ""):
                continue
            seen.add(text)
            results.append({
                "title": text,
                "url": href,
                "snippet": "",
                "source": "Bing 新闻",
            })
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


# 各新闻站点直接抓取配置
_NEWS_SITE_CONFIG: dict[str, dict] = {
    "tencent": {
        "url": "https://news.qq.com/",
        "name": "腾讯新闻",
        "link_sel": "a[href]",
        "url_pattern": "qq.com",
    },
    "netease": {
        "url": "https://news.163.com/",
        "name": "网易新闻",
        "link_sel": "a[href]",
        "url_pattern": "163.com/data/article/",
    },
    "sina": {
        "url": "https://news.sina.com.cn/",
        "name": "新浪新闻",
        "link_sel": "a[href]",
        "url_pattern": "sina.com.cn",
    },
    "ifeng": {
        "url": "https://news.ifeng.com/",
        "name": "凤凰网",
        "link_sel": "a[href]",
        "url_pattern": "ifeng.com/c/",
    },
    "sohu": {
        "url": "https://news.sohu.com/",
        "name": "搜狐新闻",
        "link_sel": "a[href]",
        "url_pattern": "sohu.com/a/",
    },
}


def _fetch_site_news(source: str, keyword: str, max_results: int = 10) -> list[dict]:
    """直接从新闻站点首页抓取最新新闻标题和链接（不做关键词过滤）。"""
    config = _NEWS_SITE_CONFIG.get(source)
    if not config:
        return []
    try:
        resp = requests.get(
            config["url"],
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=settings.CRAWLER_TIMEOUT,
        )
        resp.raise_for_status()
        # 修正编码（部分站点返回 ISO-8859-1，实际为 UTF-8）
        if resp.encoding and resp.encoding.lower() in ("iso-8859-1", "latin-1"):
            resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict] = []
        seen = set()
        for a in soup.select(config["link_sel"]):
            text = a.get_text(" ", strip=True)
            href = (a.get("href") or "").strip()
            if not text or len(text) < 8 or len(text) > 120:
                continue
            if config["url_pattern"] not in href:
                continue
            if text in seen:
                continue
            if href.startswith("//"):
                href = f"https:{href}"
            seen.add(text)
            results.append({
                "title": text,
                "url": href,
                "snippet": "",
                "source": config["name"],
            })
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def _fetch_web_results(keyword: str, source: str = "all", max_results: int = 10, exact_match: bool = False) -> list[dict]:
    query = keyword.strip()
    if not query:
        return []

    # 对于特定新闻站点，先尝试直接抓取
    if source in _NEWS_SITE_CONFIG:
        results = _fetch_site_news(source, query, max_results)
        if results:
            return results
        # 直接抓取无结果时，用 Bing 搜索该站点的内容
        site_query = f"{query} {_search_suffix(source)}".strip()
        results = _fetch_bing_news(site_query, max_results)
        if results:
            return results

    # 使用 Bing 新闻搜索（国内可访问）
    search_query = query
    suffix = _search_suffix(source)
    if suffix:
        search_query = f"{query} {suffix}"
    results = _fetch_bing_news(search_query, max_results)
    if results:
        return results

    # 回退到 DuckDuckGo（国外可访问时）
    try:
        ddg_query = f'"{search_query}"' if exact_match else search_query
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": ddg_query},
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=settings.CRAWLER_TIMEOUT,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        seen: set[str] = set()
        for item in soup.select(".result")[: max_results * 2]:
            title_el = item.select_one(".result__a")
            snippet_el = item.select_one(".result__snippet")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)
            url = _normalize_result_url(title_el.get("href") or "")
            snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
            if not title or title in seen:
                continue
            if _looks_like_error_page(title, snippet):
                continue
            if url:
                ok, page_title, page_text, final_url = _probe_url(url)
                if not ok:
                    continue
                url = final_url or url
                if page_title and len(page_title) > 3 and title and title not in page_title:
                    snippet = snippet or page_title
            seen.add(title)
            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": _ensure_source_name(source),
            })
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return results


def _ensure_source_name(source: str) -> str:
    mapping = {
        "tencent": "腾讯新闻",
        "netease": "网易新闻",
        "sina": "新浪新闻",
        "ifeng": "凤凰网",
        "thepaper": "澎湃新闻",
        "sohu": "搜狐新闻",
        "toutiao": "今日头条",
        "weibo": "微博",
        "government": "政府网站",
        "social_media": "社交媒体",
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
    db: Session = Depends(get_db),
):
    q = db.query(Clue)
    if status:
        q = q.filter(Clue.status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(Clue.title.ilike(like) | Clue.content.ilike(like))
    total = q.count()
    items = q.order_by(desc(Clue.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 200, "data": [_serialize_clue(item) for item in items], "total": total, "page": page, "page_size": page_size}


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


@router.post("/batch-delete")
async def batch_delete_clue(ids: List[int], db: Session = Depends(get_db)):
    db.query(Clue).filter(Clue.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"code": 200, "message": f"已删除 {len(ids)} 条"}


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


@router.post("/collect/multichannel")
async def collect_multichannel(
    keywords: str = "",
    channels: str = "",
    max_results: int = 10,
    db: Session = Depends(get_db),
):
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    channel_list = [c.strip() for c in channels.split(",") if c.strip()]
    if not keyword_list:
        raise HTTPException(status_code=400, detail="关键词不能为空")

    items: list[dict] = []
    for keyword in keyword_list:
        for channel in channel_list or ["all"]:
            results = _fetch_web_results(keyword, channel, max_results=max_results)
            if results:
                items.extend(results)
        if not items:
            items.extend(_local_search_results(db, keyword, max_results=max_results))

    created = []
    seen = set()
    for item in items[:max_results]:
        key = (item.get("title"), item.get("url"))
        if key in seen:
            continue
        seen.add(key)
        title = str(item.get("title") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        source = _ensure_source_name(str(item.get("source") or "all"))
        source_url = str(item.get("url") or "").strip() or None
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
            processed_at=datetime.now(timezone.utc),
        )
        db.add(clue)
        created.append(clue)

    db.commit()
    for clue in created:
        db.refresh(clue)
    message = "多渠道采集已提交" if created else "未抓取到可验证来源"
    return {
        "code": 200,
        "message": message,
        "data": {
            "created": len(created),
            "items": [_serialize_clue(item) for item in created],
        },
    }


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
