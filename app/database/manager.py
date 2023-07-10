import logging
from app.database.models import Base
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from app.config import settings, db_settings

# Setting up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:

    def __init__(self,
                 host=db_settings.host,
                 port=db_settings.port,
                 db_name=db_settings.db_name,
                 user=db_settings.user,
                 password=db_settings.POSTGRES_PASSWORD):

        self.engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{db_name}')

    def create_session(self):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        return session

    def write_to_db(self, obj):
        session = self.create_session()
        try:
            session.merge(obj)
            session.commit()
            logger.info("Data was inserted")
        except exc.SQLAlchemyError as error:
            session.rollback()
            logger.error("Error while executing SQL", error)
        finally:
            session.close()