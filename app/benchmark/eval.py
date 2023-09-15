from app.chatbot.retrieval_chatbot import RetrievalChatbot

import benchllm

@benchllm.test(suite=".")
def bench_chat(input: str):
    bench_bot = RetrievalChatbot()
    bench_bot_answer = bench_bot.chat(input)
    print(bench_bot_answer)
    return bench_bot_answer
