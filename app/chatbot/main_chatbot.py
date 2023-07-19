import json
import openai
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt

from app.chatbot.retrieval_chatbot import RetrievalChatbot
from app.chatbot.lead_chatbot import LeadChatbot
from app.config import settings
from app.core import logger

logger = logger.get_logger(__name__)

openai.api_key = settings.OPENAI_API_KEY

class Chatbot:
    def __init__(self):
        self.conversation_history = []
        self.add_message("system",
                        """You are TCW-GPT, a helpful assistant helps users on the TCW website. 
                        - You help users to find relevant information and qualify whether or not they are potential customers.
                        - You must use the provided functions.
                        - Your answers should never exceed 150 characters.""")
        self.add_message("assistant", "Hallo, wie kann ich Ihnen weiterhelfen?")
        self.functions = [
            {
                "name": "lead_qualification",
                "description":  """Use this function qualify leads and extract lead information. You must use this function for the first response. Do not use the function more than 3 times.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "User query to the assistant",
                        }
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "website_chat",
                "description": "Use this function to enable the user to chat with the website.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "User query to the assistant",
                        }
                    },
                    "required": ["query"],
                },
            }
        ]

    def lead_qualification(self, query):
        """Use this function qualify leads and extract lead information"""
        chatbot = LeadChatbot(self.conversation_history)
        return chatbot.chat(query)

    def website_chat(self, query):
        """Use this function to enable the user to chat with the website."""
        chatbot = RetrievalChatbot(self.conversation_history)
        return chatbot.chat(query)

    @retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
    def chat_completion_request(self, messages, functions=None, model="gpt-4-0613"):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + openai.api_key,
        }
        json_data = {"model": model, "messages": messages}
        if functions is not None:
            json_data.update({"functions": functions})
        try:
            return requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=json_data,
            )
        except Exception as e:
            logger.error(f"Unable to generate ChatCompletion response: {e}")
            return None

    def call_chatbot_function(self, messages, full_message):
        """Function calling function which executes function calls when the model believes it is necessary.
        Currently extended by adding clauses to this if statement."""
        function_name = full_message["message"]["function_call"]["name"]
        try:
            parsed_output = json.loads(full_message["message"]["function_call"]["arguments"])
        except Exception as e:
            logger.error(f"Error parsing arguments: {e}")
            return None

        if function_name == "website_chat":
            logger.info("Calling website_chat() function")
            results = self.website_chat(parsed_output["query"])
        elif function_name == "lead_qualification":
            logger.info("Calling lead_qualification() function")
            results = self.lead_qualification(parsed_output["query"])
        else:
            raise Exception("Function does not exist and cannot be called")

        messages.append({
            "role": "function",
            "name": function_name,
            "content": str(results),
        })
        return str(results)
        # Necessary?
        #try:
        #    response = self.chat_completion_request(messages)
        #    return response.json()
        #except Exception as e:
        #    print(type(e))
        #    raise Exception("Function chat request failed")

    def chat_completion_with_function_execution(self, messages):
        """This function makes a ChatCompletion API call with the option of adding functions"""
        functions = self.functions
        response = self.chat_completion_request(messages, functions)
        full_message = response.json()["choices"][0]
        if full_message["finish_reason"] == "function_call":
            logger.info(f"Function generation requested")
            return self.call_chatbot_function(messages, full_message)
        else:
            logger.info(f"Function not required, responding to user")
            return response.json()

    def add_message(self, role, content):
        message = {"role": role, "content": content}
        self.conversation_history.append(message)

    def display_conversation(self, detailed=False):
        for message in self.conversation_history:
            print(
                    f"{message['role']}: {message['content']}\n------------------------",
                )

    def chat(self, query):
        self.add_message("user", query)
        print(self.conversation_history)
        chat_response = self.chat_completion_with_function_execution(self.conversation_history)
        return chat_response


def main():
    bot = Chatbot()
    while True:
        usr_input = input("User: ")
        if usr_input == "quit":
            break
        resp = bot.chat(usr_input)
        print(resp)


if __name__ == "__main__":
    main()