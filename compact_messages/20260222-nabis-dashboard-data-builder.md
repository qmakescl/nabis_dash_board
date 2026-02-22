# NABIS 균형발전지표 대시보드 데이터 빌더 구현 (2026-02-22)

## 요약

NABIS 균형발전지표 XLS 파일들을 파싱하여 지리정보·년도별 대시보드 생성을 위한 3종 처리 파일을 생성하는 `build_dashboard_data.py` 구현 및 데이터 품질 이슈 수정.

---

## 주요 작업 내용

### 1. 환경 설정

- **uv 가상환경 단독 사용**: 시스템 Python 대신 workspace 전용 `.venv` 사용
- `pyproject.toml` 신규 생성 (uv 의존성 선언)
- `uv sync` 실행 → `xlrd 2.0.2` 포함 전체 의존성 설치
- 현재 가상환경에서 `python` 명령어로 실행 (python3 아님)

### 2. 신규 파일 생성

#### `build_dashboard_data.py`
- 전체 XLS 파일 순회 → 3종 처리 파일 생성
- **핵심 상수**:
  ```python
  YEAR_COLS = {
      2025: (7,  8,  9),
      2024: (10, 11, 12),
      2023: (13, 14, 15),
      2022: (16, 17, 18),
      2021: (19, 20, 21),
  }
  DATA_START_ROW = 6
  ```

#### `datasets/processed/indicators_long.csv` (6.8 MB)
- 56,325행 × 12열 long-format tidy 데이터
- 열: `sido, sigungu, region_type, publish_year, indicator_no, indicator_type, category, indicator_name, unit, local_value, national_value, reference_year`

#### `datasets/processed/indicator_catalog.json` (8 KB)
- 46개 지표 메타데이터 배열

#### `datasets/processed/region_hierarchy.json` (4 KB)
- 시도 17개 → 시군구 228개 계층 구조

### 3. 보고서 문서화

#### `report/NABIS_index_download_claude.md`
- 다운로드 스크립트 목적·기술·흐름·버그이력 문서화

#### `report/index_data_structure.md`
- XLS 52행×22열 구조 완전 문서화
- 46개 지표 전체 목록, 결측률, 파싱 가이드 코드 포함

---

## 발견 및 수정된 버그

### Bug 1: `return []` 과도한 처리 (build_dashboard_data.py)

- **원인**: 초기 버전에서 sido=='전국'이면 파일 전체를 `return []`로 포기
- **결과**: `창원시.xls` 전체가 스킵됨 (215개 레코드 손실)
- **실제 패턴**: 일부 지표(직주근접성, 지식기반산업집적도 등)는 시군구 수준 데이터가 없어 해당 행만 sido='전국'으로 표시됨
- **수정**: `return []` → `continue` (해당 행만 건너뜀)
  ```python
  # 수정 전
  if sido == "전국":
      return []   # ← 파일 전체 손실

  # 수정 후
  if sido == "전국":
      continue    # ← 해당 행만 건너뜀
  ```

### Bug 2: 미추홀구.xls 오진

- **초기 판단**: ALL rows가 sido='전국'
- **실제**: 핵심지표 2개 행만 sido='전국', 나머지 44개 지표는 인천광역시/미추홀구 데이터 존재
- **처리**: 위 Bug 1 수정으로 자동 해결. 미추홀구에서 핵심지표 2개는 없는 것이 맞음.

---

## XLS 파일 구조 요약

```
행 0:   제목행
행 1~3: 빈 행
행 4:   헤더 1단 (순번, 지표구분, 부문, 지표명, 단위, 시도, 시군구, 2025발표×3, ...)
행 5:   헤더 2단 (지자체/전국/기준년도 반복)
행 6~51: 데이터 46행 (지표순번 1~46)

col 0: 순번 (float 1.0~46.0)
col 1: 지표구분 (핵심지표/객관지표)
col 2: 부문
col 3: 지표명
col 4: 단위
col 5: 시도
col 6: 시군구 (시도파일은 시도명과 동일)
col 7~9:   2025발표 (지자체, 전국, 기준년도)
col 10~12: 2024발표
col 13~15: 2023발표
col 16~18: 2022발표
col 19~21: 2021발표
```

---

## 데이터 통계

| 발표년도 | local_value 유효률 |
|----------|--------------------|
| 2025     | 72.8%              |
| 2024     | 69.8%              |
| 2023     | 47.6% ← 결측 많음 |
| 2022     | 69.2%              |
| 2021     | 72.3%              |

> **2023년 결측 원인**: NABIS 공표 주기 차이로 추정

- **총 레코드**: 56,325건 (이론값 56,350 − 25건의 전국-행 제외)
- **지역**: 17개 시도 + 206개 시군구 (합계 223개 지역 유형)
- **계층**: region_hierarchy.json 기준 시도 17개, 시군구 228개

---

## 특이사항

- **sido='전국' 패턴**: 직주근접성(15), 지진옥외대피소(23), 지식기반산업집적도(39), 지역내 무역거래량(42), 핵심지표 일부 → 시군구 수준 데이터 NABIS 미제공
- **시도 vs 시군구 구분**: `col5(시도) == col6(시군구)`이면 시도 파일, 다르면 시군구 파일
- **단위 없는 지표**: 순번 15, 23, 39, 42 → `unit = ''`

---

## 미완료 / 다음 단계

- **지리 매핑**: `indicators_long.csv`와 행정구역 shapefile 연결 (시군구명 → 행정구역 코드)
- **대시보드 구축**: 준비된 3종 파일 기반 Plotly Dash 또는 웹 프론트엔드 개발
- **미추홀구 핵심지표**: 재다운로드로 데이터 보완 가능 (현재 핵심지표 2개 누락)

---

## 관련 파일

| 파일 | 설명 |
|------|------|
| `build_dashboard_data.py` | 메인 데이터 빌더 (신규) |
| `datasets/processed/indicators_long.csv` | 전체 long-format 데이터 (신규) |
| `datasets/processed/indicator_catalog.json` | 지표 메타데이터 (신규) |
| `datasets/processed/region_hierarchy.json` | 지역 계층 구조 (신규) |
| `report/index_data_structure.md` | XLS 구조 문서 (신규) |
| `report/NABIS_index_download_claude.md` | 다운로드 과정 문서 (신규) |
| `pyproject.toml` | uv 의존성 선언 (신규) |
