# NABIS 균형발전지표 Excel 다운로더 구현 (2026-02-22)

## 요약

NABIS 웹사이트에서 핵심·객관지표 데이터를 시도(17개) + 시군구(약 250개) 단위로 자동 다운로드하는 `download_nabis_index.py` 스크립트 구현 및 버그 수정.

---

## 주요 작업 내용

### 1. 신규 파일 생성
**`download_nabis_index.py`** - Selenium 기반 자동 다운로더

- 저장 경로: `datasets/index2025-claude/{시도명}/{지역명}.xls`
- Chrome Headless + CDP `Browser.setDownloadBehavior`로 headless 다운로드 활성화
- `_tmp/` 임시 폴더 → 파일 감지 → `shutil.move()`로 이름 지정 방식

### 2. 핵심 설정값
```python
NABIS_URL = "https://www.nabis.go.kr/totalStatisticsDetailView.do?menucd=168&menuFlag=Y"

SIDO_NODES_CSS = "#tree_menu > ul > li > ul > li.jstree-node"
ANCHOR_CSS = "a.jstree-anchor"
EXPAND_BTN_CSS = "i.jstree-ocl"
SIGUNGU_NODES_CSS = "ul.jstree-children > li.jstree-node > a.jstree-anchor"
DOWNLOAD_BTN_XPATH = "//button[contains(text(), '다운로드(지자체)')]"

CLICK_DELAY = 0.1
AJAX_WAIT = 2.0
EXPAND_WAIT = 1.5
DOWNLOAD_TIMEOUT = 30
```

---

## 발견 및 수정된 버그

### Bug 1: jstree 컨테이너 ID 오류
- **원인**: `#jstree` 셀렉터 사용 → 실제 ID는 `#tree_menu`
- **수정**: `#jstree` → `#tree_menu`

### Bug 2: `os.walk` 변수명 충돌
- **원인**: `for _, _, files in os.walk(...)` - `_` 변수 중복으로 경로 체크 실패
- **수정**: `for dirpath, _dirs, files in os.walk(...)` + `"_tmp" not in dirpath`

### Bug 3: 시군구 다운로드 전혀 안 됨 (복합 버그)
- **Bug 3a (치명적)**: `except` 블록에 `continue` → expand 버튼 못 찾으면 해당 시도의 시군구 전체 건너뜀
  ```python
  # 버그: except 안에 continue
  except Exception as e:
      continue  # ← 모든 시군구 건너뜀

  # 수정: continue 제거, 경고만 출력
  except Exception as e:
      print(f"    [경고] expand 버튼 오류 ({sido_name}): {e}")
  ```
- **Bug 3b**: `jstree-closed` 클래스 체크 로직 - 시도 클릭 시 jstree가 자동 `open` 상태로 변경되어 expansion 블록 전체 skip
  - **수정**: `jstree-closed` 체크 대신 DOM에 sigungu 노드가 있는지 먼저 확인 후, 없으면 expand 시도

### 최종 시군구 expansion 로직
```python
# 1단계: DOM에 시군구 노드가 이미 있는지 먼저 확인
sigungu_anchors = sido_node.find_elements(By.CSS_SELECTOR, SIGUNGU_NODES_CSS)

if not sigungu_anchors:
    # 2단계: jstree-leaf(하위 없는 노드)가 아니면 expand 시도
    node_class = sido_node.get_attribute("class")
    if "jstree-leaf" not in node_class:
        try:
            expand_btn = sido_node.find_element(By.CSS_SELECTOR, EXPAND_BTN_CSS)
            driver.execute_script("arguments[0].click();", expand_btn)
            time.sleep(CLICK_DELAY)
            time.sleep(EXPAND_WAIT)
        except Exception as e:
            print(f"    [경고] expand 버튼 오류 ({sido_name}): {e}")
        # 3단계: expand 후 재조회
        sido_nodes = driver.find_elements(By.CSS_SELECTOR, SIDO_NODES_CSS)
        sido_node = sido_nodes[i]
        sigungu_anchors = sido_node.find_elements(By.CSS_SELECTOR, SIGUNGU_NODES_CSS)
```

---

## 특이사항

- **세종특별자치시**: 하위 시군구가 없는 단일 시도 → `시군구 없음 (단일 시도)` 로그 출력, 정상 처리
- **Stale Element 방지**: 매 반복마다 DOM 요소 재조회 (`find_elements` 재호출)
- **루트 노드 자동 펼침**: 전국 루트 노드가 `jstree-closed`이면 자동 expand

---

## 미완료 / 검증 필요

- Bug 수정 후 재실행하여 시군구 다운로드 정상 작동 여부 확인 필요
- 전체 17개 시도 + ~250개 시군구 파일 수집 완료 후 Phase 2 진행 (지도-통계 매핑 JSON 구축)

---

## 관련 파일

| 파일 | 설명 |
|------|------|
| `download_nabis_index.py` | 메인 다운로더 (신규, 현재 수정 완료) |
| `scrape_nabis_data.py` | 기존 Selenium 뼈대 (참조용) |
| `scrape_nabis_api.py` | HTTP requests 기반 대안 접근법 (사용자 수정) |
| `parse_nabis.py` | 페이지 구조 분석용 스크립트 |
| `datasets/index2025-claude/` | 최종 저장 경로 |
