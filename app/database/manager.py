from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:

    def __init__(self,
                 host=settings.POSTGRES_HOST,
                 port=settings.POSTGRES_PORT,
                 db_name=settings.POSTGRES_NAME,
                 user=settings.POSTGRES_USER,
                 password=settings.POSTGRES_PASSWORD):

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



