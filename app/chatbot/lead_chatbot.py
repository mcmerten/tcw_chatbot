import openai
from app.config import settings
from app.chatbot.prompts import LeadPrompts
from app.core.logger import get_logger

logger = get_logger(__name__)

class LeadChatbot:
    def __init__(self, history=None):
        self.chat_history = history or []
        openai.api_key = settings.OPENAI_API_KEY

    def get_answer(self, user_message):
        system_prompt = LeadPrompts.system_prompt(self.chat_history)
        try:
            response = openai.ChatCompletion.create(
                # TODO: add config variable for model
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
            )
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return

        answer = response['choices'][0]['message']['content']
        if __name__ == "__main__":
            self.chat_history.append((f"User: {user_message}\n", f"Assistant: {answer}\n"))
        return answer

    def chat(self, query, history=None):
        if history:
            self.chat_history = history
        final_answer = self.get_answer(query)
        return final_answer


if __name__ == "__main__":
    bot = LeadChatbot()

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        response = bot.chat(user_input)
        print("Bot: ", response)
