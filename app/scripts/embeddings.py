import os
import re
import shutil
import boto3
import botocore.session
import pathlib
from bs4 import BeautifulSoup
from tqdm import tqdm
from uuid import uuid4
import pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import UnstructuredFileLoader
from langchain.embeddings import OpenAIEmbeddings
from app.config import settings, db_settings


# Constants
DOMAIN = "tcw.de"
FULL_URL = "https://tcw.de/"
S3_BUCKET = 'tcw-chatbot'
S3_PREFIX = 'dev/scraper/tcw.de/'
TMP_DIR = 'tmp'
VECTOR_DIMENSION = 1536
BATCH_LIMIT = 100
PINECONE_INDEX_NAME = "tcw-website-embeddings"
PINECONE_ENVIRONMENT = "us-west1-gcp-free"

# Set up s3 client
session = boto3.session.Session()
s3_client = session.client('s3',
                           endpoint_url='https://fra1.digitaloceanspaces.com',
                           config=botocore.config.Config(s3={'addressing_style': 'virtual'}),
                           region_name='fra1',
                           aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

# Create a /tmp directory within the current directory
def create_temp_dir(dir_name=TMP_DIR):
    pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)

# Remove the /tmp directory
def remove_temp_dir(dir_name=TMP_DIR):
    shutil.rmtree(dir_name)

# Download files from s3 to local directory
def download_files_from_s3(bucket=S3_BUCKET, prefix=S3_PREFIX, dir_name=TMP_DIR):
    try:
        response = s3_client.list_objects(Bucket=bucket, Prefix=prefix)
        if 'Contents' not in response:
            print(f"No objects found in s3://{bucket}/{prefix}")
            return
        for file in response['Contents']:
            filename = file['Key'].split(prefix)[1]
            s3_client.download_file(bucket, file['Key'], f'{dir_name}/{filename}')
    except Exception as e:
        print(f"Error downloading files from s3: {e}")

# Add source url to the metadata of elements
def add_source_url(elements):
    for element in elements:
        source_url = "https://" + element.metadata["source"].split("/")[1].replace("_", "/").removesuffix(".html")
        element.metadata["source"] = source_url
    return elements

# Remove html tags from page_content of elements
def remove_html_tags(elements):
    for element in elements:
        element.page_content = re.sub('<[^<]+?>', ' ', element.page_content)
        element.page_content = re.sub(r'<!--.*?-->', '', element.page_content)
        element.page_content = re.sub(r'<!--.*', '', element.page_content)
        element.page_content = re.sub(r'.*-*>', '', element.page_content)
        element.page_content = element.page_content.strip()
    return elements

# Get filtered documents from s3
def get_filtered_documents_from_s3(dir_name=TMP_DIR):
    create_temp_dir(dir_name)
    download_files_from_s3(dir_name=dir_name)
    seen = set()
    relevant_content = []
    for file in os.listdir(dir_name):
        with open(f"{dir_name}/{file}", "r+") as f:
            soup = BeautifulSoup(f, "html.parser")
            text = str(soup.find("div", class_="content_frame_out"))
            f.seek(0)
            f.write(text)
            f.truncate()
        loader = UnstructuredFileLoader(f"{dir_name}/{file}", strategy="hi_res", mode="elements")
        doc = loader.load()
        doc = add_source_url(doc)
        doc = remove_html_tags(doc)
        for element in doc:
            if element.page_content not in seen and (element.metadata["category"] == "NarrativeText" or element.metadata["category"] == "ListItem"):
                seen.add(element.page_content)
                relevant_content.append(element)
    remove_temp_dir(dir_name)
    return relevant_content


# Create vector database
def create_vector_db(documents, index_name=PINECONE_INDEX_NAME, vector_dimension=VECTOR_DIMENSION, batch_limit=BATCH_LIMIT):
    pinecone.init(environment=PINECONE_ENVIRONMENT, api_key=settings.PINECONE_API_KEY)
    embeddings = OpenAIEmbeddings()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=20)

    if index_name not in pinecone.list_indexes():
        pinecone.create_index(
            name=index_name,
            metric='cosine',
            dimension=vector_dimension
        )
    index = pinecone.Index(index_name)
    texts = []
    metadatas = []
    for i, record in enumerate(tqdm(documents)):
        metadata = {
            'source_url': str(record['source_url']),
            'filetype': record['filetype'],
            'category': record['category']
        }
        record_texts = text_splitter.split_text(record['page_content'])
        record_metadatas = [{"chunk": j, "text": text, **metadata} for j, text in enumerate(record_texts)]
        texts.extend(record_texts)
        metadatas.extend(record_metadatas)
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

# Flatten document
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


# Main function
if __name__ == "__main__":
    try:
        cleaned_documents = get_filtered_documents_from_s3()
        final_documents = flatten_document(cleaned_documents)
        create_vector_db(final_documents)
    except Exception as e:
        print(f"An error occurred: {e}")
