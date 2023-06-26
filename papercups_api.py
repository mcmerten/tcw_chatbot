from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import Chatbot
import requests
import os
import uvicorn

load_dotenv()

BASE_URL = os.getenv("PAPERCUPS_BASE_URL", "https://app.papercups.io")

bot = Chatbot()


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
            raise HTTPException(status_code=400, detail="Invalid token!")

        headers = {'Authorization': f'Bearer {self.token}'}
        result = {
            "conversation_id": params["conversation_id"],
            "body": bot.get_answer(params["body"])
        }

        requests.post(f"{BASE_URL}/api/v1/messages", headers=headers, json={'message': result})

    def fetch_conversation(self, conversation_id):
        """
        Fetch a conversation from Papercups.
        """
        if not self.token:
            raise HTTPException(status_code=400, detail="Invalid token!")

        headers = {'Authorization': f'Bearer {self.token}'}
        requests.get(f"{BASE_URL}/api/v1/conversations/{conversation_id}", headers=headers)


papercups = Papercups.init(os.environ.get("PAPERCUPS_API_KEY"))
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


@app.post("/chat")
async def webhook(item: Item):
    """
    Process incoming webhook events.
    """
    if item.event == "webhook:verify":
        return item.payload

    elif item.event == "message:created" and item.payload["customer_id"]:
        papercups.send_message(item.payload)
        return {'ok': True}

    elif item.event == "message:created" and item.payload["user_id"]:
        return {'ok': True}

    elif item.event == "converation:created" and item.payload["user_id"]:
        return {'ok': True}

    else:
        raise HTTPException(status_code=400, detail="Invalid event or payload")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
