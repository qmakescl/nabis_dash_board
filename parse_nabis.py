import requests
from bs4 import BeautifulSoup
import re

url = "https://www.nabis.go.kr/totalStatisticsDetailView.do?menucd=168&menuFlag=Y"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
response = requests.get(url, headers=headers, verify=False)
soup = BeautifulSoup(response.text, "html.parser")

# Find the download buttons or scripts to see how download is triggered
scripts = soup.find_all("script")
for s in scripts:
    if s.string and "다운로드" in s.string or "download" in (s.string or "").lower():
        print("--- SCRIPT FOUND ---")
        lines = s.string.split("\n")
        for line in lines:
            if "download" in line.lower() or "submit" in line.lower() or "href" in line.lower() or "excel" in line.lower():
                print(line.strip())

# Also find onclick attributes of buttons
buttons = soup.find_all("button")
for b in buttons:
    if "다운로드" in b.text:
        print(f"BUTTON: {b.text.strip()}, ONCLICK: {b.get('onclick')}, ID: {b.get('id')}, CLASS: {b.get('class')}")
