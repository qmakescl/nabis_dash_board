import pandas as pd

# Load excel region codes
excel_path = 'datasets/shapefile/센서스 공간정보 지역 코드.xlsx'
# Skip the first row to use the second row as the actual header
df_codes = pd.read_excel(excel_path, header=1)

# Ensure columns are string types to prevent stripping of leading zeros
df_codes = df_codes.astype(str)

print("=== 분석 대상 데이터 컬럼 ===")
print(df_codes.columns)

# 컬럼명 정리 및 17개 시도별로 시/구/군 추출
# 우리는 '시군구명칭' 내에서 띄어쓰기 또는 계층 구조를 통해 '부천시 소사구' 처럼 
# '시' 하위에 '구'가 있는 케이스를 찾아야 합니다.
# 엑셀 데이터의 형태를 파악하기 위해 앞부분 출력
print("\n=== 데이터 형태 샘플 ===")
print(df_codes.head(10))

# 일반적으로 '수원시 영통구' 처럼 시군구명칭에 "시 구"가 모두 포함되어 있거나,
# 다른 컬럼 구조를 통해 식별할 수 있습니다.
# '시군구명칭' 컬럼에 '시'와 '구'가 공백으로 구분되어 들어가는지 확인합니다.
city_with_gu = df_codes[df_codes['시군구명칭'].str.contains(r'.+시\s+.+구$', regex=True, na=False)]

# 유니크한 지역명 추출 (읍면동은 제외하고 시군구 레벨만)
unique_city_gu_pairs = city_with_gu[['시도명칭', '시군구코드', '시군구명칭']].drop_duplicates()

print("\n=== [결과] 하위에 '구'를 포함하는 '시' 목록 ===")
# 결과를 보기 좋게 그룹핑
grouped_result = {}
for index, row in unique_city_gu_pairs.iterrows():
    sido = row['시도명칭']
    city_gu = row['시군구명칭']
    
    # "수원시 영통구" -> city: "수원시", gu: "영통구"
    parts = city_gu.split(' ')
    if len(parts) >= 2:
        city = parts[0]
        gu = ' '.join(parts[1:])
        
        # 광역시/특별시의 '구'(예: 서울특별시 강남구)는 제외. 
        # 도 단위 산하의 '시'에 속한 '구'만 남깁니다.
        if "도" in sido or "특별자치도" in sido:
            key = f"[{sido}] {city}"
            if key not in grouped_result:
                grouped_result[key] = []
            grouped_result[key].append(f"{gu} (코드: {row['시군구코드']})")

for city, gu_list in grouped_result.items():
    print(f"\n{city}:")
    for gu in gu_list:
        print(f"  - {gu}")

print("\n총 파악된 자치구가 아닌 '행정구'를 가진 시의 개수:", len(grouped_result))
