# 구현 계획: NABIS 균형발전지표 대시보드 (Plotly Dash)

## Context

NABIS 데이터 파이프라인(Phase 1~3)이 완료되어 4종의 처리 파일이 준비되었다.
이제 Figma 디자인(`build_messages/layout.md`)에 맞는 인터랙티브 대시보드를 구현한다.

**준비된 데이터:**
- `datasets/processed/indicators_long.csv` — 56,325행 (17시도 × 206시군구 × 5년 × 46지표)
- `datasets/processed/indicator_catalog.json` — 46개 지표 메타데이터
- `datasets/processed/region_hierarchy.json` — 시도→시군구 계층
- `datasets/shapefile/SGG_2025/smooth_sgg_2025.json` — 시군구 경계 GeoJSON (229개, EPSG:5179)

**데이터 불일치 (검증 완료, 3건):**
1. 시도명: CSV `전라북도` ↔ GeoJSON `전북특별자치도` → **CSV 쪽을 `전북특별자치도`로 변환** (최신 명칭 기준)
2. 세종: GeoJSON에 `세종시` 폴리곤 1개, CSV에는 시도 레벨 `세종특별자치시`로만 존재 → **세종은 단일 행정구역이므로 시군구 조회 시 시도 데이터를 사용, 조인 키는 `세종특별자치시`로 통일**
3. 군위군: 2023년 경상북도 → 대구광역시 편입. CSV는 `경상북도`, GeoJSON은 `대구광역시` → **CSV 쪽을 `대구광역시`로 변환** (최신 행정구역 기준)

---

## 기술 스택: Plotly Dash

**선택 이유:**
- Figma 스펙의 200px 사이드바, 정확한 색상·크기를 CSS `style={}` 로 직접 구현 가능
- `dcc.Graph`의 `clickData` 콜백으로 지도 클릭 → 사이드바 업데이트 자연스럽게 구현
- Plotly `choropleth_map`이 GeoJSON + 호버 툴팁 + 클릭 이벤트를 네이티브 지원
- Streamlit은 고정 200px 사이드바 불가, 클릭 인터랙션에 session state 해킹 필요

**추가 의존성:**
```toml
"dash>=2.18.0",
"plotly>=6.0.0",
```

---

## 생성할 파일 (2개)

### 1. `prepare_dashboard_data.py` (~57줄)

GeoJSON 전처리 스크립트. 한 번만 실행.

**처리 내용:**
1. `smooth_sgg_2025.json` 로딩 (geopandas)
2. EPSG:5179 → EPSG:4326 좌표 재투영 (Plotly 웹 지도에 WGS84 필수)
3. **세종 조인 키**: GeoJSON `SIGUNGU_NM == '세종시'` → `csv_sigungu = '세종특별자치시'` 로 매핑
4. **동명 시군구 복합키**: `csv_sido_sigungu = SIDO_NM + " " + csv_sigungu` (서구, 중구, 동구 등 7종 중복 해결)
5. **시도 외곽선 생성**: 시군구를 `SIDO_NM`으로 dissolve → `geo_sido_4326.json` (17개 시도)
   - `make_valid()` 적용하여 TopologyException 방지
6. 저장:
   - `datasets/processed/geo_sgg_4326.json` (시군구 경계)
   - `datasets/processed/geo_sido_4326.json` (시도 외곽선)

### 2. `app.py` (~400줄)

대시보드 메인 앱. 구조:

```
# SECTION 1: 데이터 로딩 (모듈 레벨, 앱 시작 시 1회)
#   - indicators_long.csv → pandas DataFrame
#   - CSV sido 변환: '전라북도' → '전북특별자치도' (최신 명칭 통일)
#   - 군위군 sido 변환: '경상북도' → '대구광역시' (2023년 편입 반영)
#   - 세종 처리: CSV에서 sido=='세종특별자치시' & region_type=='시도' 행을
#     시군구 데이터로 복사 (sigungu='세종특별자치시' 유지, GeoJSON csv_sigungu와 매칭)
#   - 동명 시군구 복합키: sido_sigungu = sido + " " + sigungu
#   - indicator_catalog.json → 드롭다운 옵션 리스트
#   - geo_sgg_4326.json → GeoJSON dict (json.load)
#   - geo_sido_4326.json → 시도 외곽선 GeoJSON
#   - 시도별 GeoJSON 캐시 생성 (호버 강조용)

# SECTION 2: 레이아웃 (Figma 스펙 1:1 매칭)
#   - 최외곽: display:flex, 1512×982px
#   - 사이드바: 200×982px, rgba(217,217,217,0.5), borderRight 1px #000
#     - "균형발전상황판" 타이틀 (Inter 24px, 200×60px, center)
#     - 기준년도 dcc.Dropdown (내림차순, 기본값=최신)
#     - 관심지표 dcc.Dropdown (46개 지표, 기본값=첫 번째 지표)
#     - 지역명 라벨 html.Div (동적: "{sido} - {sigungu}")
#     - 지표 요약 html.Div (동적: 지표명, 지자체값, 시도값, 전국값, 기준년도)
#     - 추이 차트 dcc.Graph (180×150px, displayModeBar=False)
#     - "Developed by Q" 푸터 (absolute bottom)
#   - 콘텐츠: flex:1, 982px 높이
#     - dcc.Graph (코로플레스 지도, 100% 너비/높이)

# SECTION 3: 콜백 3개
#   - Callback A: 지도 갱신 (년도/지표 변경)
#   - Callback B-hover: 시도 호버 강조 (Patch 부분 업데이트)
#   - Callback C: 사이드바 갱신 (지도 클릭)

# SECTION 4: app.run(debug=True, port=8050)
```

---

## 콜백 상세

### Callback A: 지도 갱신
- **Trigger**: `Input("year-select", "value")`, `Input("indicator-select", "value")`
- **Output**: `Output("choropleth-map", "figure")`
- **로직**:
  1. `df` 필터: `region_type=='시군구'` + 선택 연도 + 선택 지표
     - 세종: 시도 레벨 데이터가 시군구 데이터에 이미 병합되어 있으므로 별도 처리 불필요
     - 전북: CSV 로딩 시 `전라북도` → `전북특별자치도` 변환 완료 상태
     - 군위군: CSV 로딩 시 `경상북도` → `대구광역시` 변환 완료 상태
  2. GeoJSON feature별 `csv_sido_sigungu` 속성으로 `local_value` 매핑 (복합키)
  3. `px.choropleth_map` 생성:
     - `map_style="white-bg"` (타일 없는 흰 배경 → `paper_bgcolor="#D9D9D9"`)
     - `center={"lat": 36.5, "lon": 127.8}`, `zoom=5.8`
     - `color_continuous_scale="YlOrRd"`
     - `custom_data=["sido", "sigungu"]` — 클릭/호버 시 식별용
     - `hovertemplate` 직접 지정 (customdata 오염 방지)
     - 시군구 경계: `marker_line_color="#ccc"`, `marker_line_width=0.5`
  4. 시도 외곽선: `map_layers`로 GeoJSON line 레이어 오버레이 (`#888`, width 1)
  5. 지도 타이틀: `f"{indicator} ({unit})"` 중앙 상단 표시
  6. `uirevision="constant"` — 줌/팬 상태 보존
  7. NaN 지역: 중립 회색 표시 (Plotly 기본 동작)

### Callback B-hover: 시도 호버 강조
- **Trigger**: `Input("choropleth-map", "hoverData")`
- **Output**: `Output("choropleth-map", "figure", allow_duplicate=True)`
- **로직**:
  1. `Patch()` 사용하여 `layout.map.layers`만 부분 업데이트 (성능 최적화)
  2. `hoverData`에서 `customdata[0]` (sido) 추출
  3. `_sido_geojson_cache`에서 해당 시도 GeoJSON 조회 (O(1))
  4. 기본 시도 경계 + 강조 시도 경계 (`#1565C0`, width 2.5) 2개 레이어 설정
  5. `prevent_initial_call=True`

### Callback C: 사이드바 갱신 (지도 클릭)
- **Trigger**: `Input("choropleth-map", "clickData")`, `State("year-select")`, `State("indicator-select")`
- **Output**: `region-label`, `info-panel`, `sparkline`
- **로직**:
  1. `clickData`에서 `customdata` 추출 → `(sido, sigungu)` 식별
  2. 지역명 라벨: `f"{sido} - {sigungu}"` (세종은 `"세종특별자치시"`, 시도와 시군구가 동일하면 시도명만 표시)
  3. 텍스트 요약 (구조화 HTML):
     - 지표명 + 단위 (헤더)
     - 지자체값 (`#2196F3` 파랑)
     - 시도값 (`#FF9800` 주황) — `region_type=='시도'` 데이터에서 조회
     - 전국값 (`#9E9E9E` 회색)
     - 기준년도
  4. 추이 차트 (Sparkline):
     - 해당 지역 × 지표의 5개년(2021~2025) 데이터 필터
     - `go.Scatter` 3개 trace:
       - 지자체값: 실선 `#2196F3`, ● 마커, `connectgaps=False`
       - 시도값: 점선 `#FF9800`, ◆ 마커 (diamond)
       - 전국값: 파선 `#9E9E9E`, ○ 마커 (circle-open)
     - 선택 연도 마커 크기 1.5배 (size 7→10)
     - 수평 범례, 레이아웃: 180×150px, 최소 마진, "연도별 추이" 소제목
  5. `clickData is None` (초기 상태): 플레이스홀더 텍스트 표시, 빈 차트

---

## 수정할 기존 파일

### `pyproject.toml`
```toml
dependencies = [
    ...기존...
    # 대시보드
    "dash>=2.18.0",
    "plotly>=6.0.0",
]
```

---

## 구현 순서

| 단계 | 작업 | 파일 |
|------|------|------|
| 1 | `pyproject.toml`에 dash, plotly 추가 + `uv sync` | `pyproject.toml` |
| 2 | GeoJSON 전처리 스크립트 작성 + 실행 | `prepare_dashboard_data.py` |
| 3 | `app.py` 데이터 로딩 + 레이아웃 작성 | `app.py` |
| 4 | Callback A: 코로플레스 지도 + 시도 외곽선 구현 | `app.py` |
| 5 | Callback B-hover: 시도 호버 강조 (Patch) | `app.py` |
| 6 | Callback C: 클릭 → 사이드바 + 시도값 포함 요약 + 추이 차트 | `app.py` |
| 7 | 스타일 미세 조정 + 검증 | `app.py` |

---

## 데이터 불일치 처리 요약

| 항목 | CSV | GeoJSON | 해결 방법 |
|------|-----|---------|----------|
| 전북 시도명 | `전라북도` | `전북특별자치도` | CSV 로딩 시 `replace()` 변환 |
| 세종 | 시도 레벨 `세종특별자치시`만 존재 | `세종시` 폴리곤 1개 | CSV 시도 데이터를 시군구로 복사, GeoJSON에 `csv_sigungu=세종특별자치시` |
| 군위군 | `경상북도` (전 연도) | `대구광역시` | CSV 로딩 시 `loc[]` 변환 |
| 동명 시군구 | 서구, 중구, 동구 등 7종 | 동일 | `sido + " " + sigungu` 복합키로 1:1 매핑 |

---

## 해결한 주요 기술 이슈

### 1. Plotly 6.x API 변경
- `px.choropleth_mapbox` → `px.choropleth_map` (deprecated 대응)
- `hover_data` 파라미터가 `customdata` 배열 오염 → `hovertemplate` 직접 지정으로 해결

### 2. reference_year 다양한 문자열 포맷
- `'2020년'`, `'(2017~2019)년'`, `'(2020-2024)'`, `'-'` 등 다양한 포맷
- `str(r["reference_year"]).rstrip("년")` + null/dash 체크로 해결

### 3. TopologyException (시도 dissolve)
- 시군구 폴리곤에 유효하지 않은 geometry 존재
- `gdf_valid["geometry"].make_valid()` 적용 후 dissolve

### 4. 호버 성능 최적화
- `Patch()` 사용하여 `map_layers`만 부분 업데이트 (전체 figure 재생성 방지)
- `_sido_geojson_cache` 사전 빌드 (O(1) 조회)
- `uirevision="constant"` — 줌/팬 상태 유지

---

## 검증 체크리스트

1. `python prepare_dashboard_data.py` → `geo_sgg_4326.json`, `geo_sido_4326.json` 생성 확인
2. `python app.py` → `http://localhost:8050` 접속
3. 기능 검증:
   - [x] 지도에 229개 시군구 폴리곤 표시
   - [x] 기준년도 변경 → 지도 색상 갱신
   - [x] 관심지표 변경 → 지도 색상 갱신
   - [x] 시군구 클릭 → 라벨 "{시도} - {시군구}" 표시
   - [x] 클릭 → 텍스트 요약 (지자체값, 시도값, 전국값, 기준년도) 표시
   - [x] 클릭 → 추이 차트에 파란 실선(지자체) + 주황 점선(시도) + 회색 파선(전국) 표시
   - [x] 세종특별자치시 클릭 → 정상 표시
   - [x] 마우스 호버 → 툴팁 (지역명, 지표값)
   - [x] 시도 경계선 표시 + 호버 시 강조
   - [x] 동명 시군구 (서구, 중구 등) 정확한 매핑
   - [x] 군위군 → 대구광역시 소속으로 정상 표시
