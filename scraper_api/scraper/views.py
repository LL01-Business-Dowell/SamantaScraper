import time
import json
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

@csrf_exempt
def search_google_maps(request):
    if request.method == "POST":
        body = json.loads(request.body)
        query = f"{body['keyword']} in {body['location']}"
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        def stream_results():
            try:
                driver.get("https://www.google.com/maps")
                time.sleep(3)

                search_box = driver.find_element(By.ID, "searchboxinput")
                search_box.send_keys(query)
                search_box.send_keys(Keys.RETURN)
                time.sleep(5)

                place_links = set()
                results_container = driver.find_element(By.XPATH, '//div[@role="feed"]')

                prev_count = 0
                scroll_attempts = 0

                while True:
                    results = driver.find_elements(By.CSS_SELECTOR, 'a[href*="https://www.google.com/maps/place/"]')

                    for result in results:
                        url = result.get_attribute("href")
                        if url and url not in place_links:
                            place_links.add(url)
                            yield f"{url}\n"

                    driver.execute_script("arguments[0].scrollTop += 1000;", results_container)
                    time.sleep(5) 

                    if len(place_links) == prev_count:
                        scroll_attempts += 1
                        if scroll_attempts >= 5:
                            break
                    else:
                        scroll_attempts = 0

                    prev_count = len(place_links)

            finally:
                driver.quit()

        return StreamingHttpResponse(stream_results(), content_type="text/plain")

    return JsonResponse({"error": "Only POST requests allowed"}, status=400)
