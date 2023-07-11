from pydantic import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # Secrets
    PAPERCUPS_API_KEY = os.getenv("PAPERCUPS_API_KEY")
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Constants
    GPT_MODEL = "gpt-3.5-turbo-0613"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    BASE_URL = os.getenv("PAPERCUPS_BASE_URL", "https://app.papercups.io")

    # Postgres Database
    POSTGRES_HOST = "db-postgresql-fra1-47508-do-user-14280808-0.b.db.ondigitalocean.com"
    POSTGRES_PORT = "25061"
    POSTGRES_NAME = "tcw-connection-pool"
    POSTGRES_USER = "doadmin"
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

    # Pinecone Vector Database
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    PINECONE_INDEX_NAME = "tcw-website-embeddings"
    PINECONE_ENVIRONMENT = "us-west1-gcp-free"

    # AWS S3 Bucket
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_ENDPOINT_URL = "https://fra1.digitaloceanspaces.com"
    AWS_REGION_NAME = "fra1"
    S3_BUCKET = 'tcw-chatbot'


settings = Settings()
