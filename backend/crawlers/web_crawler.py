"""웹 크롤러 — Product Hunt (Atom 피드) + Hacker News (Firebase API)"""
import requests
from bs4 import BeautifulSoup
import re
from backend.db import get_db, init_db

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KLD-Bot/1.0; +https://kld.example.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "Accept-Language": "en-US,en;q=0.9",
}

HN_KEYWORDS = [
    "Show HN", "launch", "SaaS", "startup", "revenue", "MRR",
    "side project", "built", "launched", "profitable", "micro saas"
]


def crawl_producthunt() -> tuple[int, int]:
    """Product Hunt Atom 피드에서 제품 수집"""
    db = get_db()
    found = 0
    new_items = 0

    try:
        resp = requests.get("https://www.producthunt.com/feed", headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "xml")
        entries = soup.find_all("entry")

        for entry in entries[:30]:
            title_el = entry.find("title")
            link_el = entry.find("link")
            if not title_el or not link_el:
                continue

            name = title_el.text.strip()[:200]
            url = link_el.get("href", "")
            if not url:
                continue

            # 본문에서 설명 추출
            content_el = entry.find("content")
            desc = ""
            if content_el and content_el.text:
                # HTML 태그 제거
                desc = re.sub(r'<[^>]+>', ' ', content_el.text)
                desc = re.sub(r'\s+', ' ', desc).strip()[:1000]

            found += 1
            try:
                db.execute("""
                    INSERT OR IGNORE INTO discovered_services
                    (name, url, description, source, source_url, category)
                    VALUES (?, ?, ?, 'producthunt', ?, 'unknown')
                """, (name, url, desc, url))
                if db.total_changes > 0:
                    new_items += 1
            except Exception:
                pass

    except Exception as e:
        db.execute(
            "INSERT INTO crawl_log (source, items_found, new_items, status, error_msg) "
            "VALUES ('producthunt', 0, 0, 'error', ?)", (str(e)[:500],)
        )

    db.commit()
    db.execute(
        "INSERT INTO crawl_log (source, items_found, new_items, status) "
        "VALUES ('producthunt', ?, ?, 'success')", (found, new_items)
    )
    db.commit()
    db.close()
    return found, new_items


def crawl_hackernews() -> tuple[int, int]:
    """Hacker News API로 Show HN 등 인디 해커 글 수집"""
    db = get_db()
    found = 0
    new_items = 0

    try:
        # 최신 글 ID 목록
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/newstories.json",
            timeout=15
        )
        story_ids = resp.json()[:100]

        for sid in story_ids:
            try:
                story = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=10
                ).json()

                if not story:
                    continue
                title = story.get("title", "")
                if not title:
                    continue

                title_lower = title.lower()
                if not any(kw.lower() in title_lower for kw in HN_KEYWORDS):
                    continue

                url = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
                found += 1

                try:
                    db.execute("""
                        INSERT OR IGNORE INTO discovered_services
                        (name, url, description, source, source_url, category)
                        VALUES (?, ?, ?, 'hackernews', ?, 'unknown')
                    """, (
                        title[:200], url,
                        story.get("text", "")[:1000],
                        f"https://news.ycombinator.com/item?id={sid}"
                    ))
                    if db.total_changes > 0:
                        new_items += 1
                except Exception:
                    pass
            except Exception:
                continue

    except Exception as e:
        db.execute(
            "INSERT INTO crawl_log (source, items_found, new_items, status, error_msg) "
            "VALUES ('hackernews', 0, 0, 'error', ?)", (str(e)[:500],)
        )

    db.commit()
    db.execute(
        "INSERT INTO crawl_log (source, items_found, new_items, status) "
        "VALUES ('hackernews', ?, ?, 'success')", (found, new_items)
    )
    db.commit()
    db.close()
    return found, new_items


def crawl_all_web() -> tuple[int, int]:
    """모든 웹 소스 크롤링"""
    ph_f, ph_n = crawl_producthunt()
    hn_f, hn_n = crawl_hackernews()
    total_f = ph_f + hn_f
    total_n = ph_n + hn_n
    print(f"ProductHunt: {ph_f}f/{ph_n}n | HackerNews: {hn_f}f/{hn_n}n | Total: {total_f}f/{total_n}n")
    return total_f, total_n


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    init_db()
    crawl_all_web()
