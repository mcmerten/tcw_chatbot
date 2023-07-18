import json
import openai
import datetime

from app.database import DatabaseManager, Conversation, Summary
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

openai.api_key = settings.OPENAI_API_KEY

db_manager = DatabaseManager()
db_session = db_manager.create_session()


def list_conversations(session, all_conversations=True):
    query = session.query(Conversation.conversation_id,
                          Conversation.user_id).distinct()
    # TODO: implement filter
    if not all_conversations:
        query = query.filter(...)

    return query.all()


def fetch_conversation(session, conversation_id):
    conversations = [c[0] for c in list_conversations(session)]

    if conversation_id not in conversations:
        logger.error("Conversation not found")
        return

    conversation = (session.query(Conversation)
                    .filter(Conversation.conversation_id == conversation_id)
                    .order_by(Conversation.created_at)
                    .all())

    conversation_str = ""

    for msg in conversation:
        if msg.user_msg:
            conversation_str += f"user: {msg.user_msg}\n"

        if msg.bot_msg:
            conversation_str += f"assistant: {msg.bot_msg}\n"

    return {
        "user_id": conversation[0].user_id,
        "conversation_id": conversation_id,
        "conversation_str": conversation_str
    }


def extract_content(response):
    content = json.loads(response["choices"][0]["message"]["content"])
    return {k: v if v != "None" else None for k, v in content.items()}


def create_response(conversation):
    assistant_prompt = """
        - You are an assistant that extracts lead info from conversations. 
        - You ONLY extract information from the user. You DO NOT extract information from the assistant. 
        - If no information is provided, use "None".
        Reply in json format:
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
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": assistant_prompt},
            {"role": "user", "content": conversation["conversation_str"]},
        ]
    )

    logger.info(f"Data extracted for {conversation['conversation_id']}")

    summary = extract_content(response)
    summary['conversation_id'] = conversation['conversation_id']
    summary['user_id'] = conversation['user_id']
    summary['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return Summary(**summary)


if __name__ == "__main__":

    for convo in list_conversations(db_session, all_conversations=True):
        conversation = fetch_conversation(db_session, convo[0])
        response = create_response(conversation)
        db_manager.write_to_db(response)