import pandas as pd
import geopandas as gpd

print("Loading data...")

# Load excel region codes
excel_path = 'datasets/shapefile/센서스 공간정보 지역 코드.xlsx'
df_codes = pd.read_excel(excel_path)
print("\n=== Excel Region Codes Sample ===")
print(df_codes.head())
print("Excel Columns:", df_codes.columns)

# Load shapefile
shp_path = 'datasets/shapefile/BND_SIGUNGU_PG/BND_SIGUNGU_PG.shp'
# We just need to read the dbf/attributes for analysis, but reading the whole file is fine
gdf = gpd.read_file(shp_path)
print("\n=== Shapefile DBF Data Sample ===")
print(gdf.drop(columns='geometry').head())
print("Shapefile Columns:", gdf.columns)
