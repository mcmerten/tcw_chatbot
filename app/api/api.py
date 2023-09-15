import datetime
import uuid
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

import uvicorn
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
    # Initialize Papercups API
    def __init__(self, token):
        self.token = token

    # Define send_message() function to send reply to Papercups
    def send_message(self, params):
        if not self.token:
            logger.error("send_message() : Invalid token!")
            raise HTTPException(status_code=400, detail="Invalid token!")

        headers = {'Authorization': f'Bearer {self.token}'}
        result = {
            "conversation_id": params["conversation_id"],
            "body": bot.chat(params["body"])
        }
        # Data to be written to database
        data_dict = {
            "id": str(uuid.uuid4()),
            "user_id": params["customer_id"],
            "conversation_id": params["conversation_id"],
            "user_msg": params["body"],
            "bot_msg": result["body"],
            "created_at": datetime.datetime.utcnow()
        }

        # Write data to database
        conversation_data = Conversation(**data_dict)
        db_manager.write_to_db(conversation_data)

        # Send reply to Papercups
        requests.post(f"{settings.BASE_URL}/api/v1/messages", headers=headers, json={'message': result})


papercups = Papercups(settings.PAPERCUPS_API_KEY)
app = FastAPI()

origins = ["http://localhost:3000"]

# Add CORS middleware to allow requests from localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Item class for incoming webhooks
class Item(BaseModel):
    event: str
    payload: object

# Define route for root to test chatbot in browser
@app.get("/")
async def root():
    app_path = os.getenv("APP_PATH", "..")
    return FileResponse(f'{app_path}/static/index.html')

# Define route for incoming webhooks from Papercups
@app.post("/webhooks/message-created")
async def webhook(item: Item):
    # Verify webhook
    if item.event == "webhook:verify":
        logger.info("Papercups webhook verified")
        return item.payload
    # Handle incoming messages from leads
    elif item.event == "message:created" and item.payload["customer_id"]:
        logger.info(f'New message from {item.payload["customer_id"]}')
        papercups.send_message(item.payload)
        return {'ok': True}
    # Check that answer was sent to lead
    elif item.event == "message:created" and item.payload["user_id"]:
        logger.info(f'Answer sent to {item.payload["user_id"]}')
        return {'ok': True}

    elif item.event == "converation:created" and item.payload["user_id"]:
        return {'ok': True}
    # Handle other events
    else:
        raise HTTPException(status_code=400, detail="Invalid event or payload")

if __name__ == "__main__":
    os.environ["APP_PATH"] = "../.."
    uvicorn.run(app, host="0.0.0.0", port=8000)
