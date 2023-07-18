import boto3
import botocore.config
from bs4 import BeautifulSoup
from uuid import uuid4
import pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from app.config import settings
from unstructured.partition.html import partition_html
from unstructured.staging.base import convert_to_dict
from unstructured.partition.text_type import is_possible_title
from app.core.logger import get_logger


logger = get_logger(__name__)


# Set up s3 client
session = boto3.session.Session()
s3_client = session.client('s3',
                           endpoint_url=settings.AWS_ENDPOINT_URL,
                           config=botocore.config.Config(s3={'addressing_style': 'virtual'}),
                           region_name=settings.AWS_REGION_NAME,
                           aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)


def read_files_from_s3(bucket=settings.S3_BUCKET):
    """
    Read files from s3 to list object
    """
    prefix = 'dev/scraper/tcw.de/'
    html_content = []
    try:
        response = s3_client.list_objects(Bucket=bucket, Prefix=prefix)
        if 'Contents' not in response:
            logger.info(f"No objects found in s3://{bucket}/{prefix}")
            return
        for obj in response.get('Contents', []):
            data = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
            entry = {'page_content': data['Body'].read(),
                     'metadata': data['Metadata']}
            html_content.append(entry)
    except Exception as e:
        logger.error(f"Error downloading files from s3: {e}")
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
    text_elements = []
    seen = set()

    for html_file in html_list:
        partitioned_html = partition_html(text=html_file['page_content'], strategy="hi_res", include_metadata=False)
        html_elements = convert_to_dict(partitioned_html)

        for element in html_elements:
            element['metadata'] = html_file['metadata']
            element = {k: v for k, v in element.items() if k in ['type', 'text', 'metadata']}
            if element['type'] not in ['NarrativeText', 'ListItem'] and element['text'] not in seen and not is_possible_title(element['text']):
                continue
            else:
                seen.add(element['text'])
                text_elements.append(element)

    return text_elements


def create_vector_db(documents, index_name=settings.PINECONE_INDEX_NAME, vector_dimension=1536, batch_limit=100):
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
    html_files = read_files_from_s3()
    processed_html_files = html_preprocessing(html_files)
    text_files = html_to_text(processed_html_files)
    create_vector_db(text_files)


if __name__ == "__main__":
    main()
