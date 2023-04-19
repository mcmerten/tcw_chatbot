#!/usr/bin/env python
# coding: utf-8

import os
from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.prompts import PromptTemplate#
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQAWithSourcesChain, RetrievalQA, ConversationalRetrievalChain
from langchain import OpenAI
from langchain.memory import ConversationBufferMemory

import gradio as gr

load_dotenv()
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_TOKEN')

embeddings = OpenAIEmbeddings()
db = Chroma(persist_directory="chroma_db", embedding_function=embeddings, collection_name="tcw_chroma_collection")

# Tune prompt to give it more the sense of a chatbot 
prompt_template = """You are a chatbot used on a corporate website. Be helpful. Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

{context}

Question: {question}
Answer in German:"""
PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
) 

chain_type_kwargs = {"prompt": PROMPT}

#qa = RetrievalQA.from_chain_type(llm=OpenAI(),
#                                 chain_type="stuff",
#                                 retriever=db.as_retriever(),
#                                 chain_type_kwargs=chain_type_kwargs, 
#                                 return_source_documents=True)

chat_history = []
#memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

qa = ConversationalRetrievalChain.from_llm(llm = OpenAI(temperature=0),
                                           retriever = db.as_retriever(),
                                           qa_prompt=PROMPT,
                                           chain_type="stuff", 
                                           return_source_documents = False, 
                                           #memory = memory, 
                                           verbose = True)

def qa_query(query, chat_history):
    chat_history = []
    result = qa({"question": query, "chat_history" : chat_history})
    return result

with gr.Blocks() as tcw_bot:
    chatbot = gr.Chatbot()
    msg = gr.Textbox(placeholder="Enter question and press enter", show_label=False)
    clear = gr.Button("Clear")

    def user(user_message, history):
        return "", history + [[user_message, None]]
    
    def bot(history):
        query = history[-1][0]
        response = qa_query(query, chat_history)
        print(response)
        #chat_history.append((query, response["answer"]))
        response_result = response["answer"]
        history[-1][1] = response_result
        return history

    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, chatbot, chatbot
    )
    clear.click(lambda: None, None, chatbot, queue=False)

tcw_bot.launch(share=False)