import datetime
import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import sql
import psycopg2
import requests
from pydantic import BaseModel
import uvicorn

from chatbot import Chatbot

load_dotenv()

BASE_URL = os.getenv("PAPERCUPS_BASE_URL", "https://app.papercups.io")

bot = Chatbot()


# Setting up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, host, port, db_name, user, password):
        self.host = host
        self.port = port
        self.db_name = db_name
        self.user = user
        self.password = password

    def write_to_db(self, data_dict):
        try:
            with psycopg2.connect(host=self.host, port=self.port, database=self.db_name, user=self.user, password=self.password) as conn:
                with conn.cursor() as cur:
                    insert = sql.SQL("INSERT INTO conversations ({}) VALUES ({})").format(
                        sql.SQL(',').join(map(sql.Identifier, data_dict.keys())),
                        sql.SQL(',').join(map(sql.Placeholder, data_dict.keys()))
                    )
                    cur.execute(insert, data_dict)
                    conn.commit()

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("Error while executing SQL", error)


db_manager = DatabaseManager(
    host="db-postgresql-fra1-47508-do-user-14280808-0.b.db.ondigitalocean.com",
    port="25060",
    db_name="tcw-dev-db",
    user="doadmin",
    password=os.getenv('POSTGRES_PASSWORD')
)


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
        print(f"token: {self.token}")
        if not self.token:
            print("send_message() : Invalid token!")
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

        db_manager.write_to_db(data_dict)

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
        print("webhook verified")
        return item.payload

    elif item.event == "message:created" and item.payload["customer_id"]:
        print(f'New message from {item.payload["customer_id"]}')
        papercups.send_message(item.payload)
        return {'ok': True}

    elif item.event == "message:created" and item.payload["user_id"]:
        print(f'Answer sent from {item.payload["user_id"]}')
        return {'ok': True}

    elif item.event == "converation:created" and item.payload["user_id"]:
        return {'ok': True}

    else:
        raise HTTPException(status_code=400, detail="Invalid event or payload")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
