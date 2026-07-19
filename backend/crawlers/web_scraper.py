"""ConvertRadar — Playwright 웹 스크래퍼 (좌표 수집 및 캡처)"""
import os
import time
import uuid
from playwright.sync_api import sync_playwright

def scrape_with_coordinates(url: str, output_dir: str = "backend/static/screenshots") -> dict:
    """웹페이지를 크롤링하고 핵심 UI 요소들의 좌표와 텍스트를 추출하며 스크린샷을 찍음"""
    # 캡처 저장 디렉토리 생성
    full_output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        output_dir
    )
    os.makedirs(full_output_dir, exist_ok=True)
    
    filename = f"shot_{uuid.uuid4().hex[:8]}.png"
    screenshot_path = os.path.join(full_output_dir, filename)
    screenshot_url = f"/static/screenshots/{filename}"
    
    result = {
        "url": url,
        "title": "",
        "meta_desc": "",
        "headers": {"h1": [], "h2": [], "h3": []},
        "cta_buttons": [],
        "text_content": "",
        "screenshot_url": screenshot_url,
        "screenshot_path": screenshot_path,
        "elements": [],
        "page_width": 1280,
        "page_height": 800,
        "load_time_ms": 0,
        "seo_metadata": {}
    }
    
    # 크롤링 타겟 셀렉터
    target_selectors = [
        "h1", "h2", "h3",
        "button", 
        "a[role='button']", 
        "a.btn", 
        "a.button",
        "input[type='submit']",
        "input[type='button']"
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 1280x800 브라우저 창 크기로 일관되게 분석
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 페이지 로딩 시간 측정 (실제 브라우저 로딩 시간만 측정하고, 스크롤 시간은 제외)
        start_time = time.time()
        try:
            page.goto(url, wait_until="load", timeout=15000)
            result["load_time_ms"] = int((time.time() - start_time) * 1000)
        except Exception as e:
            # 타임아웃이 나더라도 이미 페이지 DOM은 로드되었을 가능성이 높으므로 중단하지 않고 계속 진행
            print(f"Playwright navigation load timeout, proceeding anyway: {e}")
            result["load_time_ms"] = int((time.time() - start_time) * 1000)
            
        # 지연 로딩 이미지 및 동적 콘텐츠 렌더링 활성화를 위해 자동 스크롤 실행 (예외가 났더라도 계속 실행)
        try:
            page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 300;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= scrollHeight || totalHeight > 6000) {
                                clearInterval(timer);
                                window.scrollTo(0, 0); // 다시 맨 위로 스크롤 복구
                                resolve();
                            }
                        }, 50);
                    });
                }
            """)
            page.wait_for_timeout(1000) # 안정화 대기
        except Exception as e:
            print(f"Scroll evaluation skipped/failed: {e}")

        # 기본 정보 수집
        result["title"] = page.title()
        meta_desc_el = page.locator('meta[name="description"]').first
        if meta_desc_el.count() > 0:
            result["meta_desc"] = meta_desc_el.get_attribute("content") or ""
            
        # Headers 수집
        for h_type in ["h1", "h2", "h3"]:
            elements = page.locator(h_type).all()
            headers_list = []
            for el in elements:
                t = el.inner_text().strip()
                if t:
                    headers_list.append(t)
            result["headers"][h_type] = headers_list[:15] # 한도 확장
            
        # CTA 버튼 수집
        buttons = page.locator('button, a[role="button"], a.btn, a.button').all()
        for btn in buttons[:15]: # 한도 확장
            text = btn.inner_text().strip()
            href = btn.get_attribute("href") or ""
            if text:
                result["cta_buttons"].append({"text": text, "href": href})
                
        # 본문 텍스트 추출 (LLM 컨텍스트 전달용)
        body_text = page.locator('body').inner_text()
        result["text_content"] = " ".join(body_text.split())[:4000]
        
        # 온페이지/테크니컬 SEO 메타데이터 추가 분석
        images = page.locator("img").all()
        total_imgs = len(images)
        missing_alt_imgs = 0
        for img in images:
            try:
                alt = img.get_attribute("alt")
                if not alt or not alt.strip():
                    missing_alt_imgs += 1
            except Exception:
                missing_alt_imgs += 1
                
        canonical_el = page.locator('link[rel="canonical"]').first
        has_canonical = canonical_el.count() > 0
        
        result["seo_metadata"] = {
            "title_length": len(result["title"]),
            "meta_desc_length": len(result["meta_desc"]),
            "h1_count": len(result["headers"]["h1"]),
            "total_images": total_imgs,
            "missing_alt_images": missing_alt_imgs,
            "has_canonical": has_canonical
        }
        
        # 브라우저 실제 크기 획득
        dimensions = page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight, scrollHeight: document.body.scrollHeight })")
        result["page_width"] = dimensions["width"]
        result["page_height"] = dimensions["scrollHeight"] # 전체 스크롤 높이 기입
        
        # 전체 랜딩페이지 전체 화면 스크린샷 저장 (full_page=True)
        page.screenshot(path=screenshot_path, full_page=True)
        
        # 각 요소의 절대 좌표값 수집 (전체 페이지 영역)
        element_id = 0
        for selector in target_selectors:
            locators = page.locator(selector).all()
            for loc in locators:
                try:
                    if not loc.is_visible():
                        continue
                    
                    box = loc.bounding_box()
                    text = loc.inner_text().strip()
                    tag = loc.evaluate("el => el.tagName.toLowerCase()")
                    
                    # 픽셀이 일정 수준 이상이고 텍스트가 있는 경우만 포함
                    if box and (box["width"] > 10 and box["height"] > 10):
                        element_id += 1
                        result["elements"].append({
                            "id": element_id,
                            "tag": tag,
                            "text": text[:100],
                            "x": box["x"],
                            "y": box["y"],
                            "w": box["width"],
                            "h": box["height"]
                        })
                        
                        # 컨텍스트가 너무 비대해지는 것을 방지하기 위해 최대 60개 엘리먼트만 수집
                        if element_id >= 60:
                            break
                except Exception:
                    continue
            if len(result["elements"]) >= 60:
                break
                
        browser.close()
        
    return result

if __name__ == "__main__":
    # 스크래퍼 단독 동작 테스트
    test_url = "https://news.ycombinator.com"
    print(f"Testing scraper on {test_url}...")
    res = scrape_with_coordinates(test_url)
    print("Scrape complete!")
    print(f"Title: {res['title']}")
    print(f"Found {len(res['elements'])} elements.")
    print(f"Screenshot saved to: {res['screenshot_path']}")
