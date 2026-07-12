"""GitHub Search API 크롤러 - 공식 API 사용, 완전 합법"""
import requests, time, os
from backend.db import get_db

# .env에서 토큰 읽기 (환경변수 또는 파일)
def _get_token():
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        try:
            with open(os.path.expanduser("~/.hermes/.env")) as f:
                for line in f:
                    if "GITHUB_TOKEN" in line and not line.strip().startswith("#"):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except: pass
    return token

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "KLD-Bot/1.0 (Korean Localization Detector; contact@kld.lat)",
}
TOKEN = _get_token()
if TOKEN:
    HEADERS["Authorization"] = f"token {TOKEN}"

# 노이즈 키워드: SaaS 제품이 아닌 리소스/템플릿류 제외
NOISE_TERMS = [
    "awesome", "boilerplate", "starter", "template", "curated",
    "skeleton", "scaffold", "cookiecutter", "example", "demo-app",
    "awesome-list", "resources", "cheatsheet", "roadmap", "interview",
]

SEARCHES = [
    ("topic:saas", "github-search"),
    ("topic:self-hosted+topic:webapp", "github-search"),
    ("topic:developer-tools+topic:web", "github-search"),
]

MIN_STARS = 10  # 별 10개 이상으로 상향 (잡음 감소)


def _is_noise(name: str, description: str) -> bool:
    """레포가 진짜 SaaS/제품인지 판별"""
    combined = f"{name} {description}".lower()
    for term in NOISE_TERMS:
        if term in combined:
            return True
    # "list of", "curated list" 등 패턴
    if "list" in name.lower().split("/")[-1] and "of" in combined:
        return True
    return False


def crawl_github_search() -> tuple[int, int]:
    """GitHub Search API로 SaaS/도구성 레포 수집"""
    db = get_db()
    found = 0
    new_items = 0
    skipped = 0

    for query, source_label in SEARCHES:
        page = 1
        while page <= 5:  # 쿼리당 최대 5페이지 (500개)
            url = f"https://api.github.com/search/repositories?q={query}+stars:>={MIN_STARS}&sort=stars&per_page=100&page={page}"
            
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                
                if resp.status_code == 403:
                    # Rate limit 초과
                    reset_time = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait = max(reset_time - int(time.time()), 10)
                    print(f"  Rate limit hit, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                
                if resp.status_code != 200:
                    print(f"  GitHub API error: {resp.status_code} {resp.text[:100]}")
                    break

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break

                for repo in items:
                    found += 1
                    name = repo.get("full_name", "")
                    description = (repo.get("description") or "")[:1000]

                    # 진짜 SaaS 제품만 통과
                    if _is_noise(name, description):
                        skipped += 1
                        continue

                    url = repo.get("html_url", "")
                    stars = repo.get("stargazers_count", 0)
                    language = repo.get("language") or ""
                    topics = ",".join(repo.get("topics", [])[:5])

                    try:
                        db.execute("""
                            INSERT OR IGNORE INTO discovered_services
                            (name, url, description, source, source_url, category)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            name[:200], url, description,
                            source_label,
                            f"https://github.com/search?q={query}",
                            language or "unknown"
                        ))
                        if db.total_changes > 0:
                            new_items += 1
                    except Exception:
                        pass

                db.commit()
                page += 1

                # Rate limit 남은 횟수 확인
                remaining = int(resp.headers.get("X-RateLimit-Remaining", 60))
                if remaining < 5:
                    reset_time = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait = max(reset_time - int(time.time()), 5)
                    print(f"  Low rate limit ({remaining}), waiting {wait}s...")
                    time.sleep(wait)

                time.sleep(1.5)  # 부드럽게

            except Exception as e:
                print(f"  GitHub search '{query}' page {page} error: {e}")
                break

    db.execute(
        "INSERT INTO crawl_log (source, items_found, new_items, status) "
        "VALUES ('github-search', ?, ?, 'success')", (found, new_items)
    )
    print(f"GitHub Search: {found} found, {skipped} skipped (noise), {new_items} new")
    db.commit()
    db.close()
    return found, new_items


if __name__ == "__main__":
    from backend.db import init_db
    init_db()
    f, n = crawl_github_search()
    print(f"GitHub Search: {f} found, {n} new")
