"""ConvertRadar — Playwright 웹 스크래퍼 (좌표 수집 및 캡처)"""
import os
import time
import uuid
from playwright.sync_api import sync_playwright

def scrape_with_coordinates(url: str, output_dir: str = "backend/static/screenshots") -> dict:
    """웹페이지를 크롤링하고 핵심 UI 요소들의 좌표와 텍스트를 추출하며 스크린샷을 찍음 (30초 제한 최적화)"""
    start_time = time.time()
    full_output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        output_dir
    )
    os.makedirs(full_output_dir, exist_ok=True)
    
    filename = f"shot_{uuid.uuid4().hex[:8]}.png"
    screenshot_path = os.path.join(full_output_dir, filename)
    screenshot_url = f"/static/screenshots/{filename}"
    
    result = {
        "url": url, "title": "", "meta_desc": "",
        "headers": {"h1": [], "h2": [], "h3": []},
        "cta_buttons": [], "text_content": "",
        "screenshot_url": screenshot_url, "screenshot_path": screenshot_path,
        "elements": [], "page_width": 1280, "page_height": 800,
        "load_time_ms": 0, "seo_metadata": {}
    }
    
    target_selectors = [
        "h1", "h2", "h3", "button",
        "a[role='button']", "a.btn", "a.button",
        "input[type='submit']", "input[type='button']"
    ]
    
    browser = None
    with sync_playwright() as p:
        if time.time() - start_time > 28:
            return result
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 페이지 로딩 타임아웃 계산 (남은 시간 기반, 최소 2초, 최대 15초)
            elapsed = time.time() - start_time
            goto_timeout = min(15000, max(2000, int((25 - elapsed) * 1000)))
            
            try:
                page.goto(url, wait_until="load", timeout=goto_timeout)
            except Exception as e:
                print(f"Playwright navigation timeout/error, proceeding: {e}")
            result["load_time_ms"] = int((time.time() - start_time) * 1000)
            
            # 스크롤 최적화 (최대 1.5초, viewport 로딩 자극 용도)
            if time.time() - start_time < 28:
                try:
                    page.evaluate("""
                        async () => {
                            await new Promise((resolve) => {
                                let totalHeight = 0, count = 0;
                                const distance = 300, maxScrolls = 5;
                                const timer = setInterval(() => {
                                    window.scrollBy(0, distance);
                                    totalHeight += distance; count++;
                                    if (totalHeight >= document.body.scrollHeight || totalHeight > 1500 || count >= maxScrolls) {
                                        clearInterval(timer);
                                        window.scrollTo(0, 0);
                                        resolve();
                                    }
                                }, 50);
                                setTimeout(() => { clearInterval(timer); window.scrollTo(0, 0); resolve(); }, 1500);
                            });
                        }
                    """)
                    page.wait_for_timeout(200)
                except Exception as e:
                    print(f"Scroll skipped: {e}")
            
            # 기본 정보
            result["title"] = page.title()
            meta_desc_el = page.locator('meta[name="description"]').first
            if meta_desc_el.count() > 0:
                result["meta_desc"] = meta_desc_el.get_attribute("content") or ""
            
            for h_type in ["h1", "h2", "h3"]:
                result["headers"][h_type] = [el.inner_text().strip() for el in page.locator(h_type).all() if el.inner_text().strip()][:15]
            
            buttons = page.locator('button, a[role="button"], a.btn, a.button').all()
            for btn in buttons[:15]:
                text = btn.inner_text().strip()
                if text:
                    result["cta_buttons"].append({"text": text, "href": btn.get_attribute("href") or ""})
            
            result["text_content"] = " ".join(page.locator('body').inner_text().split())[:4000]
            
            # SEO
            images = page.locator("img").all()
            total_imgs = len(images)
            missing_alt = sum(1 for img in images if not (img.get_attribute("alt") or "").strip())
            has_canonical = page.locator('link[rel="canonical"]').first.count() > 0
            
            result["seo_metadata"] = {
                "title_length": len(result["title"]),
                "meta_desc_length": len(result["meta_desc"]),
                "h1_count": len(result["headers"]["h1"]),
                "total_images": total_imgs,
                "missing_alt_images": missing_alt,
                "has_canonical": has_canonical
            }
            
            # 스크린샷 (전체 페이지, 최대 5000px 높이로 clip 제한)
            dims = page.evaluate("() => ({ w: window.innerWidth, h: document.body.scrollHeight })")
            clip_h = min(dims["h"], 5000)
            try:
                page.screenshot(path=screenshot_path, full_page=True, clip={"x":0,"y":0,"width":1280,"height":clip_h})
            except Exception:
                page.screenshot(path=screenshot_path, full_page=False)
            result["page_width"] = dims["w"]
            result["page_height"] = dims["h"]
            
            # 요소 좌표 추출 (is_visible 대신 bounding_box 유무로 빠른 필터링, Viewport 내 요소만 타겟팅)
            element_id = 0
            for selector in target_selectors:
                if time.time() - start_time > 27:
                    print("Timeout approaching, stopping element coordinates extraction early.")
                    break
                for loc in page.locator(selector).all():
                    if time.time() - start_time > 27:
                        break
                    try:
                        box = loc.bounding_box()
                        if not box:
                            continue
                        
                        # 극도로 작은 요소 제외
                        if box["width"] <= 10 or box["height"] <= 10:
                            continue
                            
                        text = loc.inner_text().strip()
                        tag = loc.evaluate("el => el.tagName.toLowerCase()")
                        element_id += 1
                        result["elements"].append({
                            "id": element_id, "tag": tag, "text": text[:100],
                            "x": box["x"], "y": box["y"],
                            "w": box["width"], "h": box["height"]
                        })
                        if element_id >= 60:
                            break
                    except Exception:
                        continue
                if element_id >= 60:
                    break
        finally:
            if browser:
                browser.close()
    
    return result

if __name__ == "__main__":
    test_url = "https://news.ycombinator.com"
    print(f"Testing scraper on {test_url}...")
    res = scrape_with_coordinates(test_url)
    print(f"Scrape complete! Title: {res['title']}, Elements: {len(res['elements'])}")
