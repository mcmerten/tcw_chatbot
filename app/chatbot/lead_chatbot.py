import openai
from app.config import settings

class LeadChatbot:
    def __init__(self, history):
        self.chat_history = history
        openai.api_key = settings.OPENAI_API_KEY

    def get_answer(self, user_message):
        system_prompt = """
                    You are a lead generation bot. You are tasked with asking the user questions to extract lead information.
                    - You ONLY extract information from the user. You DO NOT extract information from the assistant.
                    - Use the user's answers to ask the next question. 
                    - Do not ask multiple questions at once.
                    - Your answer should be short and precise. Do not exceed 150 characters.
                    - Always be thankful and polite. If the user does not want to answer the question, that's okay.
                    - Always start the conversation in German. Only switch the language if the user asks you to.
                    - You are ONLY allowed to ask for the following information in the following order:
                        1. name
                        2. company industry and company size
                        3. email
                """

        assistant_prompt = f"""
                    - Based on the following conversation history, check which information have already been asked for and ask the user for the missing information.

                    CONVERSATION HISTORY: 
                    {self.chat_history}
                """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "assistant", "content": assistant_prompt},
                    {"role": "user", "content": user_message},
                ]
            )
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return

        answer = response['choices'][0]['message']['content']
        # self.chat_history.append((f"User: {user_message}\n", f"Assistant: {answer}\n"))
        return answer

    def chat(self, user_message):
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

