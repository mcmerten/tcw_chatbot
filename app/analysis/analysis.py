import json
import openai
import datetime
from pydantic import BaseModel, Field
from typing import Optional
from app.database import DatabaseManager, Conversation, Summary
from app.config import settings
from app.core.logger import get_logger

###
from langchain.chat_models import ChatOpenAI
from langchain.chains import create_extraction_chain_pydantic
###


class Lead(BaseModel):
    """Identifying information about a lead."""

    name: Optional[str] = Field(None, description="The person's name")
    email: Optional[str] = Field(None, description="The person's email address")
    phone: Optional[str] = Field(None, description="The person's phone number")
    company: Optional[str] = Field(None, description="The company the person is working for")
    company_size: Optional[str] = Field(None, description="The size of the company")
    role: Optional[str] = Field(None, description="The position / role the person is working in for the company")
    interest: Optional[str] = Field(None, description="The intent of the person and what the person is interested in")
    pain: Optional[str] = Field(None, description="The pain point the person is trying to solve")
    budget: Optional[str] = Field(None, description="The budget which is available for the person")
    additional_info: Optional[str] = Field(None, description="Additional information from the user that might be relevant")


logger = get_logger(__name__)

openai.api_key = settings.OPENAI_API_KEY

db_manager = DatabaseManager()
db_session = db_manager.create_session()


def list_conversations(session, all_conversations=False):
    if all_conversations:
        conversations = session.query(Conversation.conversation_id, Conversation.user_id).distinct().all()
        return conversations
    else:

        conversations = session.query(Conversation.conversation_id, Conversation.user_id).distinct().all()
    return conversations


def fetch_conversation(session, conversation_id):

    # check if conversation_id is in the list returned by list_conversations(db_session), throw exception if not
    if conversation_id not in [conversation[0] for conversation in list_conversations(db_session)]:
        print("Conversation ID not found!")

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
    content_dict = {k: None if v == "None" else v for k, v in content_dict.items()}

    return content_dict


def extraction(conversation):
    llm = ChatOpenAI(temperature=0, model="gpt-4-0613")
    chain = create_extraction_chain_pydantic(pydantic_schema=Lead, llm=llm)
    result = chain.run(conversation['conversation_str'])
    result_dict = result[0].dict()
    print(result_dict)
    metadata = {'conversation_id': conversation['conversation_id'],
                'user_id': conversation['user_id'],
                'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    summary = Summary(**(metadata | result[0].dict()))
    return summary


if __name__ == "__main__":
    for convo in list_conversations(db_session, all_conversations=True):
        fetched_conversation = fetch_conversation(db_session, convo[0])
        gpt_response = extraction(fetched_conversation)
        db_manager.write_to_db(gpt_response)
