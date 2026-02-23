"""NABIS 균형발전지표 대시보드 — Plotly Dash."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, Patch, State, dcc, html, no_update

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: 데이터 로딩
# ═══════════════════════════════════════════════════════════════════

DATA = Path("datasets/processed")

# 지표 데이터
df = pd.read_csv(DATA / "indicators_long.csv")
df["sido"] = df["sido"].replace({"전라북도": "전북특별자치도"})

# 군위군: 2023년 경상북도 → 대구광역시 편입 (GeoJSON은 최신 기준 대구광역시)
df.loc[df["sigungu"] == "군위군", "sido"] = "대구광역시"

# 세종: 시도 레벨 데이터를 시군구 데이터에 병합
sejong = df[(df["sido"] == "세종특별자치시") & (df["region_type"] == "시도")].copy()
sejong["region_type"] = "시군구"
df = pd.concat([df, sejong], ignore_index=True)

# 동명 시군구 대응: sido+sigungu 복합키 (서구, 중구, 동구 등 7종 중복)
df["sido_sigungu"] = df["sido"] + " " + df["sigungu"]

# 지표 카탈로그
with open(DATA / "indicator_catalog.json", encoding="utf-8") as f:
    catalog = json.load(f)

indicator_options = [
    {"label": f"{ind['indicator_no']}. {ind['indicator_name']}", "value": ind["indicator_name"]}
    for ind in catalog
]

# 연도 옵션 (내림차순: 최근 연도가 위에)
years = sorted(df["publish_year"].unique())
year_options = [{"label": str(y), "value": y} for y in reversed(years)]

# GeoJSON (EPSG:4326)
with open(DATA / "geo_sgg_4326.json", encoding="utf-8") as f:
    geojson = json.load(f)

# 시도 외곽선 GeoJSON
with open(DATA / "geo_sido_4326.json", encoding="utf-8") as f:
    geojson_sido = json.load(f)

# ═══════════════════════════════════════════════════════════════════
# SECTION 2: 레이아웃
# ═══════════════════════════════════════════════════════════════════

app = Dash(__name__)
app.title = "균형발전상황판"

SIDEBAR_W = 200

sidebar = html.Div(
    [
        # 타이틀
        html.Div(
            "균형발전상황판",
            style={
                "height": "60px",
                "lineHeight": "60px",
                "textAlign": "center",
                "fontFamily": "Inter, sans-serif",
                "fontSize": "24px",
                "color": "#000",
            },
        ),
        # 컨트롤 영역
        html.Div(
            [
                # 기준년도
                html.Label("기준년도", style={"fontFamily": "Inter, sans-serif", "fontSize": "14px", "color": "#1E1E1E"}),
                dcc.Dropdown(
                    id="year-select",
                    options=year_options,
                    value=years[-1],
                    clearable=False,
                    style={"marginBottom": "8px"},
                ),
                # 관심지표
                html.Label("관심지표", style={"fontFamily": "Inter, sans-serif", "fontSize": "14px", "color": "#1E1E1E"}),
                dcc.Dropdown(
                    id="indicator-select",
                    options=indicator_options,
                    value=indicator_options[0]["value"],
                    clearable=False,
                    style={"marginBottom": "12px"},
                ),
                # 지역명 라벨
                html.Div(
                    id="region-label",
                    children="지도에서 지역을 클릭하세요",
                    style={
                        "fontFamily": "Inter, sans-serif",
                        "fontSize": "14px",
                        "fontWeight": "bold",
                        "color": "#1E1E1E",
                        "padding": "10px 0 4px 0",
                    },
                ),
                # 지표 요약 패널
                html.Div(
                    id="info-panel",
                    style={
                        "border": "1px solid #D9D9D9",
                        "borderRadius": "8px 8px 0 0",
                        "padding": "10px 10px 6px 10px",
                        "backgroundColor": "#FFF",
                        "fontFamily": "Inter, sans-serif",
                        "color": "#1E1E1E",
                        "minHeight": "60px",
                    },
                ),
                # 추이 차트
                html.Div(
                    dcc.Graph(
                        id="sparkline",
                        config={"displayModeBar": False},
                        style={"height": "150px", "width": "100%"},
                    ),
                    style={
                        "border": "1px solid #D9D9D9",
                        "borderTop": "none",
                        "borderRadius": "0 0 8px 8px",
                        "backgroundColor": "#FFF",
                        "padding": "0 4px 4px 4px",
                    },
                ),
            ],
            style={"padding": "0 10px", "display": "flex", "flexDirection": "column", "gap": "4px"},
        ),
        # 푸터
        html.Div(
            "Developed by Q",
            style={
                "position": "absolute",
                "bottom": "0",
                "width": f"{SIDEBAR_W}px",
                "height": "40px",
                "lineHeight": "40px",
                "textAlign": "center",
                "fontFamily": "Inter, sans-serif",
                "fontSize": "12px",
                "color": "#000",
            },
        ),
    ],
    style={
        "width": f"{SIDEBAR_W}px",
        "height": "100vh",
        "backgroundColor": "rgba(217,217,217,0.5)",
        "borderRight": "1px solid #000",
        "position": "relative",
        "flexShrink": 0,
        "overflowY": "auto",
    },
)

content = html.Div(
    dcc.Graph(id="choropleth-map", style={"height": "100%", "width": "100%"}),
    style={"flex": 1, "height": "100vh", "backgroundColor": "#D9D9D9"},
)

app.layout = html.Div(
    [sidebar, content],
    style={"display": "flex", "fontFamily": "Inter, sans-serif"},
)


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: 콜백
# ═══════════════════════════════════════════════════════════════════

# --- Callback A: 코로플레스 지도 갱신 ---

@app.callback(
    Output("choropleth-map", "figure"),
    Input("year-select", "value"),
    Input("indicator-select", "value"),
)
def update_map(year, indicator):
    if not indicator:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="#D9D9D9",
            plot_bgcolor="#D9D9D9",
            margin=dict(l=0, r=0, t=0, b=0),
            annotations=[dict(text="관심지표를 선택하세요", showarrow=False, font=dict(size=18, color="#666"))],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    filtered = df[(df["region_type"] == "시군구") & (df["publish_year"] == year) & (df["indicator_name"] == indicator)]
    merged = filtered[["sido", "sigungu", "sido_sigungu", "local_value", "unit"]].copy()

    fig = px.choropleth_map(
        merged,
        geojson=geojson,
        locations="sido_sigungu",
        featureidkey="properties.csv_sido_sigungu",
        color="local_value",
        color_continuous_scale="YlOrRd",
        custom_data=["sido", "sigungu"],
        map_style="white-bg",
        center={"lat": 36.5, "lon": 127.8},
        zoom=5.8,
        opacity=0.8,
    )
    # 호버 템플릿 직접 지정 (customdata 오염 방지)
    unit = merged["unit"].iloc[0] if len(merged) > 0 else ""
    fig.update_traces(
        hovertemplate="<b>%{customdata[1]}</b> (%{customdata[0]})<br>값: %{z:.2f} " + unit + "<extra></extra>",
        marker_line_color="#ccc",
        marker_line_width=0.5,
    )
    fig.update_layout(
        paper_bgcolor="#D9D9D9",
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(
            text=f"{indicator} ({unit})",
            font=dict(size=16, color="#333", family="Inter, sans-serif"),
            x=0.5,
            xanchor="center",
            y=0.98,
        ),
        coloraxis_colorbar=dict(
            title=dict(text=unit),
            len=0.6,
            thickness=12,
            x=0.98,
        ),
        map_layers=[
            dict(
                sourcetype="geojson",
                source=geojson_sido,
                type="line",
                color="#888",
                line=dict(width=1),
            ),
        ],
        uirevision="constant",
    )
    return fig


# --- Callback: 시도 강조 (호버) ---

# 시도별 GeoJSON 캐시 (앱 로딩 시 1회 생성)
_sido_geojson_cache = {}
for _f in geojson_sido["features"]:
    _name = _f["properties"].get("SIDO_NM")
    if _name:
        _sido_geojson_cache[_name] = {"type": "FeatureCollection", "features": [_f]}


@app.callback(
    Output("choropleth-map", "figure", allow_duplicate=True),
    Input("choropleth-map", "hoverData"),
    prevent_initial_call=True,
)
def highlight_sido_on_hover(hover_data):
    patched = Patch()
    base_layer = dict(
        sourcetype="geojson",
        source=geojson_sido,
        type="line",
        color="#888",
        line=dict(width=1),
    )
    if not hover_data:
        patched["layout"]["map"]["layers"] = [base_layer]
        return patched

    customdata = hover_data.get("points", [{}])[0].get("customdata")
    if not customdata or len(customdata) < 2:
        patched["layout"]["map"]["layers"] = [base_layer]
        return patched

    hovered_sido = customdata[0]
    highlight_geojson = _sido_geojson_cache.get(hovered_sido)
    if highlight_geojson:
        patched["layout"]["map"]["layers"] = [
            base_layer,
            dict(
                sourcetype="geojson",
                source=highlight_geojson,
                type="line",
                color="#1565C0",
                line=dict(width=2.5),
            ),
        ]
    else:
        patched["layout"]["map"]["layers"] = [base_layer]
    return patched


# --- Callback B: 사이드바 갱신 (지도 클릭) ---

@app.callback(
    Output("region-label", "children"),
    Output("info-panel", "children"),
    Output("sparkline", "figure"),
    Input("choropleth-map", "clickData"),
    State("year-select", "value"),
    State("indicator-select", "value"),
)
def update_sidebar(click_data, year, indicator):
    empty_fig = go.Figure()
    empty_fig.update_layout(
        margin=dict(l=8, r=8, t=20, b=8),
        height=150,
        paper_bgcolor="#FFF",
        plot_bgcolor="#FFF",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    if not click_data or not indicator:
        return "지도에서 지역을 클릭하세요", html.Div("", style={"minHeight": "60px"}), empty_fig

    point = click_data["points"][0]
    customdata = point.get("customdata")
    if not customdata or len(customdata) < 2:
        return no_update, no_update, no_update

    sido = customdata[0]
    sigungu = customdata[1]

    # 지역명 라벨
    if sido == sigungu:
        label = sido
    else:
        label = f"{sido} - {sigungu}"

    # 텍스트 요약
    row = df[
        (df["region_type"] == "시군구")
        & (df["sido"] == sido)
        & (df["sigungu"] == sigungu)
        & (df["publish_year"] == year)
        & (df["indicator_name"] == indicator)
    ]
    if len(row) > 0:
        r = row.iloc[0]
        local_v = r["local_value"]
        national_v = r["national_value"]
        local_str = f"{local_v:.2f}" if pd.notna(local_v) else "—"
        national_str = f"{national_v:.2f}" if pd.notna(national_v) else "—"
        ref_year = str(r["reference_year"]).rstrip("년") if pd.notna(r["reference_year"]) and r["reference_year"] != "-" else "—"
        unit_text = r["unit"]

        # 시도 값 조회
        sido_row = df[
            (df["region_type"] == "시도")
            & (df["sido"] == sido)
            & (df["publish_year"] == year)
            & (df["indicator_name"] == indicator)
        ]
        if len(sido_row) > 0:
            sido_v = sido_row.iloc[0]["local_value"]
            sido_str = f"{sido_v:.2f}" if pd.notna(sido_v) else "—"
        else:
            sido_str = "—"

        val_row_style = {"display": "flex", "justifyContent": "space-between", "padding": "2px 0"}
        val_label_style = {"color": "#666", "fontSize": "12px"}
        val_num_style = {"fontWeight": "bold", "fontSize": "13px", "color": "#1E1E1E"}

        summary = html.Div([
            html.Div(
                f"{r['indicator_name']} ({unit_text})",
                style={"fontSize": "12px", "fontWeight": "600", "color": "#333", "marginBottom": "8px",
                        "borderBottom": "1px solid #eee", "paddingBottom": "6px"},
            ),
            html.Div([
                html.Span("지자체", style=val_label_style),
                html.Span(f"{local_str} {unit_text}", style={**val_num_style, "color": "#2196F3"}),
            ], style=val_row_style),
            html.Div([
                html.Span("시도", style=val_label_style),
                html.Span(f"{sido_str} {unit_text}", style={**val_num_style, "color": "#FF9800"}),
            ], style=val_row_style),
            html.Div([
                html.Span("전국", style=val_label_style),
                html.Span(f"{national_str} {unit_text}", style={**val_num_style, "color": "#9E9E9E"}),
            ], style=val_row_style),
            html.Div([
                html.Span("기준", style=val_label_style),
                html.Span(ref_year, style={"fontSize": "12px", "color": "#999"}),
            ], style={**val_row_style, "marginTop": "4px"}),
        ])
    else:
        summary = html.Div("데이터 없음", style={"color": "#999", "fontSize": "12px", "textAlign": "center", "padding": "16px 0"})

    # 추이 차트
    trend = df[
        (df["region_type"] == "시군구")
        & (df["sido"] == sido)
        & (df["sigungu"] == sigungu)
        & (df["indicator_name"] == indicator)
    ].sort_values("publish_year")

    # 시도 추이
    sido_trend = df[
        (df["region_type"] == "시도")
        & (df["sido"] == sido)
        & (df["indicator_name"] == indicator)
    ].sort_values("publish_year")

    fig = go.Figure()

    # 지자체값 (파란 실선)
    local_sizes = [10 if y == year else 7 for y in trend["publish_year"]]
    fig.add_trace(go.Scatter(
        x=trend["publish_year"],
        y=trend["local_value"],
        mode="lines+markers",
        name="지자체",
        line=dict(color="#2196F3", width=2),
        marker=dict(size=local_sizes, color="#2196F3"),
        connectgaps=False,
    ))

    # 시도값 (주황 점선)
    sido_sizes = [10 if y == year else 7 for y in sido_trend["publish_year"]]
    fig.add_trace(go.Scatter(
        x=sido_trend["publish_year"],
        y=sido_trend["local_value"],
        mode="lines+markers",
        name="시도",
        line=dict(color="#FF9800", width=2, dash="dot"),
        marker=dict(size=sido_sizes, color="#FF9800", symbol="diamond"),
        connectgaps=False,
    ))

    # 전국값 (회색 파선)
    nat_sizes = [10 if y == year else 7 for y in trend["publish_year"]]
    fig.add_trace(go.Scatter(
        x=trend["publish_year"],
        y=trend["national_value"],
        mode="lines+markers",
        name="전국",
        line=dict(color="#9E9E9E", width=2, dash="dash"),
        marker=dict(size=nat_sizes, color="#9E9E9E", symbol="circle-open"),
        connectgaps=False,
    ))

    fig.update_layout(
        title=dict(text="연도별 추이", font=dict(size=11, color="#666"), x=0.02, y=0.95),
        height=150,
        margin=dict(l=30, r=8, t=22, b=10),
        paper_bgcolor="#FFF",
        plot_bgcolor="#FFF",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.02,
            xanchor="center",
            x=0.5,
            font=dict(size=9, color="#666"),
            itemsizing="constant",
            itemwidth=30,
        ),
        xaxis=dict(
            tickmode="array",
            tickvals=years,
            ticktext=[str(y)[-2:] for y in years],
            tickfont=dict(size=10),
            gridcolor="rgba(0,0,0,0.05)",
        ),
        yaxis=dict(
            tickfont=dict(size=10),
            gridcolor="rgba(0,0,0,0.1)",
        ),
    )

    return label, summary, fig


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: 실행
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
