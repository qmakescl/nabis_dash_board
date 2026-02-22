import urllib.request
import urllib.parse
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://www.nabis.go.kr/totalStatisticsDetailView.do?menucd=168&menuFlag=Y', headers={'User-Agent': 'Mozilla'})
with urllib.request.urlopen(req, context=ctx) as r:
    html = r.read().decode('utf-8')
    match = re.search(r'(.{0,200}selectStatEcelList\.do.{0,200})', html, re.DOTALL | re.IGNORECASE)
    if match: print("MATCH 1:", match.group(1))
    match2 = re.search(r'(.{0,200}selectStatAllEcelList\.do.{0,200})', html, re.DOTALL | re.IGNORECASE)
    if match2: print("MATCH 2:", match2.group(1))
