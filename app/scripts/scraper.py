import re
import requests
from urllib.parse import urlparse
from collections import deque
from html.parser import HTMLParser
import urllib.request
import boto3
import botocore.session
import datetime
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

# S3 client
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
        self.hyperlinks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.hyperlinks.append(attrs["href"])


def get_hyperlinks(url):
    try:
        with urllib.request.urlopen(url) as response:
            if response.info().get_content_type() != "text/html":
                return []
            html = response.read().decode('utf-8')
    except Exception as e:
        print(e)
        return []

    parser = HyperlinkParser()
    parser.feed(html)
    return parser.hyperlinks


def get_domain_hyperlinks(local_domain, url):
    clean_links = []
    for link in set(get_hyperlinks(url)):
        clean_link = None

        if re.search(HTTP_URL_PATTERN, link):
            url_obj = urlparse(link)
            if url_obj.netloc == local_domain:
                clean_link = link
        else:
            if link.startswith("/"):
                link = link[1:]
            elif (
                link.startswith("#")
                or link.startswith("mailto:")
                or link.startswith("tel:")
            ):
                continue
            clean_link = "https://" + local_domain + "/" + link

        if clean_link is not None:
            if clean_link.endswith("/"):
                clean_link = clean_link[:-1]
            clean_links.append(clean_link)

    return list(set(clean_links))


def is_blacklisted(url):
    for blacklisted_url in URL_BLACKLIST:
        if blacklisted_url in url:
            return True
    return False


def write_to_s3(local_domain, filename, html_content, metadata):
    client.put_object(
        Bucket='tcw-chatbot',
        Key=f'dev/scraper/{local_domain}/{filename}',
        Body=html_content,
        ACL='private',
        Metadata=metadata
    )


def crawl(url):
    local_domain = urlparse(url).netloc
    queue = deque([url])
    seen = {url}

    while queue:
        url = queue.pop()
        print(f"{url} ({len(queue)})")
        file_name = f'{url[8:].replace("/", "_")}.html'
        resp = requests.get(url)

        if resp.headers.get('Content-Type').startswith('text/html'):
            metadata = {
                'Source-url': url,
                'Content-type': resp.headers.get('Content-Type'),
                'Created-at': datetime.date.today().strftime("%Y-%m-%d")
            }

            html_content = resp.text
            try:
                write_to_s3(local_domain, file_name, html_content, metadata)
            except Exception as e:
                print(e)
                continue

        for link in get_domain_hyperlinks(local_domain, url):
            if link not in seen and not is_blacklisted(link):
                queue.append(link)
                seen.add(link)


if __name__ == "__main__":
    # Start Crawling
    crawl(FULL_URL)
