#!/usr/bin/env python
# coding: utf-8
from dotenv import load_dotenv
import gradio as gr
from chatbot import Chatbot

chatbot = Chatbot()

# Gradio Interface
def user(user_message, history):
    return "", history + [[user_message, None]]

def query_chatbot(history):
    query = history[-1][0]
    result = chatbot.get_answer(query)
    history[-1][1] = result
    return history

# Launch the Gradio interface with the chatbot components and functions
with gr.Blocks() as demo:
    gradio_chatbot = gr.Chatbot()

    with gr.Row():
        msg = gr.Textbox(
            label="Wie kann ich Ihnen weiterhelfen?",
            placeholder="Welche Beratungsdienstleistungen bietet TCW an?",
            lines=2,
        )
        submit = gr.Button(value="Submit", variant="primary").style(full_width=False)
        clear = gr.Button("Clear").style(full_width=False)

    gr.Examples(
        examples = [
            ["Wer ist Prof. Dr. Wildemann?"],
            ["Welche Beratungsdienstleitungen bietet TCW an?"],
            ["Ich habe eine Frage zu einem Data-Science Projekt. Wie können Sie mir weiterhelfen?"],
        ],
        inputs=msg,
    )

    submit.click(user, [msg, gradio_chatbot], [msg, gradio_chatbot], queue=False).then(
        query_chatbot, gradio_chatbot, gradio_chatbot
    )
    clear.click(lambda: None, None, gradio_chatbot, queue=False)

    with gr.Row():
        msg
        submit
        clear

demo.launch()