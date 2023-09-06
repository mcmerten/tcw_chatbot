import json
import openai
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt
from app.chatbot.prompts import DefaultPrompts
from app.chatbot.retrieval_chatbot import RetrievalChatbot
from app.chatbot.lead_chatbot import LeadChatbot
from app.config import settings
from app.core import logger

logger = logger.get_logger(__name__)

openai.api_key = settings.OPENAI_API_KEY

class Chatbot:
    def __init__(self):
        self.conversation_history = []
        self.lead_chatbot = LeadChatbot()
        self.retrieval_chatbot = RetrievalChatbot()
        self.system_prompt = DefaultPrompts.system_prompt()
        self.assistant_prompt = DefaultPrompts.assistant_prompt()
        self.add_message("system", self.system_prompt)
        self.add_message("assistant", "Hallo, ich bin der TCW Bot. Wie kann ich Ihnen weiterhelfen?")

        self.functions = [
            {
                "name": "lead_qualification",
                "description":  """Collect data about the user to qualify them as a lead.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "User query to the assistant",
                        }
                    },
                    "required": ["query"],
                    "optional": ["chat_history"]
                },
            },
            {
                "name": "website_chat",
                "description": "Provide information about the TCW website and it's contents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "User query to the assistant asking about TCW website",
                        }
                    },
                    "required": ["query"],
                    "optional": ["chat_history"]
                },
            }
        ]

    @retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
    def chat_completion_request(self, messages, functions=None, model="gpt-4-0613"):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + openai.api_key,
        }
        json_data = {"model": model, "messages": messages}
        if functions is not None:
            json_data.update({"functions": functions})
            #json_data.update({"function_call": {"name": "website_chat"}})
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
            results = self.retrieval_chatbot.chat(parsed_output["query"], self.conversation_history)
        elif function_name == "lead_qualification":
            logger.info("Calling lead_qualification() function")
            results = self.lead_chatbot.chat(parsed_output["query"], self.conversation_history)
        else:
            raise Exception("Function does not exist and cannot be called")

        self.add_message("assistant", str(results))
        return str(results)
        # Necessary?
        #try:
        #    response = self.chat_completion_request(messages)
        #    return response.json()
        #except Exception as e:
        #    print(type(e))
        #    raise Exception("Function chat request failed")

    def chat_completion_with_function_execution(self, query):
        """This function makes a ChatCompletion API call with the option of adding functions"""

        messages_body = [{"role": "system", "content": self.system_prompt},
                        # {"role": "assistant", "content": self.assistant_prompt},
                         {"role": "user", "content": query}]
        functions = self.functions
        response = self.chat_completion_request(messages_body, functions)
        full_message = response.json()["choices"][0]
        if full_message["finish_reason"] == "function_call":
            logger.info(f"Function generation requested")
            return self.call_chatbot_function(messages_body, full_message)
        else:
            logger.info(f"Function not required, responding to user")
            return response.json()

    def add_message(self, role, content):
        message = f"{role}: {content}"
        self.conversation_history.append(message)

    def display_conversation(self):
        for message in self.conversation_history:
            print(f"{message}\n")

    def chat(self, query):
        self.add_message("user", query)
        chat_response = self.chat_completion_with_function_execution(query)
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
