import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import anthropic

def extract_version(driver, url, software_name):

    driver.get(url)
    time.sleep(3)

    html = driver.page_source

    # 取得したHTMLからBeautifulSoupオブフェクトを生成
    # scriptやstyle及びその他タグの除去
    soup = BeautifulSoup(html, "lxml")
    for s in soup(['script', 'style']):
        s.decompose()

    text = ' '.join(soup.stripped_strings)


    client = anthropic.Anthropic(api_key='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')
    message = client.messages.create(
        max_tokens=100,
        system='以下はソフトウェア「' + software_name + '」の配布ページです。安定版の最新バージョンおよび、可能な場合はその提供日をJSON形式で出力してください。ベータ版やプレビュー版は除きます。キーは以下のとおりです。"version","release_date" 不明な場合はnullを格納してください。JSONのみ出力し余計な発言は不要です。',
        model="claude-3-haiku-20240307",
    #    model="claude-3-5-sonnet-latest",
        messages=[
            {"role": "user", "content": text},
            {"role": "assistant", "content": '{\n "version":'}
        ]
    )
    return ('{\n "version":' + message.content[0].text)

targets = [
    ("https://forest.watch.impress.co.jp/library/software/blackjmbdog/", "BlackJumboDog"),
    ("https://github.com/lucasg/Dependencies", "Dependencies"),
    ("https://jmeter.apache.org/download_jmeter.cgi", "Apache JMeter"),
    ("https://sourceforge.net/p/cppcheck/news/", "CppCheck"),
    ("https://forest.watch.impress.co.jp/library/software/crdiskinfo/", "CrystalDiskInfo"),
    ("https://www.gimp.org/downloads/", "GIMP"),
    ("https://marketplace.visualstudio.com/items?itemName=donjayamanne.githistory", "Git History"),
    ("https://www.ffmpeg.org/download.html", "FFmpeg"),
    ("https://github.com/icsharpcode/ILSpy/releases", "ILSpy"),
    ("https://inkscape.org/release/inkscape-1.4/windows/64-bit/msi/?redirected=1", "InkSpace"),
    ("https://a5m2.mmatsubara.com/", "A5:SQL Mk-2"),
    ("https://teratermproject.github.io/", "Tera Term"),
    ("https://www.roto21.net/husen/", "付箋紙21FE"),
    ("https://www.selenium.dev/downloads/", "Selenium for Python"),
    ('https://tortoisesvn.net/downloads.html', "tortoisesvn"),

]

driver = webdriver.Chrome()

results = []

for (url, software_name) in targets:
    version = extract_version(driver, url, software_name).replace('\n','')
    print (software_name)
    print (version)
    results.append('{"softwarename": "' + software_name + '", "versioninfo": ' + version + '}\n')

driver.close()

print ("{\n" + ",".join(results) + "}")