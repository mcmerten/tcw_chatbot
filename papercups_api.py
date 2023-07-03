from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import Chatbot
import requests
import os
import uvicorn
import datetime
import psycopg2
from psycopg2 import sql
import uuid

load_dotenv()
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
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

    @staticmethod
    def write_to_db(user_id, conversation_id, user_msg, bot_msg):
        data_dict = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_msg": user_msg,
            "bot_msg": bot_msg,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            # Establishing the connection
            with psycopg2.connect(host="db-postgresql-fra1-47508-do-user-14280808-0.b.db.ondigitalocean.com",
                                  port="25060",
                                  database="tcw-dev-db",
                                  user="doadmin",
                                  password=POSTGRES_PASSWORD) as conn:
                # Creating a cursor object using the cursor() method
                with conn.cursor() as cur:
                    # Formulating SQL query
                    insert = sql.SQL("INSERT INTO conversations ({}) VALUES ({})").format(
                        sql.SQL(',').join(map(sql.Identifier, data_dict.keys())),
                        sql.SQL(',').join(map(sql.Placeholder, data_dict.keys()))
                    )

                    # Executing the SQL command
                    cur.execute(insert, data_dict)

                    # Commit your changes in the database
                    conn.commit()

        except (Exception, psycopg2.DatabaseError) as error:
            print("Error while executing SQL", error)
        finally:
            if conn is not None:
                conn.close()
                print("Database connection closed.")

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

        self.write_to_db(user_id=params["customer_id"], conversation_id=params["conversation_id"], user_msg=["body"], bot_msg=result["body"])

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
