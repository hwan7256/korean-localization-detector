#!/usr/bin/env python3
"""국내 API 레퍼런스 데이터베이스 시딩"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import get_db

KOREAN_APIS = [
    # 결제
    {"name": "토스페이먼츠", "category": "결제",
     "description": "토스의 온라인 결제 대행. 카드/계좌이체/간편결제 지원. 연동 난이도 낮음.",
     "docs_url": "https://docs.tosspayments.com", "pricing_info": "수수료 3.3% 내외, 가입비 무료"},
    {"name": "포트원 (PortOne)", "category": "결제",
     "description": "구 아임포트. 20여개 PG사 통합 결제 연동. KG이니시스/토스/카카오페이 등.",
     "docs_url": "https://portone.io/docs", "pricing_info": "기본 무료, PG 수수료 별도"},
    {"name": "카카오페이", "category": "결제",
     "description": "4천만 사용자 기반 간편결제. 온/오프라인 모두 지원.",
     "docs_url": "https://developers.kakao.com/docs/latest/ko/kakaopay", "pricing_info": "수수료 2.5% 내외"},
    {"name": "네이버페이", "category": "결제",
     "description": "네이버쇼핑 연동 간편결제. 주문형/결제형 선택 가능.",
     "docs_url": "https://developer.pay.naver.com", "pricing_info": "수수료 2.2% 내외"},

    # 메시징
    {"name": "카카오 알림톡", "category": "메시징",
     "description": "카카오톡 기반 정보성 비즈니스 메시지. SMS보다 저렴하고 신뢰도 높음.",
     "docs_url": "https://business.kakao.com", "pricing_info": "건당 5~10원"},
    {"name": "알리고 (Aligo)", "category": "메시징",
     "description": "국내 SMS/LMS/MMS 발송 1위. REST API 연동 간편.",
     "docs_url": "https://smartsms.aligo.in", "pricing_info": "SMS 건당 9원부터"},
    {"name": "카카오비즈메시지", "category": "메시징",
     "description": "친구톡(광고성) + 알림톡(정보성). 카카오 채널과 연동.",
     "docs_url": "https://center-pf.kakao.com", "pricing_info": "친구톡 10~20원, 알림톡 5~10원"},

    # 푸시
    {"name": "NHN Cloud Notification", "category": "푸시",
     "description": "FCM/APNS 통합 푸시. 국내 점유율 1위. 월 10만건 무료.",
     "docs_url": "https://docs.nhncloud.com", "pricing_info": "월 10만건 무료, 이후 종량제"},

    # 인증
    {"name": "카카오 로그인", "category": "인증",
     "description": "국민 메신저 기반 소셜 로그인. 한국 사용자 90% 이상 보유.",
     "docs_url": "https://developers.kakao.com", "pricing_info": "무료"},
    {"name": "네이버 로그인", "category": "인증",
     "description": "네이버 아이디로 로그인. 카페/블로그 연동 가능.",
     "docs_url": "https://developers.naver.com", "pricing_info": "무료"},
    {"name": "PASS 인증", "category": "인증",
     "description": "통신3사 공동 본인인증. 법적 본인확인 필수 시 사용.",
     "docs_url": "https://www.pass.or.kr", "pricing_info": "건당 120~150원"},

    # 지도
    {"name": "카카오 맵", "category": "지도",
     "description": "국내 지도 점유율 1위. 장소검색/길찾기 REST API.",
     "docs_url": "https://apis.map.kakao.com", "pricing_info": "일 30만건 무료"},
    {"name": "네이버 지도", "category": "지도",
     "description": "네이버 지도 API. 국내 상세도 높고 지적편집도 지원.",
     "docs_url": "https://navermaps.github.io", "pricing_info": "일 5만건 무료"},

    # 클라우드/호스팅
    {"name": "네이버 클라우드", "category": "클라우드",
     "description": "국내 법인 클라우드 점유율 1위. 개인정보보호법 컴플라이언스.",
     "docs_url": "https://www.ncloud.com", "pricing_info": "종량제"},
    {"name": "카페24", "category": "호스팅",
     "description": "국내 최대 웹호스팅. 설치형 쇼핑몰부터 클라우드까지.",
     "docs_url": "https://www.cafe24.com", "pricing_info": "웹호스팅 월 500원부터"},

    # 문서/계약
    {"name": "모두싸인", "category": "문서",
     "description": "국내 1위 전자계약. API로 계약서 발송/서명 연동.",
     "docs_url": "https://developers.modusign.co.kr", "pricing_info": "월 5건 무료"},

    # 노코드
    {"name": "아임웹", "category": "노코드",
     "description": "국내 쇼핑몰/웹사이트 빌더. PG 연동, 도메인 기본 제공.",
     "docs_url": "https://www.imweb.me", "pricing_info": "월 1만원부터"},
]


def seed():
    db = get_db()
    for api in KOREAN_APIS:
        db.execute("""
            INSERT OR REPLACE INTO korean_apis (name, category, description, docs_url, pricing_info)
            VALUES (?, ?, ?, ?, ?)
        """, (api["name"], api["category"], api["description"], api["docs_url"], api["pricing_info"]))
    db.commit()
    db.close()
    print(f"국내 API {len(KOREAN_APIS)}개 시딩 완료")


if __name__ == "__main__":
    seed()
