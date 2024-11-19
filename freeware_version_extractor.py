import time
import datetime 
import json

from selenium import webdriver
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup

import anthropic
from openai import AzureOpenAI
from openai import RateLimitError

doller_to_en = 152

demomode = False

with open('models.json') as f:
    models = json.load(f)

input_tokens = 0
output_tokens = 0

def cached_filename(url: str):
    url = url.removeprefix("http://").removeprefix("https://").replace("/", "-")
    return f"cached/{datetime.datetime.now().strftime('%Y%m%d')}{url}.txt"
    
def cached(url):
    try:
        with open(cached_filename(url),'r', encoding='utf-8') as o:
            return o.read()
    except:
        return None

def save_as_cache(url, text):
    with open(cached_filename(url),'w', encoding='utf-8') as o:
        o.write(text)

def scraping(driver, url):
    try:
        driver.get(url)
    except TimeoutException as e:
        pass

    time.sleep(3)

    html = driver.page_source

    # remove script and style tags
    soup = BeautifulSoup(html, "lxml")
    for s in soup(['script', 'style']):
        s.decompose()

    text = ' '.join(soup.stripped_strings)

    return text

def extract_version(model, software_name, text):
    if demomode:
        return ("0.0", 0, 0)
    
    system_text = \
                f'This is the distribution page for the software"{software_name}".' \
                f'Please output the latest stable version and, if available, its release date in JSON format.' \
                'Exclude beta and preview versions(like "10.0-preview2" ). The keys are as follows: "version", "release_date"."' \
                'Remove prefix like "v" or "ver" for version text."' \
                'Date format is "yyyy/mm/dd".' \
                'If version or release_date are unknown or not included in given text, store null.' \
                'Reply JSON only(Do not include your comment).'

    with open(f'QueryText-{software_name}.txt', 'w', encoding='utf-8') as f:
        f.write(system_text)
        f.write('\n')
        f.write(text)
        f.close()

    useAzure = True

    resMessage = ''
    input_tokens = 0
    output_tokens = 0

    model_name = model['name']
    api_key = model['apikey']
    if not 'gpt' in model_name.lower():
        clude_client = anthropic.Anthropic(api_key=api_key)
        message = clude_client.messages.create(
            max_tokens=1000,
            temperature=0.0,
            system=system_text,
            model=model_name,
            messages=[
                {"role": "user", "content": text},
                {"role": "assistant", "content": '{\n "version":'}
            ]
        )
        resMessage = ('{\n "version":' + message.content[0].text).replace('\n','')
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
    else:
        endpoint = model['endpoint']
        azure_client = AzureOpenAI(
            api_key= api_key,
            api_version="2024-08-01-preview",
            azure_endpoint = endpoint
            )

        retry_count = 1
        wait_sec = 5.0
        while True:
            try:
                response = azure_client.chat.completions.create(
                    model=model_name,
                    max_tokens=1000,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": system_text},
                        {"role": "user", "content": text},
                        {"role": "assistant", "content": '{\n "version":'}
                    ]
                )
                break
            except RateLimitError:
                print("RateLimitError is occured. Retry..")
                time.sleep(wait_sec * retry_count)
                retry_count = retry_count + 1

        resMessage = (response.choices[0].message.content).replace('\n','')
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

    return (
        resMessage,
        input_tokens,
        output_tokens
        )

if __name__ == '__main__':

    with open('targets.json', encoding='utf-8') as f:
        targets = json.load(f)

    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-certificate-errors")

    driver = webdriver.Chrome(options=options)

    texts = []
    results = []

    driver.set_page_load_timeout(20)

    start = time.time()

    print ('Scraping..')
    for target in targets:
        software_name = target['software-name'].removeprefix("#")
#        model_name = 'haiku' if not software_name.startswith('#') else 'sonnet'
        model_name = 'gpt4omini'
        software_name = software_name.removeprefix("#")
        print (f'Scraping: {software_name}')
        url = target['url']
        if not url:
            print (" Skip(url is blank.)")
            continue
        text = cached(url)
        if not text:
            text = scraping(driver, url)
            save_as_cache(url, text)

        texts.append((software_name, text, model_name))

    driver.close()

    total_cost_input = 0
    total_cost_output = 0

    start_extracting = time.time()

    print ('-------------------------')
    print ('Extracting version info by AI..')
    for (software_name, text, model_name) in texts:
        # Select AI Model
        model = models[model_name]

        print (software_name)
        print (model["name"])

        # Extract
        (version, input_token, output_token) = extract_version(model, software_name, text)

        print (version)
        results.append(
            f'{{"softwarename": "{software_name}", "text-len": {len(text)},"versioninfo": {version}}}\n')
        total_cost_input = total_cost_input + (input_token  / 1000000.0 * model['pi']) * doller_to_en
        total_cost_output = total_cost_output + (output_token / 1000000.0 * model['po']) * doller_to_en

    end_time = time.time()

    print ("{\n" + ",".join(results) + "}")

    print (f" {total_cost_input+total_cost_output}(In={total_cost_input} + Out={total_cost_output}) yen ")
    print (f" Elapsed time {end_time - start:.3f}sec ( {end_time - start_extracting:.3f}sec + {start_extracting - start:.3f}sec ) ")
