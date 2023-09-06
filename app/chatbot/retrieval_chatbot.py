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

    def consolidate_query(self, query, history):
        """Consolidate query and history into new query for retrieval"""
        if len(history) == 0:
            return query
        else:
            recent_history = history[-2:]
            system_prompt = RetrievalPrompts.summary_prompt(chat_history=recent_history, user_question=query)
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                ]
            )
            answer = response['choices'][0]['message']['content']
            print(f"consolidated query: {answer}")
            return answer

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
        # TODO: Group results by item['metadata']['source-url']
        grouped_items = {}

        # Loop through the list of dictionaries
        for item in query_results['matches']:
            source_url = item['metadata']['source-url']
            if source_url in grouped_items:
                grouped_items[source_url].append(item)
            else:
                grouped_items[source_url] = [item]

        formatted_list = []
        for source_url, items in grouped_items.items():
            concatenated_texts = ""

            for item in items:
                text = item['metadata']['text']
                concatenated_texts += f"- {text}\n"

            formatted_entry = f"SOURCE: {source_url}\nCONTENT:\n{concatenated_texts}"
            formatted_list.append(formatted_entry)

        content = "\n".join(formatted_list)
        return content

    def get_answer(self, query, retrieved_content):
        system_prompt = RetrievalPrompts.system_prompt()
        assistant_prompt = RetrievalPrompts.cot_prompt(chat_history=self.get_chat_history(),
                                                       context=retrieved_content)
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": assistant_prompt},
                # {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": query},
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
        summarized_query = self.consolidate_query(query, self.chat_history)
        query_results = self.query_vector(summarized_query)
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
