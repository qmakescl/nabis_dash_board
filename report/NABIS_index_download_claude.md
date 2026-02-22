# NABIS 균형발전지표 Excel 다운로드 자동화 가이드

- [1. 목적 및 개요](#1-목적-및-개요)
- [2. 대상 페이지 및 데이터 구조](#2-대상-페이지-및-데이터-구조)
- [3. 저장 경로 구조](#3-저장-경로-구조)
- [4. 핵심 기술 구성](#4-핵심-기술-구성)
- [5. 코드 구조 및 흐름](#5-코드-구조-및-흐름)
- [6. CSS 셀렉터 상세](#6-css-셀렉터-상세)
- [7. 발견 및 해결된 버그](#7-발견-및-해결된-버그)
- [8. 실행 방법](#8-실행-방법)
- [9. 향후 작업 (Phase 2)](#9-향후-작업-phase-2)

---

## 1. 목적 및 개요

NABIS(균형발전종합정보시스템) 웹사이트에서 **핵심·객관지표** 데이터를 전국 **시도(17개) + 시군구(약 250개)** 단위로 자동 다운로드하는 스크립트.

- **스크립트 파일**: `download_nabis_index.py`
- **대상 URL**: `https://www.nabis.go.kr/totalStatisticsDetailView.do?menucd=168&menuFlag=Y`
- **다운로드 형식**: `.xls` (서버 제공 형식 그대로 유지)
- **총 예상 파일 수**: 약 267개 (시도 17 + 시군구 ~250)

---

## 2. 대상 페이지 및 데이터 구조

### 페이지 레이아웃

```
NABIS 균형발전지표 통계 상세 페이지
├── 좌측: jstree 지역 선택 트리
│   ├── [전국] (루트)
│   │   ├── 서울특별시
│   │   │   ├── 종로구
│   │   │   ├── 중구
│   │   │   └── ... (25개 자치구)
│   │   ├── 부산광역시
│   │   │   └── ... (16개 시·군·구)
│   │   ├── 세종특별자치시  ← 시군구 없는 단일 시도
│   │   └── ... (총 17개 시도)
└── 우측: 지표 통계 테이블 + "다운로드(지자체)" 버튼
```

### 트리 구조 특징

- **jstree** (jQuery 트리 플러그인) 기반
- 컨테이너 ID: `#tree_menu` (주의: `#jstree` 아님)
- **2단계 구조만 존재**: 시도 → 시군구 (행정구 3단계 없음)
- 세종특별자치시: `jstree-leaf` 노드 (하위 시군구 없음)
- expand 버튼: `<a class="jstree-icon jstree-ocl">` — **`<i>` 태그가 아닌 `<a>` 태그**

### 핵심 동작 흐름

1. 지역 anchor 클릭 → AJAX 호출 → 우측 테이블 갱신 (~2초 소요)
2. "다운로드(지자체)" 버튼 클릭 → Chrome이 `.xls` 파일 저장
3. jstree 노드 클릭 시 **비선택 노드의 텍스트가 DOM에서 제거**됨 (렌더링 최적화)

---

## 3. 저장 경로 구조

```
datasets/index2025-claude/
├── 서울특별시/
│   ├── 서울특별시.xls       ← 시도 클릭 후 다운로드
│   ├── 종로구.xls
│   ├── 중구.xls
│   └── ...
├── 부산광역시/
│   ├── 부산광역시.xls
│   ├── 중구.xls             ← 시도 폴더 내 저장으로 충돌 없음
│   └── ...
├── 세종특별자치시/
│   └── 세종특별자치시.xls   ← 시군구 없음, 시도 파일만
└── _tmp/                    ← Chrome 임시 다운로드 경로 (실행 중 사용)
```

---

## 4. 핵심 기술 구성

### 패키지

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `selenium` | 4.41.0 | Chrome 자동화 |
| `webdriver_manager` | 4.0.2 | ChromeDriver 자동 관리 |

### Headless Chrome 다운로드 활성화

Chrome headless 환경에서는 기본적으로 파일 다운로드가 비활성화되어 있다.
Chrome Preferences(`prefs`)만으로는 headless에서 다운로드가 차단되는 경우가 있어
**CDP(Chrome DevTools Protocol) 명령을 추가**로 호출해야 한다.

```python
driver.execute_cdp_cmd("Browser.setDownloadBehavior", {
    "behavior": "allow",
    "downloadPath": tmp_dir,  # 임시 폴더 절대 경로
})
```

### 파일 이름 지정 전략

다운로드된 파일명은 서버가 임의로 지정하므로, **임시 폴더(`_tmp/`) 방식**으로 이름을 지정한다:

1. 다운로드 전: `_tmp/` 폴더를 비움
2. "다운로드(지자체)" 버튼 클릭
3. `_tmp/`에 `.xls` 파일이 나타날 때까지 폴링 (최대 30초, 0.5초 간격)
4. `.crdownload` 확장자 파일은 다운로드 중 임시파일이므로 무시
5. 완료된 파일을 `{시도명}/{지역명}.xls`로 이동 + 이름 변경

---

## 5. 코드 구조 및 흐름

### 주요 함수

| 함수 | 역할 |
|------|------|
| `setup_directories(base_dir)` | 출력 폴더 + `_tmp` 임시 폴더 생성 |
| `init_driver(tmp_dir)` | Headless Chrome + CDP 다운로드 설정 |
| `clear_tmp(tmp_dir)` | 임시 폴더 비우기 |
| `wait_for_download(tmp_dir, timeout)` | `.xls` 파일 감지 폴링 |
| `move_file(src, dest_dir, dest_name)` | 파일 이동 + 이름 변경 |
| `get_anchor_name(anchor)` | jstree anchor에서 지역명 추출 |
| `click_download_button(driver, wait, label)` | 다운로드 버튼 클릭 |
| `download_nabis_index()` | 메인 실행 함수 |

### `get_anchor_name()` — 지역명 추출 전략

```python
def get_anchor_name(anchor):
    # 1순위: anchor.text (렌더링된 텍스트)
    text = anchor.text.strip()
    if text:
        return text
    # 2순위: href 속성 파싱 + URL 디코딩
    # href 형식: javascript:selectGrid("11010", "%EC%A2%85%EB%A1%9C%EA%B5%AC");
    href = anchor.get_attribute("href") or ""
    m = re.search(r'selectGrid\("([^"]+)",\s*"([^"]+)"\)', href)
    if m:
        return unquote(m.group(2))  # unquote 필수: 한글이 URL 인코딩됨
    return ""
```

**배경**: jstree는 클릭 시 비선택 노드의 텍스트를 DOM에서 제거한다.
`anchor.text`가 비어 있는 경우 `href` 속성에서 파싱하되, 한글이 URL 인코딩된 형태
(`%EC%A2%85%EB%A1%9C%EA%B5%AC` = `종로구`)이므로 반드시 `unquote()` 적용.

### 시군구 트리 확장 로직

```python
node_class = sido_node.get_attribute("class")

if "jstree-leaf" in node_class:
    # 시군구 없는 단일 시도 (세종특별자치시 등)
    sigungu_anchors = []
else:
    # jstree-open이 아닌 경우에만 expand 클릭
    if "jstree-open" not in node_class:
        try:
            expand_btn = sido_node.find_element(By.CSS_SELECTOR, "a.jstree-ocl")
            driver.execute_script("arguments[0].click();", expand_btn)
            time.sleep(0.1)
        except Exception as e:
            print(f"    [경고] expand 버튼 오류: {e}")
    # open 상태이든 방금 expand했든 하위 노드 로딩 대기
    time.sleep(1.5)
    # DOM 재조회 후 시군구 목록 수집
    sido_nodes = driver.find_elements(By.CSS_SELECTOR, SIDO_NODES_CSS)
    sido_node = sido_nodes[i]
    sigungu_anchors = sido_node.find_elements(By.CSS_SELECTOR, SIGUNGU_NODES_CSS)
```

### 전체 처리 흐름

```
init_driver() → headless Chrome + CDP download 설정
    ↓
NABIS URL 접속 → jstree 렌더링 대기 (최대 15초 + 2초)
    ↓
루트 노드(전국) 닫혀 있으면 자동 expand
    ↓
for 각 시도 i in range(17):
    ├─ DOM 재조회 → 시도 노드 획득
    ├─ get_anchor_name(anchor) → 시도명
    ├─ 시도 anchor 클릭 → sleep(0.1) + sleep(2.0)
    ├─ _tmp/ 비우기 → 다운로드 버튼 클릭 → 파일 대기 → 이동
    ├─
    ├─ jstree-leaf? → 시군구 없음 처리
    ├─ jstree-open? 아니면 → a.jstree-ocl 클릭
    ├─ sleep(1.5) → DOM 재조회 → 시군구 목록 획득
    └─ for 각 시군구 j:
           ├─ DOM 재조회 (Stale Element 방지)
           ├─ get_anchor_name(sgg_anchor) → 시군구명
           ├─ 시군구 anchor 클릭 → sleep(0.1) + sleep(2.0)
           ├─ _tmp/ 비우기 → 다운로드 버튼 클릭 → 파일 대기 → 이동
           └─ 저장: {시도명}/{시군구명}.xls
    ↓
완료 후 _tmp/ 정리 + 저장 파일 수 출력
```

---

## 6. CSS 셀렉터 상세

```python
# jstree 컨테이너 (실제 ID는 #tree_menu, #jstree 아님)
SIDO_NODES_CSS    = "#tree_menu > ul > li > ul > li.jstree-node"
ANCHOR_CSS        = "a.jstree-anchor"
EXPAND_BTN_CSS    = "a.jstree-ocl"   # <a> 태그 (i 태그 아님!)
SIGUNGU_NODES_CSS = "ul.jstree-children > li.jstree-node > a.jstree-anchor"
DOWNLOAD_BTN_XPATH = "//button[contains(text(), '다운로드(지자체)')]"
```

> **주의**: NABIS jstree의 expand 버튼은 `<i class="jstree-ocl">` (내부 접근성용 아이콘)이 아닌
> `<a class="jstree-icon jstree-ocl">` (실제 클릭 대상 a 태그)이다.

---

## 7. 발견 및 해결된 버그

### Bug 1: jstree 컨테이너 ID 오류

- **증상**: 시도 노드 0개 감지
- **원인**: 셀렉터에 `#jstree` 사용 → 실제 ID는 `#tree_menu`
- **수정**: `#jstree` → `#tree_menu`

### Bug 2: `os.walk` 변수명 충돌

- **원인**: `for _, _, files in os.walk(...)` — `_` 변수 중복으로 경로 조건 체크 실패
- **수정**: `for dirpath, _dirs, files in os.walk(...)` + `"_tmp" not in dirpath`

### Bug 3: expand 버튼 셀렉터 오류 (치명적)

- **증상**: `시군구 1개 처리 시작`, 시군구 이름이 시도명과 동일 (`서울특별시`)
- **원인**: `EXPAND_BTN_CSS = "i.jstree-ocl"` → 실제 클릭 요소는 `<a class="jstree-ocl">`
- **수정**: `EXPAND_BTN_CSS = "a.jstree-ocl"`

### Bug 4: expansion 로직 — `jstree-open` 상태 미처리

- **증상**: 시도 클릭 후 이미 `jstree-open` 상태인데 expand 시도 없이 시군구 0개 처리
- **원인**: 기존 코드가 `if not sigungu_anchors` 판단만 사용, expand 후 대기 없음
- **수정**: `jstree-leaf` / `jstree-open` 클래스 명시 체크, 항상 `EXPAND_WAIT` 대기 후 재조회

### Bug 5: 빈 이름 시군구 무한 건너뜀

- **증상**: `[경고] 빈 이름 시군구 건너뜀` — 한 번 발생하면 이후도 계속 발생
- **원인**: jstree 클릭 시 비선택 노드의 DOM 텍스트 제거 → `anchor.text` = `""`
- **수정**: `get_anchor_name()` 함수 도입 — `text` 우선, 없으면 `href` 파싱

### Bug 6: 한글 파일명 깨짐 (`%EC%A2%85...` 형태)

- **증상**: `.xls` 파일이 `%EC%A2%85%EB%A1%9C%EA%B5%AC.xls` 등 URL 인코딩된 이름으로 저장
- **원인**: `anchor.get_attribute("href")` 반환값이 URL 인코딩된 형태
  ```
  javascript:selectGrid("11010", "%EC%A2%85%EB%A1%9C%EA%B5%AC");
  ```
- **수정**: `from urllib.parse import unquote` 추가, `unquote(m.group(2))` 적용

---

## 8. 실행 방법

### 환경 준비

```bash
# .venv 활성화 (selenium, webdriver_manager 이미 설치됨)
source .venv/bin/activate
```

### 실행

```bash
python download_nabis_index.py
```

### 실행 로그 예시

```
저장 경로: .../datasets/index2025-claude
NABIS 접속 중: https://www.nabis.go.kr/...
시도 17개 감지됨

[1/17] 서울특별시
    저장: datasets/index2025-claude/서울특별시/서울특별시.xls
    [진단] 감지된 시군구(25개): ['종로구', '중구', '용산구', '성동구', '광진구']...
    시군구 25개 처리 시작
    └ [1/25] 종로구 → 종로구.xls
    └ [2/25] 중구 → 중구.xls
    ...

[8/17] 세종특별자치시
    저장: datasets/index2025-claude/세종특별자치시/세종특별자치시.xls
    시군구 없음 (단일 시도)
```

### 결과 확인

```bash
# 저장된 파일 수 확인
find datasets/index2025-claude -name "*.xls" | grep -v _tmp | wc -l
# 예상값: ~267개

# 시도별 파일 확인
ls datasets/index2025-claude/서울특별시/
```

### 기존 파일 정리 후 재실행

```bash
# 빈 이름 잘못 저장된 파일 정리
find datasets/index2025-claude -name ".xls" -delete

# 재실행
python download_nabis_index.py
```

---

## 9. 향후 작업 (Phase 2)

수집 완료 후 지도-통계 매핑 JSON 구축:

1. `.xls` 파일 파싱 → 지표별 수치 추출
2. 행정구역 코드 매핑 (shapefile ↔ 지역명)
3. GeoJSON + 통계 데이터 통합 JSON 생성
4. NABIS 대시보드 시각화 레이어 구성

관련 파일: `report/shapefile_analysis.md`

---

## 관련 파일

| 파일 | 설명 |
|------|------|
| `download_nabis_index.py` | 메인 다운로더 (현재 사용) |
| `scrape_nabis_data.py` | Selenium 기반 초기 뼈대 (참조용) |
| `scrape_nabis_api.py` | HTTP requests 기반 대안 접근법 |
| `parse_nabis.py` | 페이지 구조 분석 스크립트 |
| `datasets/index2025-claude/` | 다운로드 결과 저장 경로 |
| `report/nabis_page_analysis.md` | NABIS 페이지 구조 분석 |
| `report/shapefile_analysis.md` | 행정구역 shapefile 분석 |
