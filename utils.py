from sqlalchemy import create_engine, Table, MetaData, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
import logging
from dotenv import load_dotenv
import os

# Setting up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class DatabaseManager:

    host = "db-postgresql-fra1-47508-do-user-14280808-0.b.db.ondigitalocean.com"
    port = "25061"
    db_name = "tcw-connection-pool"
    user = "doadmin"
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

    def __init__(self, host=host, port=port, db_name=db_name, user=user, password=POSTGRES_PASSWORD):
        self.engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{db_name}')

    def create_session(self):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        return session

    def write_to_db(self, table_name, data_dict):
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=self.engine)
        try:
            with self.engine.begin() as connection:
                insert = connection.execute(table.insert(), data_dict)
                if insert.inserted_primary_key is not None:
                    logger.info("Data was inserted")
                else:
                    logger.info("Data was not inserted")

        except SQLAlchemyError as error:
            logger.error("Error while executing SQL", error)


