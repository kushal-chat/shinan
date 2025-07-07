import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Any

search_endpoint = "https://www.softbank.jp/sbnews"

response = requests.get(search_endpoint)
soup = BeautifulSoup(response.text, 'html.parser')
items = soup.select('li.urllist-item.recent-entries-item')

for item in items:
    # Title and URL
    title_tag = item.select_one('a.urllist-title-link')
    title = title_tag.text.strip() if title_tag else 'No title'
    article_url = title_tag['href'] if title_tag else 'No URL'

    print(f"Title: {title}")
    print(f"URL: {article_url}")

# current_response = requests.get(current_point)
# soup = BeautifulSoup(current_response.text, 'html.parser')
# print(soup)