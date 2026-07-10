"""웹 크롤러 — Product Hunt + IndieHackers 스크래핑"""
import requests
from bs4 import BeautifulSoup
from backend.db import get_db, init_db

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KLD-Bot/1.0; +https://kld.example.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def crawl_producthunt() -> tuple[int, int]:
    """Product Hunt 메인 피드에서 인기 제품 수집"""
    db = get_db()
    found = 0
    new_items = 0

    try:
        # PH는 JS 렌더링이 많아 RSS/feed 우선 사용
        resp = requests.get("https://www.producthunt.com/feed", headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "lxml")

        items = soup.select("a[href^='/posts/']")
        seen = set()

        for item in items[:30]:
            title_el = item.select_one("h3, [class*='title']")
            desc_el = item.select_one("[class*='tagline'], [class*='description']")
            if not title_el:
                continue

            name = title_el.get_text(strip=True)[:200]
            url = item.get("href", "")
            if url and not url.startswith("http"):
                url = f"https://www.producthunt.com{url}"

            if url in seen or not url:
                continue
            seen.add(url)
            found += 1

            try:
                db.execute("""
                    INSERT OR IGNORE INTO discovered_services
                    (name, url, description, source, source_url, category)
                    VALUES (?, ?, ?, 'producthunt', ?, 'unknown')
                """, (
                    name, url,
                    desc_el.get_text(strip=True)[:1000] if desc_el else "",
                    url
                ))
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


def crawl_indiehackers() -> tuple[int, int]:
    """IndieHackers 트렌딩 포스트 수집"""
    db = get_db()
    found = 0
    new_items = 0

    try:
        resp = requests.get(
            "https://www.indiehackers.com/posts?sort=trending",
            headers=HEADERS, timeout=20
        )
        soup = BeautifulSoup(resp.text, "lxml")

        items = soup.select("a[href^='/post/']")
        seen = set()

        for item in items[:30]:
            title = item.get_text(strip=True)[:200]
            url = item.get("href", "")
            if url and not url.startswith("http"):
                url = f"https://www.indiehackers.com{url}"

            if not title or url in seen or not url:
                continue
            seen.add(url)
            found += 1

            try:
                db.execute("""
                    INSERT OR IGNORE INTO discovered_services
                    (name, url, description, source, source_url, category)
                    VALUES (?, ?, ?, 'indiehackers', ?, 'unknown')
                """, (title, url, "", url))
                if db.total_changes > 0:
                    new_items += 1
            except Exception:
                pass

    except Exception as e:
        db.execute(
            "INSERT INTO crawl_log (source, items_found, new_items, status, error_msg) "
            "VALUES ('indiehackers', 0, 0, 'error', ?)", (str(e)[:500],)
        )

    db.commit()
    db.execute(
        "INSERT INTO crawl_log (source, items_found, new_items, status) "
        "VALUES ('indiehackers', ?, ?, 'success')", (found, new_items)
    )
    db.commit()
    db.close()
    return found, new_items


def crawl_all_web() -> tuple[int, int]:
    """모든 웹 소스 크롤링"""
    ph_f, ph_n = crawl_producthunt()
    ih_f, ih_n = crawl_indiehackers()
    total_f = ph_f + ih_f
    total_n = ph_n + ih_n
    print(f"ProductHunt: {ph_f}f/{ph_n}n | IndieHackers: {ih_f}f/{ih_n}n | Total: {total_f}f/{total_n}n")
    return total_f, total_n


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    init_db()
    crawl_all_web()
