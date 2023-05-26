#!/usr/bin/env python
# coding: utf-8
import re
import promptlayer
from dotenv import load_dotenv
import gradio as gr
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.embeddings import OpenAIEmbeddings
import os
from langchain.chat_models import PromptLayerChatOpenAI


os.environ["LANGCHAIN_HANDLER"] = "langchain"
os.environ["LANGCHAIN_SESSION"] = "chatbot"


# Enable tracing of langchain via command line 'langchain-server' on http://localhost:4173/sessions

load_dotenv()
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_TOKEN')
#os.environ['PROMPTLAYER_API_KEY']= os.environ.get("PL_API_TOKEN")
promptlayer.api_key = os.environ.get("PL_API_TOKEN")

embeddings = OpenAIEmbeddings()
db = Chroma(persist_directory="chroma_db_single_mode", embedding_function=embeddings,
            collection_name="tcw_chroma_collection")

# Prompt Template & Messages
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
QA_PROMPT = PromptTemplate(template=template, input_variables=["question", "context"])

memory = ConversationBufferMemory(memory_key='chat_history',
                                  return_messages=True, 
                                  output_key='answer')


# Initialize the ChatVectorDBChain
qa = ConversationalRetrievalChain.from_llm(
    PromptLayerChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", pl_tags=["local", "firstTemp"]),
    retriever=db.as_retriever(search_type="similarity", search_kwargs={"k": 3}),    
    verbose=True, 
    return_source_documents=True,
    qa_prompt=QA_PROMPT,
    condense_question_prompt=CONDENSE_QUESTION_PROMPT,
)

# Format the text in the return
def format_terms(text):
    formatted_text = re.sub(r'[“"”]([^”“]+)[“"”]', r'<b>\1</b>', text)
    formatted_text = formatted_text.replace('\n', '<br>')
    return formatted_text


chat_history = []
def get_answer(query):
    
    result = qa({"question": query, "chat_history": chat_history})
    print(result)
    chat_history.append((query, result["answer"])) 

     # Use a set to remove duplicates
    source_urls = list(set(doc.metadata["source"] for doc in result["source_documents"]))  
    
    formatted_answer = format_terms(result['answer'])    
    
    answer = f"<strong>Answer:</strong><br><br> {formatted_answer}<br><br><strong>Source URLs:</strong><br>"
    answer += "<br>".join(f'<a href="{url}" target="_blank" style="font-size:0.7em">{url}</a>' for url in source_urls)
    
    return answer


# Gradio Interface
def user(user_message, history):
    return "", history + [[user_message, None]]

def bot(history):
    query = history[-1][0]
    result = get_answer(query)
    history[-1][1] = result
    return history

# Launch the Gradio interface with the chatbot components and functions
with gr.Blocks() as demo:
    chatbot = gr.Chatbot()

    with gr.Row():
        msg = gr.Textbox(
            label="Wie kann ich Ihnen weiterhelfen?",
            placeholder="Welche Beratungsdienstleistungen bietet TCW an?",
            lines=2,
        )
        submit = gr.Button(value="Submit", variant="primary").style(full_width=False)
        clear = gr.Button("Clear", style="secondary").style(full_width=False)

    gr.Examples(
        examples = [
            ["Wer ist Prof. Dr. Wildemann?"],
            ["Welche Beratungsdienstleitungen bietet TCW an?"],
            ["Ich habe eine Frage zu einem Data-Science Projekt. Wie können Sie mir weiterhelfen?"],
        ],
        inputs=msg,
    )

    submit.click(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, chatbot, chatbot
    )
    clear.click(lambda: None, None, chatbot, queue=False)

    with gr.Row():
        msg
        submit
        clear

demo.launch()