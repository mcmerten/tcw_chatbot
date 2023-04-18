import requests
import re
import urllib.request
from bs4 import BeautifulSoup
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urlparse
import os
import pandas as pd
import openai
import numpy as np
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import UnstructuredFileLoader
from langchain.embeddings import OpenAIEmbeddings
import chromadb
from langchain.vectorstores import Chroma
#from llama_index import download_loader


# Load secrets to access API
load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_TOKEN')
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_TOKEN')

embeddings = OpenAIEmbeddings()

##################
#### SCRAPING ####
##################

# Regex pattern to match a URL
HTTP_URL_PATTERN = r'^http[s]*://.+'

# Define root domain to crawl
domain = "tcw.de"
full_url = "https://tcw.de/"

# Load reader to correctly parse HTML
UnstructuredReader = download_loader("UnstructuredReader", refresh_cache=True)
loader = UnstructuredReader()

# Create a class to parse the HTML and get the hyperlinks
class HyperlinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        # Create a list to store the hyperlinks
        self.hyperlinks = []

    # Override the HTMLParser's handle_starttag method to get the hyperlinks
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        # If the tag is an anchor tag and it has an href attribute, add the href attribute to the list of hyperlinks
        if tag == "a" and "href" in attrs:
            self.hyperlinks.append(attrs["href"])

# Function to get the hyperlinks from a URL
def get_hyperlinks(url):
    # Try to open the URL and read the HTML
    try:
        # Open the URL and read the HTML
        with urllib.request.urlopen(url) as response:
            # If the response is not HTML, return an empty list
            if not response.info().get('Content-Type').startswith("text/html"):
                return []
            
            # Decode the HTML
            html = response.read().decode('utf-8')
    except Exception as e:
        print(e)
        return []

    # Create the HTML Parser and then Parse the HTML to get hyperlinks
    parser = HyperlinkParser()
    parser.feed(html)

    return parser.hyperlinks


# Function to get the hyperlinks from a URL that are within the same domain
def get_domain_hyperlinks(local_domain, url):
    clean_links = []
    for link in set(get_hyperlinks(url)):
        clean_link = None

        # If the link is a URL, check if it is within the same domain
        if re.search(HTTP_URL_PATTERN, link):
            # Parse the URL and check if the domain is the same
            url_obj = urlparse(link)
            if url_obj.netloc == local_domain:
                clean_link = link

        # If the link is not a URL, check if it is a relative link
        else:
            if link.startswith("/"):
                link = link[1:]
            elif link.startswith("#") or link.startswith("mailto:"):
                continue
            clean_link = "https://" + local_domain + "/" + link

        if clean_link is not None:
            if clean_link.endswith("/"):
                clean_link = clean_link[:-1]
            clean_links.append(clean_link)
    # Return the list of hyperlinks that are within the same domain
    return list(set(clean_links))

def is_blacklisted(url):
    blacklist = ["https://tcw.de/uploads",
                 "https://tcw.de/referenzen",
                 "https://tcw.de/fachliteratur",
                 "https://tcw.de/publikationen",
                 "https://tcw.de/news",
                 "https://tcw.de/referrals",
                ]
    for blacklisted_url in blacklist:
        if blacklisted_url in url:
            return True
    return False

def crawl(url):
    # Parse the URL and get the domain
    local_domain = urlparse(url).netloc

    # Create a queue to store the URLs to crawl
    queue = deque([url])

    # Create a set to store the URLs that have already been seen (no duplicates)
    seen = set([url])

    # Create a directory to store the text files
    if not os.path.exists("scraper/raw_html/"):
        os.makedirs("scraper/raw_html/")
    
    if not os.path.exists("scraper/raw_html/"+local_domain+"/"):
           os.makedirs("scraper/raw_html/" + local_domain + "/")
            
    # Create a directory to store the text files
    if not os.path.exists("scraper/html/"):
        os.makedirs("scraper/html/")
    
    if not os.path.exists("scraper/html/"+local_domain+"/"):
           os.makedirs("scraper/html/" + local_domain + "/")
    
    if not os.path.exists("text/"):
            os.mkdir("text/")

    if not os.path.exists("text/"+local_domain+"/"):
            os.mkdir("text/" + local_domain + "/")

    # Create a directory to store the csv files
    if not os.path.exists("processed"):
            os.mkdir("processed")

    # While the queue is not empty, continue crawling
    while queue:
    
    # Get the next URL from the queue
        url = queue.pop()
        print(url) # for debugging and to see the progress
        
        # Define destination
        file_name = local_domain+'/'+url[8:].replace("/", "_") 
        
        # Request content and save in distinct .html file
        urllib.request.urlretrieve(url, 'scraper/raw_html/' + file_name + ".html")
        
        # Get the hyperlinks from the URL and add them to the queue
        for link in get_domain_hyperlinks(local_domain, url):
            if link not in seen and not is_blacklisted(link):
                queue.append(link)
                seen.add(link) 

def clean_html():
    for file in os.listdir("scraper/raw_html/" + domain + "/"):
        with open("scraper/raw_html/" + domain + "/" + file, "r", encoding="UTF-8") as f:
            # Get the text from the URL using BeautifulSoup
                soup = BeautifulSoup(f, "html.parser")
                raw_html = str(soup.find("div", class_="content_frame_out"))#.get_text()
                with open("scraper/html/" + domain + "/" + file, "w", encoding="UTF-8") as f_new:
                    f_new.write(raw_html)

def create_vector_db():
    data = []
    for file in os.listdir("scraper/html/" + domain + "/"):
        loader = UnstructuredFileLoader("scraper/html/" + domain + "/" + file, strategy="hi_res", mode="elements")
        data.append(loader.load())

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    texts = []
    for doc in data:
        texts.append(text_splitter.split_documents(doc))
    texts = [text for subtexts in texts for text in subtexts]
    db = Chroma.from_documents(texts, embeddings)

def main():
     crawl(full_url)
     clean_html()
     create_vector_db()

main()