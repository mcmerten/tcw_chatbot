from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

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
    industry = Column(String(128))
    role = Column(String(128))
    interest = Column(String(1028))
    pain = Column(String(1028))
    budget = Column(String(1028))
    additional_info = Column(String(1028))