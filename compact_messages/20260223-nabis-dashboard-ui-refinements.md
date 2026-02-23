# NABIS 대시보드 UI 개선 — 2026-02-23 (세션 2)

## 완료된 작업

### 1. 사이드바 정보 패널 시각 개선
- 플레인 텍스트 → 구조화된 HTML (flex 레이아웃, 컬러 값)
- 지자체값: `#2196F3` (파랑), 전국값: `#9E9E9E` (회색) — 차트 색상과 통일
- 스파크라인 차트에 범례 추가 (`showlegend=True`, 수평 범례)
- 기본 선택 지표: 플레이스홀더 → 첫 번째 지표 자동 선택
- 지도 영역에 지표명 타이틀 추가

### 2. 동명 시군구 매핑 오류 수정
- **증상**: 광주 서구가 인천 서구로 표시
- **원인**: 7종 중복 시군구명 (서구, 중구, 동구, 남구, 북구, 강서구, 고성군)
- **수정**: `sido + " " + sigungu` 복합키 도입
  - GeoJSON: `csv_sido_sigungu` 속성 추가 (`prepare_dashboard_data.py`)
  - CSV: `sido_sigungu` 컬럼 추가 (`app.py`)
  - Callback A: `locations="sido_sigungu"`, `featureidkey="properties.csv_sido_sigungu"`
  - Callback B: 모든 쿼리에 `sido` 필터 추가
- 기준년도 드롭다운 내림차순 정렬

### 3. 시도 외곽선 표시
- `prepare_dashboard_data.py`: SIDO_NM dissolve → `geo_sido_4326.json` (17개 시도)
- `make_valid()` 적용하여 TopologyException 해결
- `map_layers`로 시도 경계선 오버레이

### 4. 시도 경계선 스타일 조정
- 시군구 경계: `#ccc`, width 0.5
- 시도 기본 경계: `#888`, width 1
- 시도 강조 경계: `#1565C0`, width 2.5

### 5. 시도 호버 강조
- 클릭 기반 → 호버 기반으로 변경
- `Patch()` 사용하여 `map_layers`만 부분 업데이트 (성능 최적화)
- `_sido_geojson_cache`: 시도별 FeatureCollection 사전 빌드 (O(1) 조회)
- `uirevision="constant"`: 줌/팬 상태 보존
- `allow_duplicate=True`: 메인 콜백과 호버 콜백이 동일 Output 공유

---

## 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `prepare_dashboard_data.py` | `csv_sido_sigungu` 복합키, sido dissolve + make_valid() |
| `app.py` | 복합키 매핑, 정보 패널 HTML, 호버 강조, 스타일 조정 |

## 관련 파일

- 이전 세션: `compact_messages/20260223-nabis-dashboard-implementation.md`
- 구현 계획: `.claude/plans/buzzing-weaving-blanket.md`
- 레이아웃 스펙: `build_messages/layout.md`
