# NABIS 균형발전지표 대시보드

국가균형발전지원센터(NABIS)의 핵심·객관지표 데이터를 시도·시군구별, 년도별로 시각화하는 대시보드 프로젝트.

---

## 현재 진행 상태

`report/20260222-process.md` 참조 — 완료된 작업과 남은 작업이 정리되어 있음.

**완료:**
- NABIS XLS 자동 다운로드 (`download_nabis_index.py`)
- 지표 데이터 long-format 처리 (`build_dashboard_data.py`)
- 시군구 Shapefile 경량화 (`process_shapefile.py`)

**남은 작업:**
- NABIS 지역명 ↔ Shapefile 지역명 매핑 테이블 생성
- 대시보드 기술 스택 결정 및 MVP 구현

---

## 환경 구축 (다른 컴퓨터에서 시작할 때)

### 1. uv 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 가상환경 생성 및 의존성 설치

```bash
cd NABIS
uv python pin 3.12
uv venv
uv sync
```

이후 모든 스크립트는 `.venv/bin/python` (또는 `python`)으로 실행.

### 3. Git에 포함되지 않은 대용량 파일 별도 확보

아래 2종은 `.gitignore`에 의해 제외되어 있으므로, 직접 준비해야 한다.

#### (A) V-World 시군구 경계 Shapefile

- 출처: [국토정보플랫폼 V-World](https://map.vworld.kr/map/maps.do) > 공간정보 다운로드 > 행정구역 > 시군구
- 파일명: `BND_SIGUNGU_PG.shp` 외 4개 (cpg/dbf/prj/shx)
- 저장 경로: `datasets/shapefile/BND_SIGUNGU_PG/`
- 기준일: 2025년 6월 30일 기준 (`BASE_DATE=20250630`)

#### (B) 센서스 공간정보 지역 코드 엑셀

- 출처: 통계청 [e-나라지표](https://kosis.kr) 또는 [SGIS](https://sgis.kostat.go.kr) > 공간정보 다운로드
- 파일명: `센서스 공간정보 지역 코드.xlsx`
- 저장 경로: `datasets/shapefile/`
- 읽을 때 `header=1` 적용 필요 (1행이 제목 병합행)

> 위 2개 파일을 준비한 뒤 `python process_shapefile.py`를 실행하면
> `datasets/shapefile/SGG_2025/smooth_sgg_2025.json` (3.6 MB) 재생성 가능.

---

## 데이터 파이프라인

```
[NABIS 웹사이트]  →(download_nabis_index.py)→  datasets/index2025-claude/{시도}/{지역}.xls
                                                          ↓
                                              (build_dashboard_data.py)
                                                          ↓
datasets/processed/
  ├── indicators_long.csv       (56,325행 × 12열)
  ├── indicator_catalog.json    (46개 지표 메타)
  └── region_hierarchy.json     (시도 17 → 시군구 228)

[V-World Shapefile] →(process_shapefile.py)→  datasets/shapefile/SGG_2025/
  ├── sgg_20250630.json         (원본 해상도, 294 MB, .gitignore 제외)
  └── smooth_sgg_2025.json      (경량화, 3.6 MB)
```

---

## 스크립트 목록

| 파일 | 역할 |
|------|------|
| `download_nabis_index.py` | NABIS XLS 자동 다운로드 (Selenium) |
| `build_dashboard_data.py` | XLS → 처리 파일 3종 생성 |
| `process_shapefile.py` | Shapefile → 경량화 GeoJSON 생성 |
| `scrape_nabis_api.py` | HTTP requests 기반 대안 (참조용) |
| `analyze_dataset.py` | 데이터 탐색용 (임시) |
| `find_city_with_gu.py` | 구 단위 시 탐색 유틸 (임시) |

---

## 주요 데이터 파일

| 파일 | 크기 | 설명 |
|------|------|------|
| `datasets/processed/indicators_long.csv` | 6.8 MB | 핵심. 지역×년도×지표 |
| `datasets/processed/indicator_catalog.json` | 8 KB | 지표 메타데이터 |
| `datasets/processed/region_hierarchy.json` | 4 KB | 지역 계층 구조 |
| `datasets/shapefile/SGG_2025/smooth_sgg_2025.json` | 3.6 MB | 시군구 경계 (대시보드용) |
| `datasets/shapefile/센서스 공간정보 지역 코드.xlsx` | 3.1 MB | 시군구 코드-명칭 매핑 |

---

## 참조 문서

| 문서 | 내용 |
|------|------|
| `report/20260222-process.md` | **전체 진행 현황 및 다음 작업** |
| `report/index_data_structure.md` | XLS 파일 내부 구조 상세 |
| `report/NABIS_index_download_claude.md` | 다운로드 스크립트 설명 |
| `report/shapefile_analysis.md` | Shapefile 구조 및 NABIS 연계 방안 |
| `compact_messages/` | 세션별 작업 요약 (Claude 대화 compact) |

---

## Python 패키지

`pyproject.toml` 참조. 주요 패키지:

```
selenium, webdriver-manager   # 웹 자동화
xlrd, openpyxl, pandas        # 데이터 처리
geopandas, shapely, pyproj    # 지리 공간
matplotlib                    # 시각화
```
