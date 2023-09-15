# Import packages
import urllib.parse
import re
import requests
from urllib.parse import urlparse, urlunparse
from collections import deque
from html.parser import HTMLParser
import urllib.request
import boto3
import botocore.session
import datetime
import logging
from app.config import settings

# Constants
HTTP_URL_PATTERN = r'^http[s]*://.+'
DOMAIN = "tcw.de"
FULL_URL = "https://tcw.de/"
URL_BLACKLIST = [
    "https://tcw.de/uploads",
    "https://tcw.de/fachliteratur",
    "https://tcw.de/publikationen",
    "https://tcw.de/impressum",
    "https://tcw.de/news",
]

# Initialize S3 client to store crawled pages
session = boto3.session.Session()
client = session.client(
    's3',
    endpoint_url=settings.AWS_ENDPOINT_URL,
    config=botocore.config.Config(s3={'addressing_style': 'virtual'}),
    region_name=settings.AWS_REGION_NAME,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
)

class HyperlinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hyperlinks = set()

    # Extract hyperlinks from HTML tags
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ["a", "link"] and "href" in attrs:
            self.hyperlinks.add(attrs["href"])

    # Parse the given URL to extract hyperlinks
    def parse(self, url):
        try:
            response = requests.get(url)
            if response.headers.get('content-type') != 'text/html':
                return []
            html = response.text
            self.feed(html)
        except requests.exceptions.RequestException as e:
            logging.error(e)
            return []

        return list(self.hyperlinks)

# Function to get hyperlinks from a given URL
def get_hyperlinks(url):
    try:
        with urllib.request.urlopen(url) as response:
            if response.info().get_content_type() != "text/html":
                return []
            html = response.read().decode('utf-8')
    except Exception as e:
        logging.error(e)
        return []

    parser = HyperlinkParser()
    parser.feed(html)
    return parser.hyperlinks

# Function to get hyperlinks that belong to the same domain as the given URL
def get_domain_hyperlinks(local_domain, url):
    clean_links = set()
    for link in get_hyperlinks(url):
        if re.search(HTTP_URL_PATTERN, link):
            url_obj = urlparse(link)
            netloc = url_obj.netloc.replace('www.', '')
            url_obj = url_obj._replace(netloc=netloc)
            link = urlunparse(url_obj)
            if url_obj.netloc == local_domain:
                clean_links.add(link.rstrip('/'))
        elif link.startswith("/"):
            clean_links.add(f"https://{local_domain}{link}".rstrip('/'))
        elif not (link.startswith("#") or link.startswith("mailto:") or link.startswith("tel:")):
            clean_links.add(f"https://{local_domain}/{link}".rstrip('/'))

    return list(clean_links)

# Check if a URL is in the blacklist
def is_blacklisted(url):
    return any(blacklisted_url in url for blacklisted_url in URL_BLACKLIST)

# Function to write scraped content to an AWS S3 bucket
def write_to_s3(local_domain, filename, html_content, metadata):
    try:
        client.put_object(
            Bucket='tcw-chatbot',
            Key=f'dev/scraper/{local_domain}/{filename}',
            Body=html_content,
            ACL='private',
            Metadata=metadata
        )
    except Exception as e:
        logging.error(e)

# Crawler class for web scraping
class Crawler:
    def __init__(self, start_url):
        self.local_domain = urlparse(start_url).netloc
        self.queue = deque([start_url])
        self.seen = {start_url}

    # Main crawl function
    def crawl(self):
        while self.queue:
            url = self.queue.popleft()
            try:
                response = requests.get(url, timeout=5)  # Added a timeout for the request
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to fetch {url} due to {e}.")
                continue

            if response.headers.get('Content-Type', '').startswith('text/html'):
                metadata = {
                    'Source-url': url,
                    'Content-type': response.headers.get('Content-Type'),
                    'Created-at': datetime.date.today().strftime("%Y-%m-%d")
                }
                logging.info(f"Crawled {url} - ({len(self.queue)} URLs in queue)")
                write_to_s3(self.local_domain, f'{url[8:].replace("/", "_")}.html', response.text, metadata)

            for link in get_domain_hyperlinks(self.local_domain, url):
                if link not in self.seen and not is_blacklisted(link):
                    self.queue.append(link)
                    self.seen.add(link)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    crawler = Crawler(FULL_URL)
    crawler.crawl()