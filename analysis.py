import os
import json
import openai
from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from utils import DatabaseManager
import uuid

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

Base = declarative_base()
db_manager = DatabaseManager()
db_session = db_manager.create_session()

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(String, primary_key=True)
    user_id = Column(String)
    conversation_id = Column(String)
    user_msg = Column(String)
    bot_msg = Column(String)
    created_at = Column(DateTime)


def list_conversations(session):
    # return conversation_ids and user_ids

    conversations = session.query(Conversation.conversation_id, Conversation.user_id).distinct().all()
    return conversations


def fetch_conversation(session, conversation_id):

    # check if conversation_id is in the list returned by list_conversations(db_session), throw exception if not
    #if conversation_id not in list_conversations(db_session)[0]:
    #    print("Conversation ID not found!")

    conversation = session.query(Conversation).filter_by(conversation_id=conversation_id).order_by(Conversation.created_at).all()

    conversation_str = ""
    for msg in conversation:
        if msg.user_msg:
            conversation_str += f"user: {msg.user_msg}\n"
        if msg.bot_msg:
            conversation_str += f"assistant: {msg.bot_msg}\n"

    user_conversation = {
         "user_id": conversation[0].user_id,
         "conversation_id": conversation_id,
         "conversation_str": conversation_str
    }

    return user_conversation


def extract_content(response):
    content_string = response["choices"][0]["message"]["content"]
    content_dict = json.loads(content_string)
    #content_dict = json.dumps(content_dict, indent=4, sort_keys=False)

    return content_dict


def create_response(conversation):

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
            {"role": "user", "content": conversation["conversation_str"]},
        ]
    )

    conversation_summary = extract_content(response)

    metadata = {'id': str(uuid.uuid4()),
                'user_id': conversation['user_id'],
                'conversation_id': conversation['conversation_id']}

    summary = metadata | conversation_summary
    return summary


if __name__ == "__main__":
    fetched_conversation = fetch_conversation(db_session, "4e3af3cd-bb23-458c-8d00-af2d745d991d")
    gpt_response = create_response(fetched_conversation)
    db_manager.write_to_db(table_name="summary", data_dict=gpt_response)


