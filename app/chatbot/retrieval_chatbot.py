# https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb

import openai
import pinecone

from app.config import settings

openai.api_key = settings.OPENAI_API_KEY

# Initialize connection to Pinecone
pinecone.init(
    api_key=settings.PINECONE_API_KEY,
    environment=settings.PINECONE_ENVIRONMENT
)

index = pinecone.Index(settings.PINECONE_INDEX_NAME)


class RetrievalChatbot:
    def __init__(self, history):
        self.chat_history = history
        self.embed_model = "text-embedding-ada-002"

    def query_vector(self, query):
        """Get embedding for query"""
        res = openai.Embedding.create(
            input=[query],
            engine=self.embed_model
        )
        embedded_question = res['data'][0]['embedding']

        # Get relevant contexts from Pinecone
        query_results = index.query(
            embedded_question,
            top_k=5,
            include_metadata=True
        )

        return query_results

    def get_content(self, query_results, include_source=False):
        """Extract content from results"""
        # TODO: implement source URL --> item['metadata']['source-url']
        return [
            item['metadata']['text']
            for item in query_results['matches']
        ]

    def get_answer(self, query, retrieved_content):

        system_prompt = """
            You are a helpful TCW website guide. You are designed to assist with questions related to the website of TCW. 
            - If you do not have enough information to answer the question, 
              ask a question back to the user that will help you answer  
              the original question, or point to the TCW contact page 
              "https://www.tcw.de/unternehmen/sonstiges/kontakt-170".
            - Always reply in the same language as the question was asked.
            - The answer should be never be longer than two sentences.
        """

        assistant_prompt = f"""
            Answer the following question based on the context below. Take the previous conversation into account.
            
            CONVERSATION HISTORY: 
            {self.chat_history}
            -----------------------------------
            QUESTION: 
            {query}
            -----------------------------------
            CONTEXT: 
            {retrieved_content}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": assistant_prompt},
            ]
        )

        answer = response['choices'][0]['message']['content']
        #self.chat_history.append((f"User: {query}\n", f"Assistant: {answer}\n"))

        return answer

    def chat(self, query):
        query_results = self.query_vector(query)
        content = self.get_content(query_results)
        final_answer = self.get_answer(query, content)
        return final_answer

# bot = Chatbot()
# bot.chat("Was macht TCW?")