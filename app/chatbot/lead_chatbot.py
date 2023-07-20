import openai
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

class LeadChatbot:
    def __init__(self, history=None):
        """
        Initialize the LeadChatbot class.

        Args:
            history (list, optional): The chat history. Defaults to None.
        """
        self.chat_history = history or []
        openai.api_key = settings.OPENAI_API_KEY

    def get_answer(self, user_message):
        """
        Get the answer from the chatbot.

        Args:
            user_message (str): The user's message.

        Returns:
            str: The chatbot's answer.
        """
        system_prompt = """
                        You're a lead generation bot with the task of engaging the user to obtain key information. Observe the following guidelines:
                        - You must answer in maximum 100 characters.
                        - Be friendly and thankful
                        - Answer the user's questions with something like "Before I answer your question, I need to ask you a few questions first."
                        - Respond to the user's answers with the next question
                        - You're only permitted to ask for the following details, in this order: name, company's industry & size, and email    
                        - After you collectd the relevant information, ask the user what they want to ask next.                    
                """

        assistant_prompt = f"""
                    Use the existing CONVERSATION HISTORY to identify which data has already been collected.

                    CONVERSATION HISTORY: 
                    {self.chat_history}
                """
        try:
            response = openai.ChatCompletion.create(
                # TODO: add config variable for model
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "assistant", "content": assistant_prompt},
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

    def chat(self, user_message):
        """
        Start a chat with the chatbot.

        Args:
            user_message (str): The user's message.

        Returns:
            str: The chatbot's answer.
        """
        final_answer = self.get_answer(user_message)
        return final_answer


if __name__ == "__main__":
    bot = LeadChatbot()

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        response = bot.chat(user_input)
        print("Bot: ", response)
