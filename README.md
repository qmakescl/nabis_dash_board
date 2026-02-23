# NABIS 균형발전지표 대시보드

국가균형발전지원센터(NABIS)의 핵심·객관지표 46종을 시도·시군구별, 년도별로 시각화하는 인터랙티브 대시보드.

- 229개 시군구 코로플레스 지도 (Plotly)
- 시군구 클릭 → 지자체/시도/전국 비교 + 연도별 추이 차트
- 마우스 호버 → 시도 경계 강조

---

## 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/qmakescl/nabis_dash_board.git
cd nabis_dash_board
```

### 2. uv 설치 (없는 경우)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 가상환경 생성 및 의존성 설치

```bash
uv python pin 3.12
uv venv
uv sync
```

### 4. GeoJSON 전처리 (최초 1회)

```bash
python prepare_dashboard_data.py
```

Shapefile(EPSG:5179)을 WGS84(EPSG:4326)로 재투영하고, 시도 외곽선 GeoJSON을 생성한다.

출력:
- `datasets/processed/geo_sgg_4326.json` (시군구 경계)
- `datasets/processed/geo_sido_4326.json` (시도 외곽선)

### 5. 대시보드 실행

```bash
python app.py
```

`http://localhost:8050` 에서 접속.

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
                                                        ↓
                                       (prepare_dashboard_data.py)
                                                        ↓
datasets/processed/
  ├── geo_sgg_4326.json         (시군구 경계, EPSG:4326)
  └── geo_sido_4326.json        (시도 외곽선, EPSG:4326)
                                                        ↓
                                              (app.py — Dash 서버)
                                                        ↓
                                           http://localhost:8050
```

---

## 대시보드 기능

| 기능 | 설명 |
|------|------|
| 코로플레스 지도 | 229개 시군구를 선택 지표값 기준으로 색상 표현 (YlOrRd) |
| 기준년도 선택 | 2021~2025 드롭다운 (내림차순) |
| 관심지표 선택 | 46개 지표 드롭다운 |
| 시군구 클릭 | 사이드바에 지자체/시도/전국 값 비교 표시 |
| 추이 차트 | 지자체(파랑) · 시도(주황) · 전국(회색) 5개년 추이 |
| 시도 호버 강조 | 마우스 호버 시 해당 시도 외곽선 강조 |
| 지도 타이틀 | 현재 선택 지표명 + 단위 표시 |

---

## 스크립트 목록

| 파일 | 역할 |
|------|------|
| `app.py` | **대시보드 메인 앱** (Plotly Dash, port 8050) |
| `prepare_dashboard_data.py` | GeoJSON 전처리 (EPSG:5179→4326, 시도 dissolve) |
| `download_nabis_index.py` | NABIS XLS 자동 다운로드 (Selenium) |
| `build_dashboard_data.py` | XLS → 처리 파일 3종 생성 |
| `process_shapefile.py` | Shapefile → 경량화 GeoJSON 생성 |

---

## 주요 데이터 파일

| 파일 | 크기 | 설명 |
|------|------|------|
| `datasets/processed/indicators_long.csv` | 6.6 MB | 지역×년도×지표 long-format |
| `datasets/processed/indicator_catalog.json` | 12 KB | 지표 메타데이터 (46종) |
| `datasets/processed/region_hierarchy.json` | 8 KB | 지역 계층 구조 |
| `datasets/processed/geo_sgg_4326.json` | 3.2 MB | 시군구 경계 (EPSG:4326) |
| `datasets/processed/geo_sido_4326.json` | 3.2 MB | 시도 외곽선 (EPSG:4326) |
| `datasets/shapefile/SGG_2025/smooth_sgg_2025.json` | 3.6 MB | 시군구 경계 원본 (EPSG:5179) |

---

## 데이터 불일치 처리

CSV와 GeoJSON 간 지역명 불일치를 `app.py` 로딩 시 자동 보정한다.

| 항목 | CSV | GeoJSON | 해결 |
|------|-----|---------|------|
| 전북 시도명 | `전라북도` | `전북특별자치도` | CSV `replace()` 변환 |
| 세종 | 시도 레벨만 존재 | `세종시` 폴리곤 1개 | CSV 시도→시군구 복사, GeoJSON `csv_sigungu=세종특별자치시` |
| 군위군 | `경상북도` | `대구광역시` | CSV `loc[]` 변환 (2023년 편입) |
| 동명 시군구 | 서구, 중구 등 7종 | 동일 | `sido+sigungu` 복합키 |

---

## Git에 포함되지 않은 대용량 파일

아래 파일은 `.gitignore`에 의해 제외되어 있으므로, 데이터를 처음부터 재생성하려면 직접 준비해야 한다.
**대시보드만 실행하려면 아래 파일은 필요 없다** (처리 완료 파일이 저장소에 포함됨).

### (A) V-World 시군구 경계 Shapefile

- 출처: [국토정보플랫폼 V-World](https://map.vworld.kr/map/maps.do) > 공간정보 다운로드 > 행정구역 > 시군구
- 저장 경로: `datasets/shapefile/BND_SIGUNGU_PG/`
- 기준일: 2025년 6월 30일

### (B) 센서스 공간정보 지역 코드 엑셀

- 출처: 통계청 SGIS > 공간정보 다운로드
- 저장 경로: `datasets/shapefile/센서스 공간정보 지역 코드.xlsx`

> 위 2개 파일을 준비한 뒤 `python process_shapefile.py`를 실행하면
> `datasets/shapefile/SGG_2025/smooth_sgg_2025.json` 재생성 가능.

---

## Python 패키지

`pyproject.toml` 참조. 주요 패키지:

```
dash, plotly               # 대시보드
pandas, numpy              # 데이터 처리
geopandas, shapely, pyproj # 지리 공간
selenium, webdriver-manager # 웹 자동화 (다운로드용)
xlrd, openpyxl             # Excel 파싱
```

---

## 참조 문서

| 문서 | 내용 |
|------|------|
| `implementation_plan/` | 대시보드 구현 계획서 |
| `build_messages/layout.md` | 대시보드 레이아웃 설계 (Figma 기반) |
| `report/20260222-process.md` | 데이터 파이프라인 진행 현황 |
| `compact_messages/` | 세션별 작업 요약 |
