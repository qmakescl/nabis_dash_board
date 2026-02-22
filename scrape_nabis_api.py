import os
import time
import requests
from urllib.parse import urlencode

# SSL 경고 무시 (공공기관 임시 인증서 오류 방지)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def setup_download_directory(base_path, folder_name):
    download_dir = os.path.join(base_path, folder_name)
    os.makedirs(download_dir, exist_ok=True)
    return download_dir

def scrape_nabis_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = setup_download_directory(os.path.join(base_dir, "datasets"), "index2025")
    print(f"다운로드 경로 지정 완료: {dataset_dir}")
    
    session = requests.Session()
    session.verify = False # 인증서 무시
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.nabis.go.kr",
        "Referer": "https://www.nabis.go.kr/totalStatisticsDetailView.do?menucd=168&menuFlag=Y"
    }

    # 1. 시도 리스트 가져오기
    print("시도 목록 가져오는 중...")
    
    # 하드코딩된 시도 리스트 (AJAX 구조상 코드 파싱 오류 대비 명시적 목록 사용)
    sido_list = [
        {"CODE_ID": "11", "CODE_NAME": "서울특별시"},
        {"CODE_ID": "26", "CODE_NAME": "부산광역시"},
        {"CODE_ID": "27", "CODE_NAME": "대구광역시"},
        {"CODE_ID": "28", "CODE_NAME": "인천광역시"},
        {"CODE_ID": "29", "CODE_NAME": "광주광역시"},
        {"CODE_ID": "30", "CODE_NAME": "대전광역시"},
        {"CODE_ID": "31", "CODE_NAME": "울산광역시"},
        {"CODE_ID": "36", "CODE_NAME": "세종특별자치시"},
        {"CODE_ID": "41", "CODE_NAME": "경기도"},
        {"CODE_ID": "51", "CODE_NAME": "강원특별자치도"},
        {"CODE_ID": "43", "CODE_NAME": "충청북도"},
        {"CODE_ID": "44", "CODE_NAME": "충청남도"},
        {"CODE_ID": "52", "CODE_NAME": "전북특별자치도"},
        {"CODE_ID": "46", "CODE_NAME": "전라남도"},
        {"CODE_ID": "47", "CODE_NAME": "경상북도"},
        {"CODE_ID": "48", "CODE_NAME": "경상남도"},
        {"CODE_ID": "50", "CODE_NAME": "제주특별자치도"}
    ]

    for sido in sido_list:
        sido_cd = sido.get("CODE_ID")
        sido_nm = sido.get("CODE_NAME")
        if sido_cd == "00": continue # 전국 제외
        
        print(f"[{sido_nm}] 시도 데이터 처리 중...")
        
        # 핵심객관지표(01) 기준 검색어 파라미터 (총괄)
        export_payload = {
            "menucd": "168",
            "menuFlag": "Y",
            "schStatSidoCd": sido_cd,
            "statSidoNm": sido_nm,
            "schStatSigunguCd": "",
            "totStatGb": "01", # 균형발전지표
            "totStatSclType": "01", # 핵심/객관
            "pageGb": "A",
            "schType": ""
        }
        
        time.sleep(0.1)
        
        # 엑셀 다운로드 (지자체)
        # 확인된 API: /selectStatEcelList.do 혹은 /selectStatAllEcelList.do
        xls_url = "https://www.nabis.go.kr/selectStatEcelList.do"
        xls_res = session.post(xls_url, data=export_payload, headers=headers)
        
        # 만약 용량이 작거나 에러가 나면 All 버전을 폴백으로 시도
        if xls_res.status_code == 200 and len(xls_res.content) < 1000:
            xls_url = "https://www.nabis.go.kr/selectStatAllEcelList.do"
            xls_res = session.post(xls_url, data=export_payload, headers=headers)
        
        if xls_res.status_code == 200 and len(xls_res.content) > 100:
            file_path = os.path.join(dataset_dir, f"NABIS_지표_{sido_nm}.xls")
            with open(file_path, "wb") as f:
                f.write(xls_res.content)
            print(f"[{sido_nm}] 다운로드 완료")
        else:
            print(f"[{sido_nm}] 로드 실패 (HTTP {xls_res.status_code})")
        
        # 하위 시군구 목록 호출
        time.sleep(0.1)
        sigungu_res = session.post("https://www.nabis.go.kr/ajaxStatTotSidoList.do", data={"upCd": sido_cd}, headers=headers)
        
        sigungu_list = []
        try:
            if sigungu_res.status_code == 200:
                s_json = sigungu_res.json()
                if "list" in s_json:
                    sigungu_list = s_json["list"]
        except:
            pass
            
        for sigungu in sigungu_list:
            sg_cd = sigungu.get("CODE_ID")
            sg_nm = sigungu.get("CODE_NAME")
            if not sg_cd or sg_cd == "000": continue # 전역/공통 등 제외
            
            print(f"  └ [{sg_nm}] 데이터 처리 중...")
            
            sg_payload = export_payload.copy()
            sg_payload["schStatSigunguCd"] = sg_cd
            sg_payload["statSigunguNm"] = sg_nm
            
            time.sleep(0.1)
            sg_xls_res = session.post(xls_url, data=sg_payload, headers=headers)
            
            if sg_xls_res.status_code == 200 and len(sg_xls_res.content) > 100:
                # 파일명: SidoName_SigunguName.xls 
                s_path = os.path.join(dataset_dir, f"NABIS_지표_{sido_nm}_{sg_nm}.xls")
                with open(s_path, "wb") as f:
                    f.write(sg_xls_res.content)
                print(f"  └ [{sg_nm}] 다운로드 완료")
            else:
                print(f"  └ [{sg_nm}] 로드 실패")
                
if __name__ == "__main__":
    print("NABIS 데이터수집 시작...")
    scrape_nabis_data()
    print("NABIS 데이터수집 종료")
