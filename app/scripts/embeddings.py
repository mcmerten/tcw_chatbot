import re
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
from app.core.logger import get_logger

logger = get_logger(__name__)

# Set up S3 client to read HTML files from
session = boto3.session.Session()
s3_client = session.client('s3',
                           endpoint_url=settings.AWS_ENDPOINT_URL,
                           config=botocore.config.Config(s3={'addressing_style': 'virtual'}),
                           region_name=settings.AWS_REGION_NAME,
                           aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

# Read files from S3 bucket
def read_files_from_s3(bucket=settings.S3_BUCKET):
    logger.info("Read files from S3 Bucket into memory")
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

# Preprocess HTML content by reading relevant HTML class
def html_preprocessing(html_list):
    logger.info("Retrieve relevant HTML class")
    for html_file in html_list:
        soup = BeautifulSoup(html_file['page_content'], "html.parser")
        html_file['page_content'] = str(soup.find("div", class_="content_frame_out"))
    return html_list

# Convert HTML to text
def html_to_text(html_list):
    logger.info("Convert HTML to text")
    text_elements = []
    seen = set()

    for html_file in html_list:
        # Extract structured elements from HTML via unstructured package
        partitioned_html = partition_html(text=html_file['page_content'], strategy="hi_res", include_metadata=False)
        html_elements = convert_to_dict(partitioned_html)
        # remove duplicates and only keep relevant elements from extracted elements
        for element in html_elements:
            element['metadata'] = html_file['metadata']
            element = {k: v for k, v in element.items() if k in ['type', 'text', 'metadata']}
            if element['text'] in seen:
                continue
            else:
                seen.add(element['text'])
                text_elements.append(element)

    return text_elements

# Group the elements in the list by metadata and concatenate the text
def group_and_concat_elements(element_list):
    logger.info("Group document elements by metadata")
    grouped_elements = {}
    for element in element_list:
        metadata_tuple = tuple(element['metadata'].items())
        raw_text = f"{element['text']} "
        if metadata_tuple in grouped_elements:
            grouped_elements[metadata_tuple] += raw_text
        else:
            grouped_elements[metadata_tuple] = raw_text
    return grouped_elements

# Create a list of documents from the grouped elements
def create_doc_list(grouped_elements):
    logger.info("Create document list")
    document_list = []
    for metadata_tuple, text in grouped_elements.items():
        new_entry = {'metadata': dict(metadata_tuple), 'text': text}
        document_list.append(new_entry)
    return document_list

# Upload documents to Pinecone
def create_vector_db(documents, index_name=settings.PINECONE_INDEX_NAME, vector_dimension=1536, batch_limit=100):
    logger.info("Create vector database")
    pinecone.init(environment=settings.PINECONE_ENVIRONMENT, api_key=settings.PINECONE_API_KEY)
    embeddings = OpenAIEmbeddings()
    # Define text splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    # Setup Pinecone index
    if index_name not in pinecone.list_indexes():
        pinecone.create_index(
            name=index_name,
            metric='cosine',
            dimension=vector_dimension
        )
    index = pinecone.Index(index_name)
    texts = []
    metadatas = []
    logger.info("Insert documents into vector database")
    # Iterate over documents and insert them into Pinecone step by step
    for i, record in enumerate(documents):
        metadata = record['metadata']
        record_texts = text_splitter.split_text(record['text'])
        record_metadatas = [{"chunk": j, "text": text, **metadata} for j, text in enumerate(record_texts)]
        texts.extend(record_texts)
        metadatas.extend(record_metadatas)
        if len(texts) >= batch_limit:
            # Create ID
            ids = [str(uuid4()) for _ in range(len(texts))]
            embeds = embeddings.embed_documents(texts)
            index.upsert(vectors=zip(ids, embeds, metadatas))
            texts = []
            metadatas = []

    if len(texts) > 0:
        # Create ID
        ids = [str(uuid4()) for _ in range(len(texts))]
        embeds = embeddings.embed_documents(texts)
        index.upsert(vectors=zip(ids, embeds, metadatas))
    logger.info("Finished inserting embeddings to Pinecone")


def main():
    html_files = read_files_from_s3()
    processed_html_files = html_preprocessing(html_files)
    text_files = html_to_text(processed_html_files)
    grouped_elements = group_and_concat_elements(text_files)
    doc_list = create_doc_list(grouped_elements)
    # user needs to confirm upload to Pinecone via console
    if input(f"Upload {len(doc_list)} documents to Pinecone? (y/n)") == "y":
        create_vector_db(doc_list)
    else:
        logger.info("Documents not uploaded to Pinecone")


if __name__ == "__main__":
    main()
