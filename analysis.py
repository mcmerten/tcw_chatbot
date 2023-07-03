import os
import json
import openai
from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv


load_dotenv()
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
openai.api_key = os.getenv('OPENAI_API_KEY')

Base = declarative_base()


class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(String, primary_key=True)
    user_id = Column(String)
    conversation_id = Column(String)
    user_msg = Column(String)
    bot_msg = Column(String)
    created_at = Column(DateTime)


ENGINE = create_engine(f'postgresql://doadmin:{POSTGRES_PASSWORD}@db-postgresql-fra1-47508-do-user-14280808-0.b.db.ondigitalocean.com:25060/tcw-dev-db?sslmode=require')
Session = sessionmaker(bind=ENGINE)
session = Session()


def list_conversations(session):
    """
    Fetches all conversations from the database and returns them as a list of Conversation objects.
    """
    conversation_ids = session.query(Conversation.conversation_id).distinct().all()

    return conversation_ids


def fetch_conversation_history(session, conversation_id):
    conversation = session.query(Conversation).filter_by(conversation_id=conversation_id).order_by(Conversation.created_at).all()

    conversation_history = ""
    for msg in conversation:
        if msg.user_msg:
            conversation_history += f"user: {msg.user_msg}\n"
        if msg.bot_msg:
            conversation_history += f"assistant: {msg.bot_msg}\n"

    return conversation_history


def extract_content(data):
    content_string = data["choices"][0]["message"]["content"]
    content_dict = json.loads(content_string)
    content_dict = json.dumps(content_dict, indent=4, sort_keys=False)

    return content_dict


def create_response():
    conversation_history = fetch_conversation_history(session, 'e7e324a9-a93b-4846-9c44-27b03e653375')

    assistant_input = """You are a an assistant for extracting customer lead information from a chat conversation. 
                         You will adhere to ALL of the following rules
                        - You reply with a json file containing the lead information.
                        - The information is always inserted in the same language as the conversation language
                        - If the information covers multiple points, you will separate them with a comma (,)
                        - The field names are always the same
                        - The field names are: 
                            - name: the name of the individual
                            - email: the email of the individual
                            - phone: the phone number of the individual
                            - company: the company the individual works for
                            - company_size: the size of the company the individual works for
                            - role: the occupation of the individual
                            - interest: what kind of service the individual is interested in
                            - pain: what pain points the individual is experiencing
                            - budget: the budget the individual has for the service
                            - additional_info: any additional information the individual has provided
                        - If the user does not provide a field, you will reply with "None"
                        """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": assistant_input},
            {"role": "user", "content": conversation_history},
        ]
    )
    print(extract_content(response))


create_response()
