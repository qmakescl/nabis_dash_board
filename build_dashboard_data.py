"""
NABIS 균형발전지표 - 대시보드용 데이터 빌더

모든 XLS 파일을 읽어 다음 3종의 파일을 생성한다:

  datasets/processed/
    indicators_long.csv     - 전체 long-format tidy 데이터 (지역×발표년도×지표)
    indicator_catalog.json  - 지표 메타데이터 (순번·구분·부문·지표명·단위)
    region_hierarchy.json   - 시도→시군구 계층 구조

데이터 모델 (indicators_long.csv):
  sido          : 시도명
  sigungu       : 시군구명  (시도 파일이면 sido와 동일)
  region_type   : "시도" | "시군구"
  publish_year  : 발표년도 int (2021~2025)
  indicator_no  : 지표 순번 int (1~46)
  indicator_type: 지표구분 (핵심지표/객관지표)
  category      : 부문
  indicator_name: 지표명
  unit          : 단위
  local_value   : 지자체 측정값 float (결측 → NaN)
  national_value: 전국 측정값 float (결측 → NaN)
  reference_year: 기준년도 문자열  (ex. '2024년', '(2020~2024)')
"""

import os
import json
import xlrd
import pandas as pd

# ── 경로 설정 ──────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR  = os.path.join(BASE_DIR, "datasets", "index2025-claude")
OUTPUT_DIR = os.path.join(BASE_DIR, "datasets", "processed")

# 발표년도 → (지자체값 열, 전국값 열, 기준년도 열)
YEAR_COLS = {
    2025: (7,  8,  9),
    2024: (10, 11, 12),
    2023: (13, 14, 15),
    2022: (16, 17, 18),
    2021: (19, 20, 21),
}

DATA_START_ROW = 6   # XLS에서 데이터가 시작하는 행 번호


def safe_float(val: str) -> float | None:
    """'-' 또는 빈 값은 None, 그 외는 float로 변환."""
    s = str(val).strip()
    if s in ("-", "", "None"):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def parse_xls(path: str) -> list[dict]:
    """XLS 파일 1개를 읽어 레코드 리스트를 반환."""
    try:
        wb = xlrd.open_workbook(path)
    except Exception as e:
        print(f"  [오류] {path}: {e}")
        return []

    ws = wb.sheet_by_index(0)

    records = []
    for row_idx in range(DATA_START_ROW, ws.nrows):
        # 순번 확인 (빈 행 방어)
        raw_no = ws.cell_value(row_idx, 0)
        if raw_no == "" or raw_no is None:
            continue
        try:
            indicator_no = int(float(raw_no))
        except (ValueError, TypeError):
            continue

        sido            = str(ws.cell_value(row_idx, 5)).strip()
        sigungu         = str(ws.cell_value(row_idx, 6)).strip()

        # sido == '전국'인 행은 두 가지 경우:
        #  1) 해당 지표에 시군구 수준 데이터 없음 → 해당 행만 건너뜀
        #  2) 파일 전체가 잘못 다운로드됨 (미추홀구.xls 등) → 전 행 건너뜀 → records=[]
        if sido == "전국":
            continue

        indicator_type  = str(ws.cell_value(row_idx, 1)).strip()
        category        = str(ws.cell_value(row_idx, 2)).strip()
        indicator_name  = str(ws.cell_value(row_idx, 3)).strip()
        unit            = str(ws.cell_value(row_idx, 4)).strip()

        # 시도 파일 vs 시군구 파일 구분
        region_type = "시도" if sido == sigungu else "시군구"

        for pub_year, (c_local, c_nat, c_ref) in YEAR_COLS.items():
            records.append({
                "sido":           sido,
                "sigungu":        sigungu,
                "region_type":    region_type,
                "publish_year":   pub_year,
                "indicator_no":   indicator_no,
                "indicator_type": indicator_type,
                "category":       category,
                "indicator_name": indicator_name,
                "unit":           unit,
                "local_value":    safe_float(ws.cell_value(row_idx, c_local)),
                "national_value": safe_float(ws.cell_value(row_idx, c_nat)),
                "reference_year": str(ws.cell_value(row_idx, c_ref)).strip(),
            })

    return records


def build_region_hierarchy(df: pd.DataFrame) -> dict:
    """시도 → 시군구 계층 구조 딕셔너리 생성."""
    hierarchy = {}
    sigungu_df = df[df["region_type"] == "시군구"][["sido", "sigungu"]].drop_duplicates()
    for sido in df["sido"].unique():
        sgus = sigungu_df[sigungu_df["sido"] == sido]["sigungu"].tolist()
        hierarchy[sido] = sorted(set(sgus))
    return dict(sorted(hierarchy.items()))


def build_indicator_catalog(df: pd.DataFrame) -> list[dict]:
    """지표 메타데이터 목록 생성 (순번 순 정렬)."""
    meta_df = (
        df[["indicator_no", "indicator_type", "category", "indicator_name", "unit"]]
        .drop_duplicates()
        .sort_values("indicator_no")
    )
    return meta_df.to_dict(orient="records")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_records = []
    skipped = []

    sido_dirs = sorted(
        d for d in os.listdir(INPUT_DIR)
        if os.path.isdir(os.path.join(INPUT_DIR, d))
        and not d.startswith("_")
    )

    for sido_name in sido_dirs:
        sido_path = os.path.join(INPUT_DIR, sido_name)
        xls_files = sorted(
            f for f in os.listdir(sido_path)
            if f.endswith(".xls") and not f.startswith(".")
        )
        print(f"[{sido_name}] {len(xls_files)}개 파일 처리 중...")

        for fname in xls_files:
            fpath = os.path.join(sido_path, fname)
            records = parse_xls(fpath)
            if records:
                all_records.extend(records)
            else:
                skipped.append(fpath)

    print(f"\n총 {len(all_records):,}개 레코드 수집 완료")
    if skipped:
        print(f"건너뜀: {len(skipped)}개")
        for p in skipped:
            print(f"  - {os.path.relpath(p, BASE_DIR)}")

    # ── DataFrame 생성 ──────────────────────────────────────────────────────
    df = pd.DataFrame(all_records)

    # 타입 정리
    df["publish_year"]   = df["publish_year"].astype(int)
    df["indicator_no"]   = df["indicator_no"].astype(int)
    df["local_value"]    = pd.to_numeric(df["local_value"],    errors="coerce")
    df["national_value"] = pd.to_numeric(df["national_value"], errors="coerce")

    # 정렬: 시도 → 시군구 → 발표년도 → 지표순번
    df = df.sort_values(
        ["sido", "region_type", "sigungu", "publish_year", "indicator_no"],
        ascending=[True, False, True, True, True],   # 시도 먼저, 시군구 다음
    ).reset_index(drop=True)

    # ── 1. indicators_long.csv ────────────────────────────────────────────
    csv_path = os.path.join(OUTPUT_DIR, "indicators_long.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n저장: {os.path.relpath(csv_path, BASE_DIR)}")
    print(f"  shape: {df.shape[0]:,}행 × {df.shape[1]}열")

    # ── 2. indicator_catalog.json ─────────────────────────────────────────
    catalog = build_indicator_catalog(df)
    catalog_path = os.path.join(OUTPUT_DIR, "indicator_catalog.json")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"저장: {os.path.relpath(catalog_path, BASE_DIR)}")
    print(f"  지표 수: {len(catalog)}개")

    # ── 3. region_hierarchy.json ──────────────────────────────────────────
    hierarchy = build_region_hierarchy(df)
    hier_path = os.path.join(OUTPUT_DIR, "region_hierarchy.json")
    with open(hier_path, "w", encoding="utf-8") as f:
        json.dump(hierarchy, f, ensure_ascii=False, indent=2)
    print(f"저장: {os.path.relpath(hier_path, BASE_DIR)}")
    total_sgg = sum(len(v) for v in hierarchy.values())
    print(f"  시도 {len(hierarchy)}개 / 시군구 {total_sgg}개")

    # ── 간단한 통계 요약 ──────────────────────────────────────────────────
    print("\n── 데이터 요약 ──────────────────────────────")
    print(f"  발표년도: {sorted(df['publish_year'].unique())}")
    print(f"  지역유형: {df.groupby('region_type')['sigungu'].nunique().to_dict()}")
    print(f"  결측률 (local_value): "
          f"{df['local_value'].isna().mean():.1%}")
    print(f"  결측률 (national_value): "
          f"{df['national_value'].isna().mean():.1%}")
    print("─" * 45)
    print("완료.")


if __name__ == "__main__":
    main()
