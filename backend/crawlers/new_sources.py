"""GitHub Trending + Dev.to 크롤러"""
import requests
from bs4 import BeautifulSoup
import re
from backend.db import get_db

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KLD-Bot/1.0)",
    "Accept": "text/html,application/json",
}

GH_KEYWORDS = [
    "saas", "boilerplate", "starter", "template", "dashboard",
    "api", "tool", "generator", "automation", "bot", "scraper",
    "monitoring", "analytics", "landing", "payment", "subscription",
    "open source", "self-hosted", "nocode", "lowcode", "ai"
]


def crawl_github_trending() -> tuple[int, int]:
    """GitHub Trending에서 SaaS/도구성 프로젝트 수집"""
    db = get_db()
    found = 0
    new_items = 0

    for lang in ["", "python", "javascript", "typescript", "go"]:
        try:
            url = f"https://github.com/trending/{lang}?since=weekly" if lang else "https://github.com/trending?since=weekly"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            for article in soup.find_all("article", class_="Box-row"):
                h2 = article.find("h2")
                if not h2:
                    continue
                link = h2.find("a")
                if not link:
                    continue

                # 저장소 이름
                full_name = link.get("href", "").strip("/")
                name = link.text.strip().replace("\n", " ").replace("  ", " ")
                repo_url = f"https://github.com/{full_name}"

                # 설명
                desc_el = article.find("p", class_="col-9")
                description = desc_el.text.strip() if desc_el else ""

                # 언어
                lang_el = article.find("span", itemprop="programmingLanguage")
                language = lang_el.text.strip() if lang_el else ""

                # 전체 텍스트에서 키워드 매칭
                text = (name + " " + description).lower()
                if not any(kw in text for kw in GH_KEYWORDS):
                    continue

                found += 1
                try:
                    db.execute("""
                        INSERT OR IGNORE INTO discovered_services
                        (name, url, description, source, source_url, category)
                        VALUES (?, ?, ?, 'github', ?, ?)
                    """, (name[:200], repo_url, description[:1000],
                          url, language or 'unknown'))
                    if db.total_changes > 0:
                        new_items += 1
                except Exception:
                    pass

        except Exception as e:
            print(f"  GitHub trending ({lang or 'all'}) error: {e}")

    db.commit()
    db.execute(
        "INSERT INTO crawl_log (source, items_found, new_items, status) "
        "VALUES ('github', ?, ?, 'success')", (found, new_items)
    )
    db.commit()
    db.close()
    return found, new_items


def crawl_devto() -> tuple[int, int]:
    """Dev.to API에서 #showdev, #saas 태그 글 수집"""
    db = get_db()
    found = 0
    new_items = 0

    tags = ["showdev", "saas", "webdev", "startup", "tutorial"]
    seen_urls = set()

    for tag in tags:
        try:
            resp = requests.get(
                f"https://dev.to/api/articles?tag={tag}&per_page=15",
                headers=HEADERS, timeout=15
            )
            articles = resp.json()

            for article in articles:
                title = article.get("title", "")
                url = article.get("url", "")
                description = article.get("description", "") or ""
                tag_list = article.get("tag_list", [])

                # 중복 제거
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # SaaS/도구 관련 글만
                text = (title + " " + description + " " + " ".join(tag_list)).lower()
                if not any(kw in text for kw in GH_KEYWORDS):
                    continue

                found += 1
                try:
                    db.execute("""
                        INSERT OR IGNORE INTO discovered_services
                        (name, url, description, source, source_url, category)
                        VALUES (?, ?, ?, 'devto', ?, ?)
                    """, (title[:200], url, description[:1000], url,
                          tag_list[0] if tag_list else 'unknown'))
                    if db.total_changes > 0:
                        new_items += 1
                except Exception:
                    pass

        except Exception as e:
            print(f"  Dev.to tag={tag} error: {e}")

    db.commit()
    db.execute(
        "INSERT INTO crawl_log (source, items_found, new_items, status) "
        "VALUES ('devto', ?, ?, 'success')", (found, new_items)
    )
    db.commit()
    db.close()
    return found, new_items


def crawl_all_new() -> tuple[int, int]:
    """새로운 소스들 전체 크롤링"""
    gh_f, gh_n = crawl_github_trending()
    dt_f, dt_n = crawl_devto()
    total_f = gh_f + dt_f
    total_n = gh_n + dt_n
    print(f"GitHub: {gh_f}f/{gh_n}n | Dev.to: {dt_f}f/{dt_n}n | Total: {total_f}f/{total_n}n")
    return total_f, total_n


if __name__ == "__main__":
    from backend.db import init_db
    init_db()
    crawl_all_new()
