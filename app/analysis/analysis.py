import json
import openai
from app.database import DatabaseManager, Conversation, Summary
from app.config import settings
import datetime
from app.core.logger import get_logger

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
    logger.info(f"Data for conversation {conversation['conversation_id']} extracted successfully")

    conversation_summary = extract_content(response)

    metadata = {'conversation_id': conversation['conversation_id'],
                'user_id': conversation['user_id'],
                'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    summary = Summary(**(metadata | conversation_summary))
    return summary


if __name__ == "__main__":
    for convo in list_conversations(db_session, all_conversations=True):
        fetched_conversation = fetch_conversation(db_session, convo[0])
        gpt_response = create_response(fetched_conversation)
       # db_manager.write_to_db(gpt_response)
