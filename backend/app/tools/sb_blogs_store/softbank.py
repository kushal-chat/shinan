import requests
from bs4 import BeautifulSoup
import pdfkit
import os

BASE_URL = "https://www.softbank.jp/sbnews"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_article_links():
    res = requests.get(BASE_URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    links = []

    print(soup)

    for a in soup.find_all("a", href=True):
        href = a['href']
        if href.startswith("/sbnews/entry/"):
            full_url = "https://www.softbank.jp" + href
            links.append(full_url)

    return list(set(links))  # remove duplicates

def download_article_as_pdf(url):
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    title = soup.title.text.strip().replace(" ", "_").replace("/", "_")
    html_path = f"/tmp/{title}.html"
    pdf_path = f"{title}.pdf"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    pdfkit.from_file(html_path, pdf_path)
    os.remove(html_path)
    print(f"Saved: {pdf_path}")

if __name__ == "__main__":
    links = get_article_links()
    print(links)
    for link in links:
        try:
            download_article_as_pdf(link)
        except Exception as e:
            print(f"Error downloading {link}: {e}")
