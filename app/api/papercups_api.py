import datetime
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import requests
from pydantic import BaseModel

from app.chatbot import Chatbot
from app.database import DatabaseManager, Conversation
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)
bot = Chatbot()
db_manager = DatabaseManager()


class Papercups:

    def __init__(self, token):
        """
        Initialize Papercups class with a token.
        """
        self.token = token

    @staticmethod
    def init(token):
        """
        Initialize a new Papercups instance.
        """
        return Papercups(token)

    def send_message(self, params):
        """
        Send a message to Papercups.
        """
        if not self.token:
            logger.error("send_message() : Invalid token!")
            raise HTTPException(status_code=400, detail="Invalid token!")

        headers = {'Authorization': f'Bearer {self.token}'}
        result = {
            "conversation_id": params["conversation_id"],
            "body": bot.get_answer(params["body"])
        }

        data_dict = {
            "id": str(uuid.uuid4()),
            "user_id": params["customer_id"],
            "conversation_id": params["conversation_id"],
            "user_msg": params["body"],
            "bot_msg": result["body"],
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        conversation_data = Conversation(**data_dict)
        db_manager.write_to_db(conversation_data)

        requests.post(f"{settings.BASE_URL}/api/v1/messages", headers=headers, json={'message': result})

    def fetch_conversation(self, conversation_id):
        """
        Fetch a conversation from Papercups.
        """
        if not self.token:
            raise HTTPException(status_code=400, detail="Invalid token!")

        headers = {'Authorization': f'Bearer {self.token}'}
        requests.get(f"{settings.BASE_URL}/api/v1/conversations/{conversation_id}", headers=headers)


papercups = Papercups.init(settings.PAPERCUPS_API_KEY)
app = FastAPI()

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Item(BaseModel):
    event: str
    payload: object

@app.get("/")
async def root():
    return {"message": "TCW Chatbot API is online"}

@app.post("/chat")
async def webhook(item: Item):
    """
    Process incoming webhook events.
    """
    if item.event == "webhook:verify":
        logger.info("Papercups webhook verified")
        return item.payload

    elif item.event == "message:created" and item.payload["customer_id"]:
        logger.info(f'New message from {item.payload["customer_id"]}')
        papercups.send_message(item.payload)
        return {'ok': True}

    elif item.event == "message:created" and item.payload["user_id"]:
        logger.info(f'Answer sent to {item.payload["user_id"]}')
        return {'ok': True}

    elif item.event == "converation:created" and item.payload["user_id"]:
        return {'ok': True}

    else:
        raise HTTPException(status_code=400, detail="Invalid event or payload")

