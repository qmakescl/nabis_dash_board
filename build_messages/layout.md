# NABIS 대시보드 레이아웃 설계

Figma 파일: `NABIS_Dashboard_01`
파일 키: `p0H5uYqgU0B6qPYBp7Eqaq`
프로토타입: https://www.figma.com/proto/p0H5uYqgU0B6qPYBp7Eqaq/NABIS_Dashboard_01

---

## 전체 캔버스 구조

```
┌──────────────────────────────────────────────────────────────┐
│ 1512 × 982 px                                                │
│                                                              │
│  ┌──────────┐  ┌────────────────────────────────────────┐   │
│  │ SIDEBAR  │  │            CONTENTS (MAP)              │   │
│  │  200px   │  │              1312 × 982                │   │
│  │          │  │                                        │   │
│  │          │  │         인터랙티브 지도 영역           │   │
│  │          │  │        (코로플레스 맵)                 │   │
│  │          │  │                                        │   │
│  │          │  │                                        │   │
│  └──────────┘  └────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 사이드바 (Sidebar)

| 속성 | 값 |
|------|----|
| 너비 | 200px |
| 높이 | 982px (전체 높이) |
| 위치 | x=0, y=0 |
| 배경색 | rgba(217, 217, 217, 0.5) — 반투명 회색 |
| 오른쪽 테두리 | 1px solid #000000 |

### 사이드바 내부 구성 (위→아래)

```
┌────────────────────────┐
│  균형발전상황판         │  ← title (200×60px, y=0)
│  Inter 24px / CENTER   │
├────────────────────────┤
│                        │
│  [기준년도 드롭다운]    │  ← y≈70 (sidebar controls 영역 시작)
│                        │
│  [관심지표 드롭다운]    │
│                        │
│  서울특별시 - 종로구    │  ← 지역명 라벨 (동적 치환)
│  ┌──────────────────┐  │
│  │ 인구 1000명당     │  │  ← 지표명 (단위)
│  │ 의사 수 (명)      │  │
│  │                  │  │
│  │ 지자체: 3.2      │  │  ← 기준년도 지자체값
│  │ 전국:   2.8      │  │  ← 기준년도 전국값
│  │ 기준:   2025년   │  │
│  │                  │  │
│  │  연도별 추이      │  │  ← 소제목
│  │ 4┤ ●            │  │
│  │ 3┤   ●  ●    ●  │  │  ● 지자체값 (파란 실선)
│  │ 2┤─○──○──○──○  │  │  ○ 전국값   (회색 파선)
│  │  └──────────────  │  │
│  │  21 22 23 24 25  │  │  ← X축: 연도
│  └──────────────────┘  │
│                        │
├────────────────────────┤
│  Developed by Q        │  ← footer (200×40px, y=942)
└────────────────────────┘
```

---

## 사이드바 컴포넌트 상세

컨트롤 공통 레이아웃 (`layout_M3XO45`):
- 배치: Column (세로 스택)
- 갭: 8px
- 좌우 패딩: 10px
- 너비: 200px (고정)
- 높이: hug (내용에 맞춤)

### 1. 기준년도 (Select Field)

**Figma 노드 ID**: `1:137`
**컴포넌트**: `Select Field` (`1:74`)

| 속성 | 값 |
|------|----|
| 라벨 | 기준년도 |
| 플레이스홀더 | 년도 |
| 타입 | 드롭다운 (Chevron down 아이콘 포함) |
| 선택박스 패딩 | 12px 12px 12px 16px |
| 선택박스 테두리 | 1px solid #D9D9D9, 8px radius |
| 텍스트색 | #1E1E1E |
| 배경색 | #FFFFFF |

**동적 데이터 연결:**
- 선택 옵션: `2021, 2022, 2023, 2024, 2025`
- 데이터 소스: `datasets/processed/indicators_long.csv`의 `publish_year` 컬럼 유니크값
- 기본값: 최신 연도 (`2025`)

---

### 2. 관심지표 (Select Field)

**Figma 노드 ID**: `1:209`
**컴포넌트**: `Select Field` (`1:74`)

| 속성 | 값 |
|------|----|
| 라벨 | 관심지표 |
| 플레이스홀더 | 지표선택 |
| 타입 | 드롭다운 (Chevron down 아이콘 포함) |
| 선택박스 패딩 | 12px 12px 12px 16px |
| 선택박스 테두리 | 1px solid #D9D9D9, 8px radius |

**동적 데이터 연결:**
- 선택 옵션: 46개 지표명 (indicator_no + indicator_name)
- 데이터 소스: `datasets/processed/indicator_catalog.json`
- 표시 형식: `{indicator_no}. {indicator_name}` 또는 `{indicator_name}`
- 기본값: 첫 번째 지표 또는 플레이스홀더

---

### 3. 지자체별지표요약 (Info Panel + Trend Chart)

**Figma 노드 ID**: `1:191` (원본 Textarea → 패널+차트 복합 컴포넌트로 대체)

#### 3-A. 지역명 라벨

| 속성 | 값 |
|------|----|
| 내용 | `{sido} - {sigungu}` (동적 치환) |
| 예시 | `서울특별시 - 종로구` |
| 폰트 | Inter 14px, Bold, #1E1E1E |
| 패딩 | 10px 10px 4px 10px |

#### 3-B. 지표 텍스트 요약

| 속성 | 값 |
|------|----|
| 테두리 | 1px solid #D9D9D9, 8px radius (상단 절반) |
| 패딩 | 10px 10px 6px 10px |
| 배경색 | #FFFFFF |

**표시 내용:**
```
{indicator_name} ({unit})

지자체:  {local_value}
전국:    {national_value}
기준:    {reference_year}년
```

#### 3-C. 연도별 추이 미니 차트 (Trend Sparkline)

| 속성 | 값 |
|------|----|
| 크기 | 180 × 130px (10px 좌우 패딩 적용) |
| 테두리 | 1px solid #D9D9D9, 0 0 8px 8px radius (하단 절반) |
| 배경색 | #FFFFFF |
| X축 | 연도 (2021, 2022, 2023, 2024, 2025) |
| Y축 | 지표값 범위 자동 조정 (min~max, 레이블 2~3개) |

**차트 구성:**

| 데이터 시리즈 | 스타일 | 설명 |
|--------------|--------|------|
| 지자체값 (`local_value`) | 실선 `#2196F3` (파랑), 원형 마커 ● | 선택 시군구의 연도별 값 |
| 전국값 (`national_value`) | 파선 `#9E9E9E` (회색), 원형 마커 ○ | 전국 평균의 연도별 값 |

**데이터 처리:**
- X축 5개 포인트: `publish_year` ∈ {2021, 2022, 2023, 2024, 2025}
- 결측값 (`NaN`): 해당 연도 마커 생략, 선 끊김 표시
- 현재 선택 연도 포인트: 마커 크기 1.5배 강조
- 소제목 "연도별 추이" Inter 11px, #666666

**동적 데이터 연결:**
- 데이터 소스: `indicators_long.csv`에서 `sigungu == 선택지역 AND indicator_name == 선택지표` 필터
- 전국값: `sido == '전국' AND sigungu == '전국'` 또는 `national_value` 열 직접 사용
- 시도값 (선택 사항): `sigungu == sido_name` 행 (시도 평균, 3번째 선으로 추가 가능)

---

## 콘텐츠 영역 (Contents / 인터랙티브 지도)

**Figma 노드 ID**: `1:223`

| 속성 | 값 |
|------|----|
| 너비 | 1312px |
| 높이 | 982px |
| 위치 | x=200, y=0 (사이드바 바로 오른쪽) |
| 배경색 | #D9D9D9 |

**구현 내용:**
- 한국 시군구 경계 코로플레스(Choropleth) 지도
- 지도 데이터 소스: `datasets/shapefile/SGG_2025/smooth_sgg_2025.json` (3.6 MB)
- 색상: 선택된 지표의 `local_value` 기준으로 그라데이션 표현
- 상호작용:
  - 시군구 클릭 → 사이드바 `지자체별지표요약` 업데이트
  - 시도 단위 / 시군구 단위 전환 가능하면 좋음
  - 마우스 오버 → 툴팁 (지역명, 지표값)

---

## 인터랙션 흐름

```
[기준년도 선택]  ──┐
                   ├──→  지도 색상 갱신 (해당 연도 local_value 기준)
[관심지표 선택]  ──┘

[지도 시군구 클릭]  ──→  라벨: {시도명} - {시군구명} 업데이트
                    └──→  요약 텍스트: 해당 지역×지표 데이터 표시
                    └──→  (선택 옵션) 해당 시군구 지도 강조 표시
```

---

## 색상 시스템

| 항목 | 색상값 | 적용 위치 |
|------|--------|-----------|
| 배경 (기본) | `#FFFFFF` | 전체 페이지 |
| 사이드바 | `rgba(217,217,217,0.5)` | 사이드바 배경 |
| 콘텐츠 영역 | `#D9D9D9` | 지도 영역 배경 |
| 텍스트 (기본) | `#1E1E1E` | 라벨, 값 |
| 텍스트 (타이틀/푸터) | `#000000` | 균형발전상황판, Developed by Q |
| 입력 테두리 | `#D9D9D9` | Select/Textarea 테두리 |
| 사이드바 우측 테두리 | `#000000` | 사이드바 경계선 |

---

## 타이포그래피

| 스타일명 | fontFamily | fontSize | fontWeight | lineHeight |
|----------|-----------|----------|------------|------------|
| 타이틀 (균형발전상황판) | Inter | 24px | 400 | 1.21em |
| Body Base (라벨, 값) | Inter | 16px | 400 | 1.4em |
| Single Line/Body Base | Inter | 16px | 400 | 1em |

---

## 기술 구현 제안

### 옵션 A: Plotly Dash (Python)

```
app.layout = html.Div([
    # 사이드바
    html.Div([
        html.H2("균형발전상황판"),
        dcc.Dropdown(id="year-select", options=[2021..2025]),
        dcc.Dropdown(id="indicator-select", options=[...46개 지표...]),
        html.Label(id="region-label"),     # 시도명 - 시군구명
        dcc.Textarea(id="region-summary"), # 지표 요약
    ], style={"width": "200px"}),

    # 콘텐츠 (지도)
    html.Div([
        dcc.Graph(id="choropleth-map"),
    ], style={"flex": 1}),
], style={"display": "flex"})
```

### 옵션 B: Streamlit

```python
col1, col2 = st.columns([1, 6])  # 사이드바 1 : 지도 6
with col1:
    year = st.selectbox("기준년도", [2021, 2022, 2023, 2024, 2025])
    indicator = st.selectbox("관심지표", indicator_names)
    st.write(f"**{sido} - {sigungu}**")
    st.text_area("지표 요약", value=summary_text)
with col2:
    st.plotly_chart(choropleth_fig)
```

### 옵션 C: React + Leaflet (웹 프론트엔드)

- `react-leaflet` 또는 `deck.gl` 로 코로플레스 맵
- `shadcn/ui` Select 컴포넌트로 드롭다운 구현 (Figma 컴포넌트와 시각적으로 유사)
- API 백엔드: FastAPI (Python) → `indicators_long.csv` 서빙

---

## 데이터 연결 매핑

| UI 요소 | 데이터 파일 | 필드 |
|---------|------------|------|
| 기준년도 옵션 | `indicators_long.csv` | `publish_year` unique |
| 관심지표 옵션 | `indicator_catalog.json` | `indicator_name`, `unit` |
| 지도 경계 | `smooth_sgg_2025.json` | `geometry`, `SIGUNGU_NM`, `SIDO_NM` |
| 지도 색상 | `indicators_long.csv` | `local_value` (지역 × 연도 × 지표 필터) |
| 시도명-시군구명 라벨 | 지도 클릭 이벤트 | `SIDO_NM`, `SIGUNGU_NM` |
| 지표 요약 텍스트 | `indicators_long.csv` | 해당 지역 전체 연도 데이터 |

---

## 남은 구현 전 선행 작업

1. **지역명 매핑 테이블** (`region_name_map.json`) 생성
   - `indicators_long.csv`의 `sigungu` ↔ `smooth_sgg_2025.json`의 `SIGUNGU_NM` 일치 확인
   - 불일치 항목 수동 보정

2. **기술 스택 결정** (Plotly Dash / Streamlit / React)

3. **MVP 구현 착수**
