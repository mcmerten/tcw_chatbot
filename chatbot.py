from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain.vectorstores import Pinecone
import pinecone
import os


load_dotenv()
GPT_MODEL = os.environ.get("GPT_MODEL")

# Connect to pinecone vector store
pinecone.init(environment="us-west1-gcp-free")
text_field = "text"
embeddings = OpenAIEmbeddings()
index = pinecone.Index("tcw-website-embeddings")
db = Pinecone(index, embeddings.embed_query, text_field)


class Chatbot:
    def __init__(self):
        self._define_prompts()
        self.llm = ChatOpenAI(temperature=0, model_name=GPT_MODEL)
        self.define_chains()
        self.chat_history = []

    def _define_prompts(self):
        template_condense = """
            Given the following conversation and a follow up question, 
            rephrase the follow up question to be a standalone question.
            Chat History:
            {chat_history}
            Follow Up Input: {question}
            Standalone question:
        """
        self.condense_question_prompt = PromptTemplate.from_template(template_condense)

        template_qa = """
            Assistant is a LLM trained to be an enthusiastic TCW website guide.
            Assistant is designed to assist with question related to the website of TCW (Transfer-Wissen-Centrum).
            Assistant will answer the question based on the context below and follows ALL the following rules when generating an answer:
            - The primary goal is to provide the user with an answer that is relevant to the question.
            - Do not make up any answers if the CONTEXT does not have relevant information.
            - Answer the question in the language in which it was asked and with in an informal tone, in german use "Sie".
            - IF the context does not have relevant information, ask a question back to the user that will help you answer the original question, or point to the TCW contact page "https://www.tcw.de/unternehmen/sonstiges/kontakt-170".
            - The answer should be no longer than 2 sentences.
            Question: {question}
            =========
            {context}
            =========
        """
        self.qa_prompt = PromptTemplate(
            template=template_qa,
            input_variables=["question", "context"]
        )

    def define_chains(self):
        question_generator = LLMChain(
            llm=self.llm,
            prompt=self.condense_question_prompt,
            verbose=False
        )
        doc_chain = load_qa_chain(
            llm=self.llm,
            prompt=self.qa_prompt,
            chain_type="stuff",
            verbose=False
        )
        memory = ConversationBufferMemory(
            memory_key='chat_history',
            return_messages=True,
            output_key='answer'
        )

        self.qa = ConversationalRetrievalChain(
            question_generator=question_generator,
            combine_docs_chain=doc_chain,
            retriever=db.as_retriever(),
            memory=memory,
            verbose=False
        )

    def get_answer(self, query):
        result = self.qa({"question": query, "chat_history": self.chat_history})
        self.chat_history.append((query, result["answer"]))
        return result["answer"]


    def get_chat_history(self):
        return self.chat_history

    # create a function which appends the most recent chat history to a file based on a user id
    def append_chat_history(self, user_id):
        pass




