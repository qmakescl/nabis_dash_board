import os
os.environ['WDM_LOCAL'] = '1'

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_download_directory(base_path, folder_name):
    """지정된 폴더에 다운로드 디렉토리를 생성하고 절대 경로를 반환합니다."""
    download_dir = os.path.join(base_path, folder_name)
    os.makedirs(download_dir, exist_ok=True)
    return download_dir

def init_driver(download_dir):
    """Selenium Chrome 드라이버를 초기화하고 다운로드 경로를 설정합니다."""
    chrome_options = Options()
    
    # 다운로드 관련 기본 설정 (프롬프트 없이 지정 경로로 바로 다운로드)
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True 
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # 백그라운드 환경 구동을 위한 Headless 및 브라우저 안정성 옵션
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # webdriver_manager를 사용해 로컬 폴더(.wdm)에 ChromeDriver 설치 및 연동
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

def scrape_nabis_data():
    # 1. 작업 공간(workspace) 내의 datasets/index2025 폴더 준비
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = setup_download_directory(os.path.join(base_dir, "datasets"), "index2025")
    print(f"다운로드 경로 지정 완료: {dataset_dir}")
    
    driver = init_driver(dataset_dir)
    wait = WebDriverWait(driver, 10)
    
    try:
        # 2. NABIS 균형발전지표 통계 화면 이동 (기본적으로 핵심.객관지표 선택 됨)
        url = "https://www.nabis.go.kr/totalStatisticsDetailView.do?menucd=168&menuFlag=Y"
        print(f"URL 접속 중: {url}")
        driver.get(url)
        
        # 페이지 스크립트 로드 및 화면 처리를 위해 잠시 대기
        time.sleep(3)
        
        # --- 아래 선택자들은 실제 대상 페이지 HTML 구조에 맞춰 수정이 필요합니다 ---
        # 예시: 좌측 트리의 1 depth 시도(li) 목록 (jstree 구조)
        # 전국(최상위) 하위의 각 시도 리스트
        sido_elements_selector = "#jstree > ul > li > ul > li.jstree-node"
        sido_list = driver.find_elements(By.CSS_SELECTOR, sido_elements_selector)
        
        # '전국' 클릭은 생략하고 시도 단위부터 반복
        for i in range(len(sido_list)):
            # DOM 갱신 대응
            sidos = driver.find_elements(By.CSS_SELECTOR, sido_elements_selector)
            if i >= len(sidos): break
            current_sido = sidos[i]
            
            # --- 3. 시도 명칭 클릭 및 "다운로드(지자체)" 클릭 ---
            sido_name_element = current_sido.find_element(By.CSS_SELECTOR, "a.jstree-anchor")
            sido_name = sido_name_element.text.strip()
            print(f"[{sido_name}] 시도 데이터 처리 중...")
            
            # 시도 클릭으로 데이터 갱신 요청
            # jstree는 a 태그 내부의 텍스트가 클릭 영역
            driver.execute_script("arguments[0].click();", sido_name_element)
            time.sleep(0.1) # Q의 지침
            time.sleep(1.5) # AJAX 통계 테이블 갱신 대기
            
            # "다운로드(지자체)" 버튼 클릭 
            try:
                download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '다운로드(지자체)')]")))
                driver.execute_script("arguments[0].click();", download_btn)
                print(f"[{sido_name}] 다운로드 버튼 클릭됨")
                time.sleep(0.1)
                time.sleep(2) # 파일 시스템 기록 대기
            except Exception as e:
                print(f"[{sido_name}] 다운로드 버튼 처리 에러: {e}")
            
            # --- 4. 시군구 확장을 위한 '+' 버튼 클릭 (있는 경우) ---
            # jstree 구조상 class 속성에 'jstree-closed'가 있으면 하위 항목이 존재하고 닫혀있는 상태임
            parent_class = current_sido.get_attribute("class")
            if "jstree-closed" in parent_class:
                try:
                    plus_button = current_sido.find_element(By.CSS_SELECTOR, "i.jstree-ocl")
                    driver.execute_script("arguments[0].click();", plus_button)
                    time.sleep(0.1)
                    time.sleep(1) # 하위 노드 확장 대기
                except Exception as e:
                    print(f"[{sido_name}] 리스트 열기 실패: {e}")
            
            # 시군구 목록 탐색 (현재 시도 노드가 open 상태이거나 하위 요소들이 렌더링된 상태)
            try:
                # 하위 ul.jstree-children 내부의 li 요소들
                sigungu_elements = current_sido.find_elements(By.CSS_SELECTOR, "ul.jstree-children > li.jstree-node > a.jstree-anchor")
                
                for j in range(len(sigungu_elements)):
                    # 재조회를 통한 Stale Element 제어
                    current_sido = driver.find_elements(By.CSS_SELECTOR, sido_elements_selector)[i]
                    sigungu_elements = current_sido.find_elements(By.CSS_SELECTOR, "ul.jstree-children > li.jstree-node > a.jstree-anchor")
                    
                    if j >= len(sigungu_elements): break
                    sigungu_el = sigungu_elements[j]
                    
                    sigungu_name = sigungu_el.text.strip()
                    print(f"  └ [{sigungu_name}] 데이터 처리 중...")
                    
                    driver.execute_script("arguments[0].click();", sigungu_el)
                    time.sleep(0.1)
                    time.sleep(1.5) # 테이블 갱신 대기
                    
                    try:
                        dl_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '다운로드(지자체)')]")))
                        driver.execute_script("arguments[0].click();", dl_btn)
                        print(f"  └ [{sigungu_name}] 다운로드 완료")
                        time.sleep(0.1)
                        time.sleep(1.5) # 파일 대기
                    except Exception as e:
                        print(f"  └ [{sigungu_name}] 다운로드 중 에러: {e}")
                        
            except Exception as e:
                # 하위 항목 탐색 중 에러 (하위가 없거나 렌더링되지 않은 경우)
                pass
                
    except Exception as e:
        print(f"과정 중 에러 발생: {e}")
    finally:
        driver.quit()
        print("모든 탐색 및 다운로드 과정이 종료되었습니다.")

if __name__ == "__main__":
    scrape_nabis_data()
