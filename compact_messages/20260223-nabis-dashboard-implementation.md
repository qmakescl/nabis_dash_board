# NABIS 대시보드 구현 (Plotly Dash) — 2026-02-23

## 완료된 작업

### 1. GeoJSON 전처리 (`prepare_dashboard_data.py`)
- `smooth_sgg_2025.json` → `geo_sgg_4326.json` (EPSG:5179→4326 재투영)
- `csv_sigungu` 조인 키 추가 (세종시→세종특별자치시 매핑)
- 결과: 229개 feature, 3.3 MB

### 2. Dash 대시보드 (`app.py`) 생성
- **Section 1**: 데이터 로딩 (CSV `전라북도`→`전북특별자치도` 변환, 세종 시도→시군구 병합)
- **Section 2**: Figma 스펙 레이아웃 (200px 사이드바 + 코로플레스 지도)
- **Section 3**: 콜백 2개 (지도 갱신 + 사이드바 갱신)
- **Section 4**: `app.run(debug=True, port=8050)`

### 3. `pyproject.toml` 업데이트
- `dash>=2.18.0`, `plotly>=6.0.0` 추가, `uv sync` 완료

---

## 해결한 버그 2건

### Bug 1: Plotly 6.x API 변경 + customdata 오염
- **증상**: 지도 클릭 시 콜백 에러
- **원인**: `px.choropleth_mapbox` deprecated, `hover_data`가 customdata 배열 오염 (4열→2열 기대)
- **수정**: `px.choropleth_mapbox` → `px.choropleth_map`, `hover_data` 제거, `hovertemplate` 직접 지정, `point.get("customdata")` 방어 코드 추가

### Bug 2: reference_year 다양한 문자열 포맷
- **증상**: `ValueError: invalid literal for int() with base 10: '(2020-2024)'`
- **원인**: `reference_year` 컬럼에 `'2020년'`, `'(2017~2019)년'`, `'(2020-2024)'`, `'(2022-2024) 평균'`, `'-'` 등 다양한 포맷 존재
- **수정**: `int(r["reference_year"])` → `str(r["reference_year"]).rstrip("년")` + null/dash 체크

---

## 데이터 불일치 처리 (2건)

| 항목 | CSV | GeoJSON | 해결 |
|------|-----|---------|------|
| 전북 시도명 | `전라북도` | `전북특별자치도` | CSV 로딩 시 변환 |
| 세종 | 시도 레벨 `세종특별자치시`만 존재 | `세종시` 폴리곤 1개 | CSV 시도 데이터를 시군구로 복사, GeoJSON에 `csv_sigungu=세종특별자치시` |

---

## 현재 상태

- `http://localhost:8050` 서빙 중, HTTP 200 확인
- reference_year 버그 수정 후 사용자 확인 대기 중

## 남은 검증 체크리스트

- [ ] 229개 시군구 폴리곤 표시
- [ ] 기준년도/관심지표 변경 → 지도 색상 갱신
- [ ] 시군구 클릭 → 라벨, 텍스트 요약, 추이 차트 정상 표시
- [ ] 세종특별자치시 클릭 → 정상 표시
- [ ] 마우스 호버 → 툴팁

## 관련 파일

- 구현 계획: `.claude/plans/buzzing-weaving-blanket.md`
- 레이아웃 스펙: `build_messages/layout.md`
- Figma: `p0H5uYqgU0B6qPYBp7Eqaq`
