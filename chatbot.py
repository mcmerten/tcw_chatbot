import os
from dotenv import load_dotenv
#import promptlayer
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Chroma
from langchain.prompts import PromptTemplate
#from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.embeddings import OpenAIEmbeddings
#from langchain.chat_models import PromptLayerChatOpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
#from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain

#os.environ["LANGCHAIN_HANDLER"] = "langchain"
#os.environ["LANGCHAIN_SESSION"] = "chatbot"
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_TOKEN')
#promptlayer.api_key = os.environ.get("PL_API_TOKEN")
   
embeddings = OpenAIEmbeddings()
db = Chroma(persist_directory="chroma_db", embedding_function=embeddings,
                 collection_name="tcw_chroma_collection")

class Chatbot:
    def __init__(self):

        # Define Condense Question Prompt
        _template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question.
        Chat History:
        {chat_history}
        Follow Up Input: {question}
        Standalone question:"""
        CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)

        # Define Question Answering Prompt
        template = """
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

        # Define Language Model
        llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")

        # Define Question Generator
        QA_PROMPT = PromptTemplate(template=template, input_variables=[
                           "question", "context"])
        question_generator = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT, verbose=False)

        # Define Document Retrieval Chain
        doc_chain = load_qa_chain(llm=llm, prompt=QA_PROMPT, chain_type="stuff", verbose=True)

        # Define Memory
        memory = ConversationBufferMemory(memory_key='chat_history',
                                  return_messages=True,
                                  output_key='answer')

        # Define Chatbot
        self.qa = ConversationalRetrievalChain(
            question_generator=question_generator,
            combine_docs_chain=doc_chain,
            retriever=db.as_retriever(),
            memory=memory,
            verbose=False
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