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
        self._lead_generation_status = "In Progress"
        self.lead_data = ""
        self.lead_chatbot = LeadChatbot()
        self.retrieval_chatbot = RetrievalChatbot()
        self.system_prompt = DefaultPrompts.system_prompt()
        self.functions = DefaultPrompts.system_functions()
        self.add_message("assistant", "Hallo, ich bin der TCW Bot. Wie kann ich Ihnen weiterhelfen?")

    @property
    def lead_generation_status(self):
        return self._lead_generation_status

    @lead_generation_status.setter
    def lead_generation_status(self, new_status):
        if new_status == "In Progress":
            return
        self._lead_generation_status = new_status
        if new_status == "Success":
            self.summarize_conversation()
        logger.info("lead_qualification() function disabled")
        self.functions = [self.functions[0]]


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
            results = self.retrieval_chatbot.chat(parsed_output["query"], self.get_chat_history(), self.get_lead_data())
        elif function_name == "lead_qualification":
            logger.info("Calling lead_qualification() function")
            results, lead_generation_status = self.lead_chatbot.chat(parsed_output["query"], self.get_chat_history())
            self.lead_generation_status = lead_generation_status
        else:
            raise Exception("Function does not exist and cannot be called")

        self.add_message("assistant", str(results))
        return str(results)

    def chat_completion_with_function_execution(self, query):
        """This function makes a ChatCompletion API call with the option of adding functions"""
        messages_body = [{"role": "system", "content": self.system_prompt},
                         {"role": "user", "content": query}]
        functions = self.functions
        response = self.chat_completion_request(messages_body, functions)
        full_message = response.json()["choices"][0]
        if full_message["finish_reason"] == "function_call":
            logger.info(f"Function generation requested")
            return self.call_chatbot_function(messages_body, full_message)
        else:
            logger.info(f"Function not required, calling retrieval chatbot as fallback option")
            return self.retrieval_chatbot.chat(query, self.get_chat_history())

    def summarize_conversation(self):
        """Summarize conversation history for retrieval chatbot"""
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": f"CONVERSATION HISTORY: '''{self.get_chat_history()}'''"},
                {"role": "user", "content": "Extract only information stated by the user information from the conversation history."}
            ],
            functions=[{"name": "extract_lead_data", "parameters": DefaultPrompts.summary_schema()}],
            function_call={"name": "extract_lead_data"},
            temperature=0,
        )
        result = json.loads(completion.choices[0].message.function_call.arguments)
        self.lead_data = result
        logger.info(f"Lead data extracted: {result}")

    def add_message(self, role, content):
        message = f"{role}: {content}"
        self.conversation_history.append(message)

    def get_chat_history(self):
        return self.conversation_history

    def get_lead_data(self):
        return self.lead_data

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
        print(f"Bot: {resp}")


if __name__ == "__main__":
    main()
