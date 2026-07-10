#!/usr/bin/env python3
"""전체 크롤링 통합 실행"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.db import init_db
from backend.crawlers.reddit_crawler import crawl_reddit
from backend.crawlers.web_crawler import crawl_all_web
from datetime import datetime


def main():
    print(f"=== KLD 크롤링 시작: {datetime.now()} ===")
    init_db()

    print("[Reddit] 크롤링 중...")
    r_found, r_new = crawl_reddit(hours_back=12)
    print(f"  Reddit: {r_found} posts found, {r_new} new")

    print("[Web] 크롤링 중...")
    w_found, w_new = crawl_all_web()

    total = r_new + w_new
    print(f"=== 크롤링 완료: 총 {total}개 신규 서비스 ===")
    return total


if __name__ == "__main__":
    main()
