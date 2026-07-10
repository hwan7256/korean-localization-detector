"""Reddit 크롤러 — r/SideProject, r/SaaS 등에서 SaaS 출시/성장 글 수집"""
import os
import praw
from datetime import datetime, timedelta, timezone
from backend.db import get_db, init_db

SUBREDDITS = ["SideProject", "SaaS", "indiehackers", "startups", "microsaas"]
KEYWORDS = [
    "launched", "revenue", "MRR", "ARR", "users", "growth",
    "making", "profitable", "hit", "reached", "built in",
    "first sale", "first customer", "monthly", "annual",
    "i made", "i built", "my saas", "my startup",
    "just hit", "just reached", "now making"
]


def connect_reddit():
    """PRAW Reddit 클라이언트 생성"""
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "KLD-bot/1.0")
    )


def extract_urls(text, post_url):
    """본문에서 외부 URL 추출 (자체 Reddit 링크 제외)"""
    urls = []
    if not text:
        return []
    import re
    url_pattern = re.compile(r'https?://[^\s\)\[\]]+')
    for match in url_pattern.findall(text):
        url = match.rstrip('.,;:!?')
        if url and 'reddit.com' not in url and 'redd.it' not in url:
            urls.append(url)
    return urls[:3]  # 최대 3개


def crawl_reddit(hours_back: int = 24) -> tuple[int, int]:
    """일정 시간 내 Reddit 게시글 수집"""
    try:
        reddit = connect_reddit()
    except Exception as e:
        db = get_db()
        db.execute(
            "INSERT INTO crawl_log (source, items_found, new_items, status, error_msg) "
            "VALUES ('reddit', 0, 0, 'error', ?)", (str(e)[:500],)
        )
        db.commit()
        db.close()
        return 0, 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    db = get_db()
    found = 0
    new_items = 0

    for subreddit_name in SUBREDDITS:
        try:
            sub = reddit.subreddit(subreddit_name)
            for post in sub.new(limit=50):
                post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                if post_time < cutoff:
                    break

                title_lower = post.title.lower()
                if not any(kw.lower() in title_lower for kw in KEYWORDS):
                    continue

                found += 1
                body = post.selftext if post.selftext else ""
                urls = extract_urls(body + " " + post.url, post.url)

                for url in (urls if urls else [post.url]):
                    try:
                        db.execute("""
                            INSERT OR IGNORE INTO discovered_services
                            (name, url, description, source, source_url)
                            VALUES (?, ?, ?, 'reddit', ?)
                        """, (post.title[:200], url, body[:1000],
                              f"https://reddit.com{post.permalink}"))
                        if db.total_changes > 0:
                            new_items += 1
                    except Exception:
                        pass
        except Exception as e:
            print(f"  Subreddit {subreddit_name} error: {e}")

    db.commit()

    db.execute(
        "INSERT INTO crawl_log (source, items_found, new_items, status) "
        "VALUES ('reddit', ?, ?, 'success')", (found, new_items)
    )
    db.commit()
    db.close()
    return found, new_items


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    init_db()
    f, n = crawl_reddit()
    print(f"Reddit: {f} posts found, {n} new services saved")
