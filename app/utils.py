from sqlalchemy import Column, String, DateTime, create_engine, exc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, declarative_base
import logging
from dotenv import load_dotenv
import os


# Setting up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

load_dotenv()

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(String, primary_key=True)
    user_id = Column(String)
    conversation_id = Column(String)
    user_msg = Column(String)
    bot_msg = Column(String)
    created_at = Column(DateTime)

class Summary(Base):
    __tablename__ = 'summary'
    conversation_id = Column(String(64), primary_key=True)
    user_id = Column(String(64))
    created_at = Column(DateTime)
    name = Column(String(128))
    email = Column(String(128))
    phone = Column(String(128))
    company = Column(String(128))
    company_size = Column(String(128))
    role = Column(String(128))
    interest = Column(String(1028))
    pain = Column(String(1028))
    budget = Column(String(1028))
    additional_info = Column(String(1028))

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