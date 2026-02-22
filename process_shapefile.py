import os
import pandas as pd
import geopandas as gpd
import topojson as tp

print("1. Excel 지역 코드 매핑 로딩 중...")
excel_path = 'datasets/shapefile/센서스 공간정보 지역 코드.xlsx'
df_codes = pd.read_excel(excel_path, header=1, dtype=str)

df_sgg = df_codes[['시도코드', '시도명칭', '시군구코드', '시군구명칭']].drop_duplicates().copy()
df_sgg['시군구코드_3자리'] = df_sgg['시군구코드'].str.zfill(3)
df_sgg['SIGUNGU_CD'] = df_sgg['시도코드'] + df_sgg['시군구코드_3자리']

def get_target_nm(row):
    nm = row['시군구명칭'].strip()
    sido = row['시도명칭']
    # 도/특별자치도 산하의 시 소속 비자치구 (예: '수원시 장안구' -> '수원시')
    # 화성시, 남양주시 등은 공백이 없어 그대로 리턴됨
    if ('도' in sido or '특별자치도' in sido) and ('시 ' in nm and nm.endswith('구')):
        return nm.split(' ')[0]
    return nm

df_sgg['TARGET_NM'] = df_sgg.apply(get_target_nm, axis=1)

print("2. 원본 Shapefile 로딩 중...")
shp_path = 'datasets/shapefile/BND_SIGUNGU_PG/BND_SIGUNGU_PG.shp'
gdf = gpd.read_file(shp_path)
print(f" -> 로딩 완료 (총 {len(gdf)}개 행). 좌표계(CRS): {gdf.crs}")

print("3. 데이터 병합(Join) 및 전처리...")
gdf_merged = gdf.merge(df_sgg[['SIGUNGU_CD', '시도명칭', 'TARGET_NM']], on='SIGUNGU_CD', how='left')

missing_mask = gdf_merged['TARGET_NM'].isna()
if missing_mask.any():
    print(f" -> 경고: 엑셀 매핑이 없는 {missing_mask.sum()}개 행에 대해 원본 데이터 유지")
    gdf_merged.loc[missing_mask, 'TARGET_NM'] = gdf_merged.loc[missing_mask, 'SIGUNGU_NM']
    gdf_merged.loc[missing_mask, '시도명칭'] = '기타'

print("4. 하위 '구' 단위 12개 시에 대한 병합 (Dissolve) 수행 중...")
dissolved_gdf = gdf_merged.dissolve(by=['시도명칭', 'TARGET_NM'], as_index=False)
dissolved_gdf = dissolved_gdf[['시도명칭', 'TARGET_NM', 'SIGUNGU_CD', 'geometry']]
dissolved_gdf.rename(columns={'TARGET_NM': 'SIGUNGU_NM', '시도명칭': 'SIDO_NM'}, inplace=True)
print(f" -> 결과 병합 완료 (총 {len(dissolved_gdf)}개 시군구 폴리곤 완성)")

out_dir = 'datasets/shapefile/SGG_2025'
os.makedirs(out_dir, exist_ok=True)

out_file1 = os.path.join(out_dir, 'sgg_20250630.json')
print(f"5. 원본 해상도 병합 GeoJSON 저장: {out_file1}")
dissolved_gdf.to_file(out_file1, driver='GeoJSON')
size_mb = os.path.getsize(out_file1) / (1024*1024)
print(f" -> 저장 완료 (크기: {size_mb:.2f} MB)")

print("\n6. Topology-preserving Smoothing (단순화) 적용 중...")
tolerance = 5000  # 5km (for projected CRS like EPSG:5179 in meters)
if dissolved_gdf.crs and dissolved_gdf.crs.is_geographic:
    # 5km in degrees (approx)
    tolerance = 5000 / 111000.0
    print(f" -> 지리(경위도) 좌표계 감지. 허용오차(Tolerance): {tolerance:.5f} degree 적용")
else:
    print(f" -> 투영(평면) 좌표계 감지. 허용오차(Tolerance): {tolerance} meters 적용")

# topojson 라이브러리로 빈틈/겹침 없는 위상 보정 스무딩 진행
topo = tp.Topology(dissolved_gdf, prequantize=False)
simplified_topo = topo.toposimplify(tolerance)
smooth_gdf = simplified_topo.to_gdf()

# CRS 속성 복구
if smooth_gdf.crs is None:
    smooth_gdf.set_crs(dissolved_gdf.crs, inplace=True)

out_file2 = os.path.join(out_dir, 'smooth_sgg_2025.json')
print(f"7. 스무딩 완료된 GeoJSON 저장: {out_file2}")
smooth_gdf.to_file(out_file2, driver='GeoJSON')
size2_mb = os.path.getsize(out_file2) / (1024*1024)
print(f" -> 정상 저장 완료! (축소된 파일 크기: {size2_mb:.2f} MB)")
