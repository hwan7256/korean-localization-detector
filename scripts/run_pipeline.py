#!/usr/bin/env python3
"""전체 파이프라인: 크롤링 + 분석"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.db import init_db
from backend.crawlers.reddit_crawler import crawl_reddit
from backend.crawlers.web_crawler import crawl_all_web
from backend.analyzer.llm_analyzer import analyze_unanalyzed_services
from datetime import datetime


def run_pipeline():
    print(f"=== KLD Pipeline Start: {datetime.now()} ===")
    init_db()

    # 1. 크롤링
    print("[1/3] Crawling...")
    r_found, r_new = crawl_reddit(hours_back=12)
    print(f"  Reddit: {r_found} found, {r_new} new")
    w_found, w_new = crawl_all_web()
    total_new = r_new + w_new

    # 2. 분석
    if total_new > 0:
        print(f"[2/3] Analyzing {total_new} new services...")
        analyzed = analyze_unanalyzed_services(limit=10)
        print(f"  {analyzed} services analyzed")
    else:
        print("[2/3] No new services to analyze")

    print(f"[3/3] Pipeline complete: {datetime.now()}")
    return total_new


if __name__ == "__main__":
    run_pipeline()
