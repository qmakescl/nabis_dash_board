"""
NABIS 균형발전지표 - 핵심·객관지표 Excel 다운로더

시도(17개) 및 시군구(약 250개) 별 지표 데이터를 자동으로 다운로드한다.
저장 경로: datasets/index2025-claude/{시도명}/{지역명}.xls
"""

import os
import re
import time
import shutil
from urllib.parse import unquote

os.environ['WDM_LOCAL'] = '1'

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

NABIS_URL = "https://www.nabis.go.kr/totalStatisticsDetailView.do?menucd=168&menuFlag=Y"

# jstree 셀렉터 (컨테이너 ID: #tree_menu)
SIDO_NODES_CSS = "#tree_menu > ul > li > ul > li.jstree-node"
ANCHOR_CSS = "a.jstree-anchor"
EXPAND_BTN_CSS = "a.jstree-ocl"
SIGUNGU_NODES_CSS = "ul.jstree-children > li.jstree-node > a.jstree-anchor"
DOWNLOAD_BTN_XPATH = "//button[contains(text(), '다운로드(지자체)')]"

CLICK_DELAY = 0.1       # 클릭 후 기본 딜레이 (사용자 요구사항)
AJAX_WAIT = 2.0         # AJAX 테이블 갱신 대기
EXPAND_WAIT = 1.5       # 트리 확장 대기
DOWNLOAD_TIMEOUT = 30   # 다운로드 완료 감지 최대 대기 시간(초)


def setup_directories(base_dir):
    """출력 폴더와 임시 다운로드 폴더를 생성하고 경로를 반환한다."""
    output_dir = os.path.join(base_dir, "datasets", "index2025-claude")
    tmp_dir = os.path.join(output_dir, "_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    return output_dir, tmp_dir


def init_driver(tmp_dir):
    """Headless Chrome 드라이버를 초기화한다.

    CDP를 통해 headless 환경에서도 파일 다운로드가 가능하도록 설정한다.
    Chrome 기본 설정(prefs)으로는 headless에서 다운로드가 막히는 경우가 있어
    setDownloadBehavior CDP 명령을 별도로 호출한다.
    """
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_experimental_option("prefs", {
        "download.default_directory": tmp_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    # Headless 환경에서 파일 다운로드 허용 (CDP 명령)
    driver.execute_cdp_cmd("Browser.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": tmp_dir,
    })
    return driver


def clear_tmp(tmp_dir):
    """임시 폴더의 모든 파일을 비운다. (다운로드 후 새 파일 식별 위해)"""
    for fname in os.listdir(tmp_dir):
        fpath = os.path.join(tmp_dir, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)


def wait_for_download(tmp_dir, timeout=DOWNLOAD_TIMEOUT):
    """임시 폴더에 완성된 Excel 파일이 나타날 때까지 대기한다.

    .crdownload 확장자는 Chrome의 다운로드 중 임시 파일이므로 무시한다.
    Returns: 완성된 파일의 전체 경로, 없으면 None
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        files = [
            f for f in os.listdir(tmp_dir)
            if not f.endswith(".crdownload")
            and (f.endswith(".xls") or f.endswith(".xlsx"))
        ]
        if files:
            return os.path.join(tmp_dir, files[0])
        time.sleep(0.5)
    return None


def move_file(src, dest_dir, dest_name):
    """다운로드된 파일을 목적지로 이동하고 이름을 변경한다.

    dest_name에 확장자가 없으면 src의 확장자를 사용한다.
    """
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(src)[1]  # 서버가 내려준 확장자 유지
    dest_path = os.path.join(dest_dir, dest_name + ext)
    shutil.move(src, dest_path)
    return dest_path


def get_anchor_name(anchor):
    """anchor에서 지역명을 반환한다.

    1순위: anchor.text (렌더링된 텍스트)
    2순위: href의 selectGrid 두 번째 인자를 URL 디코딩하여 반환
           href 형식: javascript:selectGrid("코드", "%EC%9D%B4%EB%A6%84");
           → unquote() 필수 (한글이 URL 인코딩되어 있음)
    """
    text = anchor.text.strip()
    if text:
        return text
    href = anchor.get_attribute("href") or ""
    m = re.search(r'selectGrid\("([^"]+)",\s*"([^"]+)"\)', href)
    if m:
        return unquote(m.group(2))
    return ""


def click_download_button(driver, wait, region_label):
    """"다운로드(지자체)" 버튼을 클릭하고 파일 저장 명령이 전달되길 기다린다."""
    try:
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, DOWNLOAD_BTN_XPATH)))
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(CLICK_DELAY)
    except Exception as e:
        print(f"    [경고] 다운로드 버튼 클릭 실패 ({region_label}): {e}")
        return False
    return True


def download_nabis_index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir, tmp_dir = setup_directories(base_dir)
    print(f"저장 경로: {output_dir}")

    driver = init_driver(tmp_dir)
    wait = WebDriverWait(driver, 10)

    try:
        print(f"NABIS 접속 중: {NABIS_URL}")
        driver.get(NABIS_URL)

        # jstree 컨테이너가 렌더링될 때까지 대기 (최대 15초)
        wait_long = WebDriverWait(driver, 15)
        wait_long.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tree_menu")))
        time.sleep(2)  # jstree 데이터 바인딩 완료까지 추가 대기

        # 전국 루트 노드가 닫혀 있을 경우 펼쳐서 시도 목록 노출
        root_expand = driver.find_elements(By.CSS_SELECTOR, "#tree_menu > ul > li > a.jstree-ocl")
        if root_expand:
            root_class = driver.find_element(By.CSS_SELECTOR, "#tree_menu > ul > li").get_attribute("class")
            if "jstree-closed" in root_class:
                driver.execute_script("arguments[0].click();", root_expand[0])
                time.sleep(1)

        sido_nodes = driver.find_elements(By.CSS_SELECTOR, SIDO_NODES_CSS)
        total_sido = len(sido_nodes)

        if total_sido == 0:
            # 폴백: 더 넓은 셀렉터로 재시도
            fallback_css = "#tree_menu ul.jstree-children li.jstree-node"
            all_nodes = driver.find_elements(By.CSS_SELECTOR, fallback_css)
            print(f"[진단] 기본 셀렉터로 0개 감지. 폴백 셀렉터로 {len(all_nodes)}개 발견.")
            print(f"[진단] 페이지 타이틀: {driver.title}")
            print(f"[진단] 현재 URL: {driver.current_url}")
            tree_el = driver.find_elements(By.CSS_SELECTOR, "#tree_menu")
            print(f"[진단] #tree_menu 요소 존재: {len(tree_el) > 0}")
            raise RuntimeError("시도 노드를 찾지 못했습니다. 셀렉터 또는 페이지 로드를 확인하세요.")

        print(f"시도 {total_sido}개 감지됨\n")

        for i in range(total_sido):
            # DOM 갱신 대응: 매 반복마다 재조회
            sido_nodes = driver.find_elements(By.CSS_SELECTOR, SIDO_NODES_CSS)
            if i >= len(sido_nodes):
                break
            sido_node = sido_nodes[i]

            # ── 시도 이름 확인 ──
            anchor = sido_node.find_element(By.CSS_SELECTOR, ANCHOR_CSS)
            sido_name = get_anchor_name(anchor)
            sido_dir = os.path.join(output_dir, sido_name)
            print(f"[{i+1}/{total_sido}] {sido_name}")

            # ── 시도 클릭 → 데이터 로드 ──
            driver.execute_script("arguments[0].click();", anchor)
            time.sleep(CLICK_DELAY)
            time.sleep(AJAX_WAIT)

            # ── 시도 데이터 다운로드 ──
            clear_tmp(tmp_dir)
            if click_download_button(driver, wait, sido_name):
                downloaded = wait_for_download(tmp_dir)
                if downloaded:
                    dest = move_file(downloaded, sido_dir, sido_name)
                    print(f"    저장: {os.path.relpath(dest, base_dir)}")
                else:
                    print(f"    [경고] {sido_name} 다운로드 파일 감지 실패 (timeout)")

            # ── 시군구 트리 확장 및 목록 탐색 ──
            sido_nodes = driver.find_elements(By.CSS_SELECTOR, SIDO_NODES_CSS)
            sido_node = sido_nodes[i]

            node_class = sido_node.get_attribute("class")
            if "jstree-leaf" in node_class:
                # leaf 노드: 시군구 없음 (세종특별자치시 등)
                sigungu_anchors = []
            else:
                # jstree-open이 아니면 expand 클릭
                if "jstree-open" not in node_class:
                    try:
                        expand_btn = sido_node.find_element(By.CSS_SELECTOR, EXPAND_BTN_CSS)
                        driver.execute_script("arguments[0].click();", expand_btn)
                        time.sleep(CLICK_DELAY)
                    except Exception as e:
                        print(f"    [경고] expand 버튼 오류 ({sido_name}): {e}")
                # open 상태이든 방금 expand했든 하위 노드 로딩 대기
                time.sleep(EXPAND_WAIT)
                sido_nodes = driver.find_elements(By.CSS_SELECTOR, SIDO_NODES_CSS)
                sido_node = sido_nodes[i]
                sigungu_anchors = sido_node.find_elements(By.CSS_SELECTOR, SIGUNGU_NODES_CSS)
                print(f"    [진단] 감지된 시군구({len(sigungu_anchors)}개): {[get_anchor_name(a) for a in sigungu_anchors[:5]]}{'...' if len(sigungu_anchors) > 5 else ''}")

            total_sgg = len(sigungu_anchors)
            if total_sgg == 0:
                print(f"    시군구 없음 (단일 시도)")
            else:
                print(f"    시군구 {total_sgg}개 처리 시작")

            for j in range(total_sgg):
                # Stale Element 방지: 매 반복 재조회
                sido_nodes = driver.find_elements(By.CSS_SELECTOR, SIDO_NODES_CSS)
                sido_node = sido_nodes[i]
                sigungu_anchors = sido_node.find_elements(By.CSS_SELECTOR, SIGUNGU_NODES_CSS)
                if j >= len(sigungu_anchors):
                    break
                sgg_anchor = sigungu_anchors[j]
                sgg_name = get_anchor_name(sgg_anchor)
                if not sgg_name:
                    print(f"    └ [{j+1}/{total_sgg}] [경고] 이름 파싱 실패, 건너뜀")
                    continue

                # ── 시군구 클릭 → 데이터 로드 ──
                driver.execute_script("arguments[0].click();", sgg_anchor)
                time.sleep(CLICK_DELAY)
                time.sleep(AJAX_WAIT)

                # ── 시군구 데이터 다운로드 ──
                clear_tmp(tmp_dir)
                if click_download_button(driver, wait, sgg_name):
                    downloaded = wait_for_download(tmp_dir)
                    if downloaded:
                        dest = move_file(downloaded, sido_dir, sgg_name)
                        print(f"    └ [{j+1}/{total_sgg}] {sgg_name} → {os.path.basename(dest)}")
                    else:
                        print(f"    └ [{j+1}/{total_sgg}] [경고] {sgg_name} 다운로드 파일 감지 실패")

            print()  # 시도 간 빈 줄

    except Exception as e:
        print(f"\n[오류] 예상치 못한 예외 발생: {e}")
        raise
    finally:
        driver.quit()

        # 임시 폴더 정리
        if os.path.isdir(tmp_dir) and not os.listdir(tmp_dir):
            os.rmdir(tmp_dir)

        print("\n완료. 다운로드 프로세스가 종료되었습니다.")
        # 결과 파일 수 출력
        total_files = sum(
            len(files)
            for dirpath, _dirs, files in os.walk(output_dir)
            if "_tmp" not in dirpath
        )
        print(f"저장된 파일 수: {total_files}개")


if __name__ == "__main__":
    download_nabis_index()
