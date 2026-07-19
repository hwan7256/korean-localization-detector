"""ConvertRadar — 자사 대시보드를 직접 Playwright로 캡처하여 시각화 테스트"""
import os
import time
from playwright.sync_api import sync_playwright

def capture_dashboard():
    # 캡처를 저장할 아티팩트 경로 설정
    artifact_dir = "/root/.gemini/antigravity-cli/brain/90e8b1bb-a645-46b0-896b-458b6ddb92bc"
    os.makedirs(artifact_dir, exist_ok=True)
    screenshot_path = os.path.join(artifact_dir, "dashboard_live.png")
    
    print("Starting browser session to capture ConvertRadar dashboard...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 1280x1200 크기 뷰포트 설정
        context = browser.new_context(viewport={"width": 1280, "height": 1200})
        page = context.new_page()
        
        # 1. 자사 메인 페이지 접속
        print("Connecting to http://localhost:8733 ...")
        page.goto("http://localhost:8733", wait_until="networkidle", timeout=15000)
        
        # 2. 인풋값 입력
        print("Filling target URL and audience...")
        page.fill("#targetUrl", "https://news.ycombinator.com")
        page.fill("#targetAudience", "Tech Founders")
        
        # 3. 진단 시작 버튼 클릭
        print("Clicking analysis button...")
        page.click("button.btn-analyze")
        
        # 4. 분석이 완료되어 대시보드가 노출될 때까지 대기 (최대 30초)
        print("Waiting for DeepSeek analysis and dashboard render...")
        try:
            page.wait_for_selector("#dashboardView", state="visible", timeout=40000)
            # 차트 애니메이션 및 오버레이 티피 툴팁 등 렌더링 완료 대기
            page.wait_for_timeout(3000)
            print("Dashboard rendered successfully!")
        except Exception as e:
            print(f"Failed to load dashboard within timeout: {e}")
            # 에러 발생 시 현재 상태 캡처 후 종료
            page.screenshot(path=screenshot_path)
            browser.close()
            return False
            
        # 5. 전체 페이지 캡처 저장
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Live Dashboard screenshot saved to: {screenshot_path}")
        browser.close()
        return True

if __name__ == "__main__":
    capture_dashboard()
