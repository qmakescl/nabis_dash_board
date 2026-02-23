"""GeoJSON 전처리: EPSG:5179 → EPSG:4326 재투영 + 조인 키 추가.

한 번만 실행하면 된다.
출력:
  - datasets/processed/geo_sgg_4326.json  (시군구 경계)
  - datasets/processed/geo_sido_4326.json (시도 외곽선)
"""

import geopandas as gpd
import json
from pathlib import Path

SRC = Path("datasets/shapefile/SGG_2025/smooth_sgg_2025.json")
DST_SGG = Path("datasets/processed/geo_sgg_4326.json")
DST_SIDO = Path("datasets/processed/geo_sido_4326.json")

# 1. 로딩 + 재투영
gdf = gpd.read_file(SRC)
gdf = gdf.to_crs(epsg=4326)

# 2. csv_sigungu 조인 키 생성 (기본: SIGUNGU_NM 그대로)
gdf["csv_sigungu"] = gdf["SIGUNGU_NM"]

# 세종시 → 세종특별자치시 (CSV에는 시도 레벨 데이터만 존재)
gdf.loc[gdf["SIGUNGU_NM"] == "세종시", "csv_sigungu"] = "세종특별자치시"

# 동명 시군구 대응: sido+sigungu 복합키 (서구, 중구, 동구 등 7종 중복)
gdf["csv_sido_sigungu"] = gdf["SIDO_NM"] + " " + gdf["csv_sigungu"]

# 3. 시도 외곽선: 시군구를 SIDO_NM으로 dissolve
gdf_valid = gdf.copy()
gdf_valid["geometry"] = gdf_valid["geometry"].make_valid()
sido_gdf = gdf_valid.dissolve(by="SIDO_NM").reset_index()
sido_gdf.to_file(DST_SIDO, driver="GeoJSON")

# 4. GeoJSON 저장
gdf.to_file(DST_SGG, driver="GeoJSON")

# 검증
with open(DST_SGG) as f:
    geo = json.load(f)
n = len(geo["features"])
print(f"✓ {DST_SGG} 생성 완료 ({n}개 feature, {DST_SGG.stat().st_size / 1e6:.1f} MB)")
print(f"✓ {DST_SIDO} 생성 완료 ({len(sido_gdf)}개 시도, {DST_SIDO.stat().st_size / 1e6:.1f} MB)")

# 세종 확인
for feat in geo["features"]:
    if feat["properties"]["SIGUNGU_NM"] == "세종시":
        print(f"  세종: csv_sido_sigungu = {feat['properties']['csv_sido_sigungu']}")
        break

# 동명 시군구 확인
from collections import Counter
names = [f["properties"]["csv_sigungu"] for f in geo["features"]]
dups = {k: v for k, v in Counter(names).items() if v > 1}
print(f"  동명 시군구: {len(dups)}종 → 복합키로 해결: {list(dups.keys())}")
