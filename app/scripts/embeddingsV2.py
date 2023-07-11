import os
import boto3
import botocore.config
from bs4 import BeautifulSoup
from uuid import uuid4
import pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import UnstructuredFileLoader
from langchain.embeddings import OpenAIEmbeddings
from app.config import settings
from unstructured.partition.html import partition_html
from unstructured.staging.base import convert_to_dict

# Constants
DOMAIN = "tcw.de"
FULL_URL = "https://tcw.de/"
S3_PREFIX = 'dev/scraper/tcw.de/'
TMP_DIR = 'tmp'
VECTOR_DIMENSION = 1536
BATCH_LIMIT = 100

# Set up s3 client
session = boto3.session.Session()
s3_client = session.client('s3',
                           endpoint_url=settings.AWS_ENDPOINT_URL,
                           config=botocore.config.Config(s3={'addressing_style': 'virtual'}),
                           region_name=settings.AWS_REGION_NAME,
                           aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)


def read_files_from_s3(bucket=settings.S3_BUCKET, prefix=S3_PREFIX, dir_name=TMP_DIR):
    """
    Download files from s3 to local directory
    """
    html_content = []
    try:
        response = s3_client.list_objects(Bucket=bucket, Prefix=prefix)
        if 'Contents' not in response:
            print(f"No objects found in s3://{bucket}/{prefix}")
            return
        for obj in response.get('Contents', []):
            data = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
            entry = {'page_content': data['Body'].read(),
                     'metadata': data['Metadata']}
            html_content.append(entry)
    except Exception as e:
        print(f"Error downloading files from s3: {e}")
    return html_content


def html_preprocessing(html_list):
    """
    Preprocess HTML content
    """
    for html_file in html_list:
        soup = BeautifulSoup(html_file['page_content'], "html.parser")
        html_file['page_content'] = str(soup.find("div", class_="content_frame_out"))
    return html_list


def html_to_text(html_list):
    """
    Convert HTML to Text
    """
    keys = ['type', 'text', 'metadata']
    new_doc_dict = []
    seen = set()

    for html_file in html_list:
        doc = partition_html(text=html_file['page_content'], strategy="hi_res", include_metadata=False)
        doc_dict = convert_to_dict(doc)

        for element in doc_dict:
            element['metadata'] = html_file['metadata']
            element = {k: v for k, v in element.items() if k in keys}
            # remove element if type is not NarrativeText or ListItem
            if element['type'] not in ['NarrativeText', 'ListItem'] and element['text'] not in seen:
                continue
            else:
                seen.add(element['text'])
                new_doc_dict.append(element)

    return new_doc_dict


def create_vector_db(documents, index_name=settings.PINECONE_INDEX_NAME, vector_dimension=VECTOR_DIMENSION, batch_limit=BATCH_LIMIT):
    """
    Create Vector Database
    """
    pinecone.init(environment=settings.PINECONE_ENVIRONMENT, api_key=settings.PINECONE_API_KEY)
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
    for i, record in enumerate(documents):
        metadata = record['metadata']
        record_texts = text_splitter.split_text(record['text'])
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

def main():
    # read files from s3
    html_files = read_files_from_s3()

    # preprocess html content
    processed_html_files = html_preprocessing(html_files)

    # convert html to text
    text_files = html_to_text(processed_html_files)

    # create vector database
    create_vector_db(text_files)


if __name__ == "__main__":
    main()
