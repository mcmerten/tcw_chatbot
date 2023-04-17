#!/usr/bin/env python
# coding: utf-8

import os
from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.prompts import PromptTemplate#
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQAWithSourcesChain, RetrievalQA
from langchain import OpenAI
import gradio as gr

load_dotenv()
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_TOKEN')

embeddings = OpenAIEmbeddings()
db = Chroma(persist_directory="db", embedding_function=embeddings)

prompt_template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

{context}

Question: {question}
Answer in German:"""
PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)

chain_type_kwargs = {"prompt": PROMPT}
qa = RetrievalQA.from_chain_type(llm=OpenAI(),
                                 chain_type="stuff",
                                 retriever=db.as_retriever(),
                                 chain_type_kwargs=chain_type_kwargs, 
                                 return_source_documents=True)

########

def qa_query(query):
    result = qa({"query": query})
    #print(result['result'])
    return result

with gr.Blocks() as tcw_bot:
    chatbot = gr.Chatbot()
    msg = gr.Textbox(placeholder="Enter question and press enter", show_label=False)
    clear = gr.Button("Clear")

    def user(user_message, history):
        return "", history + [[user_message, None]]
    
    def bot(history):
        response = qa_query(history[-1][0])["result"]
        history[-1][1] = response

        return history

    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, chatbot, chatbot
    )
    clear.click(lambda: None, None, chatbot, queue=False)


tcw_bot.launch(share=False)