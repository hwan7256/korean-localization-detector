# KLD 대시보드 모바일 UI 개선 계획

> **For Hermes:** 직접 dashboard.html을 수정하여 모바일 반응형을 적용한다.

**Goal:** 375px 너비의 모바일 화면에서도 KLD 대시보드가 깨지지 않고 사용 가능하게 만든다.

**Approach:** CSS 미디어 쿼리(@media)를 추가하여 모바일(≤768px)에서 레이아웃을 수직 스택으로 전환하고, 테이블은 가로 스크롤을 허용하며, 툴바는 줄바꿈 처리한다.

**현재 상태 분석:**
- CSS 전체 인라인 `<style>` 블록 하나, 미디어 쿼리 0개
- `table { min-width: 680px }` — 모바일에서 무조건 가로 스크롤 유발
- `.main` → `flex`, `.table-wrap` → `flex: 0 0 54%` — 디테일 패널이 46%로 너무 좁음
- `.toolbar` → `flex`, gap 10px — 5개 컨트롤이 한 줄에 안 들어감
- `.header` → `flex`, gap 24px — 메타 정보 공간 부족
- `body { overflow: hidden }` — 스크롤 불가능하게 막혀있음

---

## Task 1: 모바일 미디어 쿼리 추가 + body overflow 수정

**Objective:** 768px 이하에서 body overflow 허용 및 기초 반응형 토대 마련

**Files:**
- Modify: `dashboard.html` (gh-pages 브랜치)

**Step 1: body overflow를 auto로 변경**

기존:
```css
body{...overflow:hidden}
```
→ `overflow: hidden`을 `overflow: auto`로. 모바일에서 스크롤이 필요한데 hidden이 막고 있음.

**Step 2: 미디어 쿼리 구조 추가**

CSS 끝에 다음 추가:
```css
@media(max-width:768px){}
```

---

## Task 2: 메인 레이아웃 수직 스택

**Objective:** `.main`의 가로 분할을 세로로 전환

**Files:**
- Modify: `dashboard.html`

**Step 1: .main flex-direction 변경**

```css
@media(max-width:768px){
  .main{flex-direction:column}
  .table-wrap{flex:1 1 auto;border-right:none;border-bottom:1px solid var(--border)}
  .detail{flex:1 1 auto;max-height:50vh;overflow-y:auto}
}
```

`.table-wrap`이 위에, `.detail`이 아래에 배치된다. 디테일 패널은 화면의 절반 높이로 제한하고 내부 스크롤.

---

## Task 3: 테이블 가로 스크롤 허용

**Objective:** 테이블이 짤리지 않고 가로로 스크롤 가능하게

```css
@media(max-width:768px){
  .table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
  table{min-width:680px}
}
```

`min-width`는 유지하되 `.table-scroll`에 `overflow-x: auto`를 줘서 네이티브 가로 스크롤로 대응. `-webkit-overflow-scrolling: touch`로 iOS 부드러운 스크롤.

---

## Task 4: 툴바 줄바꿈

**Objective:** 5개 필터 컨트롤이 모바일에서 두 줄로 자연스럽게 배치

```css
@media(max-width:768px){
  .toolbar{flex-wrap:wrap;padding:8px 12px;gap:6px}
  .toolbar select,.toolbar input{flex:1 1 auto;min-width:80px;font-size:0.75rem;padding:6px 8px}
  .toolbar input{width:auto;min-width:120px}
  .toolbar .count{width:100%;text-align:right;margin-top:2px}
}
```

`flex-wrap: wrap`으로 줄바꿈 허용, 각 컨트롤은 `flex: 1 1 auto`로 균등 분배. 검색창은 `width: auto`로 유연하게.

---

## Task 5: 헤더 및 기타 요소 축소

**Objective:** 헤더와 메타 정보가 모바일에서 깨지지 않게

```css
@media(max-width:768px){
  .header{padding:10px 12px;gap:12px}
  .logo{font-size:1rem}
  .back{display:none}
  .header-meta{gap:14px}
  .meta-val{font-size:0.85rem}
  .meta-label{font-size:0.55rem}
}
```

"← 랜딩으로" 링크는 모바일에서 숨기고(로고 클릭으로 대체 가능), 메타 정보 폰트 축소.

---

## Task 6: 배포 및 검증

**Step 1: 파일 수정 후 gh-pages에 푸시**

```bash
git add dashboard.html
git commit -m "fix: mobile responsive dashboard"
git push origin gh-pages
```

**Step 2: 모바일에서 확인**

- `kld.etfsimulator.blog/dashboard.html` 접속
- Chrome DevTools Device Mode로 iPhone SE(375px) / iPhone 12(390px) 테스트
- 가로 스크롤이 자연스러운지, 디테일 패널이 하단에 잘 나오는지, 툴바가 두 줄로 나오는지 확인

---

## 요약

| 변경 | 효과 |
|------|------|
| `body{overflow:auto}` | 모바일 전체 스크롤 가능 |
| `.main{flex-direction:column}` | 테이블→디테일 수직 배치 |
| `.table-scroll{overflow-x:auto}` | 테이블 가로 스크롤 |
| `.toolbar{flex-wrap:wrap}` | 필터 줄바꿈 |
| 헤더 축소 + back 숨김 | 공간 확보 |
