from pydantic import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()
class Settings(BaseSettings):
    # Environment variables
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    PAPERCUPS_API_KEY = os.getenv("PAPERCUPS_API_KEY")
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Constants
    GPT_MODEL = os.getenv("GPT_MODEL")
    BASE_URL = os.getenv("PAPERCUPS_BASE_URL", "https://app.papercups.io")


class DatabaseSettings(BaseSettings):
    host = "db-postgresql-fra1-47508-do-user-14280808-0.b.db.ondigitalocean.com"
    port = "25061"
    db_name = "tcw-connection-pool"
    user = "doadmin"
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')


settings = Settings()
db_settings = DatabaseSettings()
