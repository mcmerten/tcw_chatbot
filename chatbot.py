import os
from dotenv import load_dotenv
import promptlayer
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import PromptLayerChatOpenAI

os.environ["LANGCHAIN_HANDLER"] = "langchain"
os.environ["LANGCHAIN_SESSION"] = "chatbot"

class Chatbot:
    def __init__(self):

        load_dotenv()
        os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_TOKEN')
        promptlayer.api_key = os.environ.get("PL_API_TOKEN")

        self.embeddings = OpenAIEmbeddings()
        self.db = Chroma(persist_directory="chroma_db", embedding_function=self.embeddings,
                         collection_name="tcw_chroma_collection")

        _template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question.
        Chat History:
        {chat_history}
        Follow Up Input: {question}
        Standalone question:"""
        CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)

        template = """
        # Assistant is a LLM trained to be an enthusiastic TCW website guide.
        # Assistant is designed to assist with question related to the website of TCW (Transfer-Wissen-Centrum).
        # Assistant will answer the question based on the context below and follows ALL the following rules when generating an answer:
        #  - The primary goal is to provide the user with an answer that is relevant to the question.
        #  - Do not make up any answers if the CONTEXT does not have relevant information.
        #  - Answer the question in the language in which it was asked and with in an informal tone, in german use "Sie".
        #  - IF the context does not have relevant information, ask a question back to the user that will help you answer the original question, or point to the TCW contact page "https://www.tcw.de/unternehmen/sonstiges/kontakt-170".

        Question: {question}
        =========
        {context}
        =========
        """
        QA_PROMPT = PromptTemplate(template=template, input_variables=[
                                   "question", "context"])

        memory = ConversationBufferMemory(memory_key='chat_history',
                                          return_messages=True,
                                          output_key='answer')

        self.qa = ConversationalRetrievalChain.from_llm(
            PromptLayerChatOpenAI(
                temperature=0, model_name="gpt-4", pl_tags=["docker", "papercups"]),
            retriever=self.db.as_retriever(
                search_type="similarity", search_kwargs={"k": 3}),
            verbose=True,
            return_source_documents=False,
            qa_prompt=QA_PROMPT,
            condense_question_prompt=CONDENSE_QUESTION_PROMPT,
        )

        self.chat_history = []

    def get_answer(self, query):
        result = self.qa(
            {"question": query, "chat_history": self.chat_history})
        self.chat_history.append((query, result["answer"]))
        print(result)
        return result["answer"]

    def get_chat_history(self):
        return self.chat_history
