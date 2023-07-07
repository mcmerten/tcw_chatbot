import os
import re
import shutil
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm
from uuid import uuid4
import pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import UnstructuredFileLoader
from langchain.embeddings import OpenAIEmbeddings
import boto3
import botocore.session


# Load secrets to access API
load_dotenv()

# Environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")

# Constants
DOMAIN = "tcw.de"
FULL_URL = "https://tcw.de/"

session = boto3.session.Session()
client = session.client('s3',
                        endpoint_url='https://fra1.digitaloceanspaces.com',
                        config=botocore.config.Config(s3={'addressing_style': 'virtual'}),
                        region_name='fra1',
                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


def add_source_url(elements):
    for element in elements:
        source_url = "https://" + element.metadata["source"].split("/")[1].replace("_", "/").removesuffix(".html")
        element.metadata["source"] = source_url
    return elements


def remove_html_tags(elements):
    for element in elements:
        element.page_content = re.sub('<[^<]+?>', ' ', element.page_content)
        element.page_content = re.sub(r'<!--.*?-->', '', element.page_content)
        element.page_content = re.sub(r'<!--.*', '', element.page_content)
        element.page_content = re.sub(r'.*-*>', '', element.page_content)
        element.page_content = element.page_content.strip()
    return elements


def remove_duplicates(elements):
    seen = set()
    new_elements = []
    for element in elements:
        if element.page_content not in seen:
            seen.add(element.page_content)
            new_elements.append(element)
    return new_elements


def retrieve_relevant_content():
    seen = set()
    relevant_content = []
    if not os.path.exists("tmp/"):
        os.makedirs("tmp/")

    response = client.list_objects(Bucket='tcw-chatbot')
    for file in response['Contents']:
        print(file['Key'])
        client.download_file('tcw-chatbot',
                             file,
                             f'/tmp/{file}')

    for file in os.listdir(f"scraper/data/{DOMAIN}/"):
        with open("scraper/data/" + DOMAIN + "/" + file, "r", encoding="UTF-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            text = str(soup.find("div", class_="content_frame_out"))
            with open("tmp/" + file, "w", encoding="UTF-8") as f:
                f.write(text)
    for file in os.listdir("tmp/"):
        loader = UnstructuredFileLoader("tmp/" + file, strategy="hi_res", mode="elements")
        document = loader.load()
        document = add_source_url(document)
        document = remove_html_tags(document)
        for element in document:
            if element.page_content not in seen and (element.metadata["category"] == "NarrativeText" or element.metadata["category"] == "ListItem"):
                seen.add(element.page_content)
                relevant_content.append(element)
    shutil.rmtree("tmp/")
    return relevant_content


def flatten_document(document):
    flattened_document = []
    for element in document:
        flattened_document.append({
            "page_content": element.page_content,
            "source_url": element.metadata["source"],
            "filetype": element.metadata["filetype"],
            "category": element.metadata["category"]
        })
    return flattened_document


def create_vector_db(documents):
    pinecone.init(environment="us-west1-gcp-free", api_key=PINECONE_API_KEY)
    embeddings = OpenAIEmbeddings()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    index_name = "tcw-website-embeddings"

    if index_name not in pinecone.list_indexes():
        pinecone.create_index(
            name=index_name,
            metric='cosine',
            dimension=1536
        )
    index = pinecone.Index(index_name)
    batch_limit = 100
    texts = []
    metadatas = []
    for i, record in enumerate(tqdm(documents)):
        # first get metadata fields for this record
        metadata = {
            'source_url': str(record['source_url']),
            'filetype': record['filetype'],
            'category': record['category']
        }
        # now we create chunks from the record text
        record_texts = text_splitter.split_text(record['page_content'])
        # create individual metadata dicts for each chunk
        record_metadatas = [{
            "chunk": j, "text": text, **metadata
        } for j, text in enumerate(record_texts)]
        # append these to current batches
        texts.extend(record_texts)
        metadatas.extend(record_metadatas)
        # if we have reached the batch_limit we can add texts
        if len(texts) >= batch_limit:
            ids = [str(uuid4()) for _ in range(len(texts))]
            embeds = embeddings.embed_documents(texts)
            index.upsert(vectors=zip(ids, embeds, metadatas))
            texts = []
            metadatas = []

    if len(texts) > 0:
        ids = [str(uuid4()) for _ in range(len(texts))]
        embeds = embeddings.embed_documents(texts)
        index.upsert(vectors=zip(ids, embeds, metadatas))


# create a main() method in your program
if __name__ == "__main__":
    cleaned_documents = retrieve_relevant_content()
    final_documents = flatten_document(cleaned_documents)
    create_vector_db(final_documents)
