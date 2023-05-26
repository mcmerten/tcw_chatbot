import requests
import uvicorn
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import Chatbot
from dotenv import load_dotenv

load_dotenv()

### Papercups
BASE_URL = os.getenv("PAPERCUPS_BASE_URL", "https://app.papercups.io")

# Initialize chatbot
bot = Chatbot()

class Papercups:

    def __init__(self, token):
        self.token = token

    @staticmethod
    def init(token):
        return Papercups(token)

    def send_message(self, params):
        if not self.token:
            raise HTTPException(status_code=400, detail="Invalid token!")
        print(f'Message received:', params["body"])
        headers = {'Authorization': f'Bearer {self.token}'}

        result = {"conversation_id" : params["conversation_id"], "body" : bot.get_answer(params["body"])}
        # send post request
        requests.post(f"{BASE_URL}/api/v1/messages", headers=headers, json={'message': result})
        print("Response sent to Papercups")

    def fetch_conversation(self, conversationId):
        if not self.token:
            raise HTTPException(status_code=400, detail="Invalid token!")
        headers = {'Authorization': f'Bearer {self.token}'}
        # send get request
        requests.get(f"{BASE_URL}/api/v1/conversations/{conversationId}", headers=headers)

papercups = Papercups.init(os.getenv("PAPERCUPS_API_TOKEN"))

### FastAPI
# Create a FastAPI instance
app = FastAPI()
origins = [
    "http://localhost:3000",  # React app connect from here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model to handle request body
class UserMessage(BaseModel):
    message: str

class Item(BaseModel):
    event: str
    payload: object

@app.post("/chat")
async def webhook(item: Item):
    if item.event == "webhook:verify":
        # respond with random string in the payload
        return item.payload
    elif item.event == "message:created" and item.payload["customer_id"]:
        papercups.send_message(item.payload)
        return {'ok': True}
    elif item.event == "message:created" and item.payload["user_id"]:
        print("Response received from Papercups")
        return {'ok': True}
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid event or payload",
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)