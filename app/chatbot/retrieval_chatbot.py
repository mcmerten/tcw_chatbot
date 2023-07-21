# https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
import openai
import pinecone

from app.config import settings
from app.chatbot.prompts import RetrievalPrompts
from app.core import logger

logger = logger.get_logger(__name__)

openai.api_key = settings.OPENAI_API_KEY

# Initialize connection to Pinecone
pinecone.init(
    api_key=settings.PINECONE_API_KEY,
    environment=settings.PINECONE_ENVIRONMENT
)

class RetrievalChatbot:
    def __init__(self, history=[]):
        self.chat_history = history
        self.embed_model = "text-embedding-ada-002"
        self.index = pinecone.Index(settings.PINECONE_INDEX_NAME)

    def query_vector(self, query):
        """Get embedding for query"""
        res = openai.Embedding.create(
            input=[query],
            engine=self.embed_model
        )
        embedded_question = res['data'][0]['embedding']

        # Get relevant contexts from Pinecone
        query_results = self.index.query(
            embedded_question,
            top_k=5,
            include_metadata=True
        )

        return query_results

    def get_content(self, query_results):
        """Extract content from results"""
        content_list = list(map(lambda item: ({item['metadata']['text']}, ({item['metadata']['source-url']})), query_results['matches']))
        return content_list

    def get_answer(self, query, retrieved_content):
        system_prompt = RetrievalPrompts.system_prompt()
        user_prompt = RetrievalPrompts.cot_prompt(query=query,
                                                  chat_history=self.get_chat_history(),
                                                  context=retrieved_content)
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        answer = response['choices'][0]['message']['content']
        if __name__ == "__main__":
            self.chat_history.append((f"User: {query}\n", f"Assistant: {answer}\n"))

        return answer

    def get_chat_history(self):
        return self.chat_history

    def chat(self, query, history=None):
        if history:
            self.chat_history = history
        query_results = self.query_vector(query)
        content = self.get_content(query_results)
        final_answer = self.get_answer(query, content)
        return final_answer


if __name__ == "__main__":
    bot = RetrievalChatbot()

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        bot_response = bot.chat(user_input)
        print("Bot: ", bot_response)