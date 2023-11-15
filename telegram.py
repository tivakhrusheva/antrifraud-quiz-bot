import json
import urllib3
import json
import os
import random
from texts import texts as contents
from db import n_incorr, n_corr


QUESTION_OPTIONS: list[str] = contents["question"]
START_TEXT: str = contents["start"]
http = urllib3.PoolManager()
TOKEN=os.getenv('TOKEN')
URL = f"https://api.telegram.org/bot{TOKEN}/"

class TelegramUtils:

    def __init__(self, chat_id: str):
        self.chat_id = chat_id

    def send_message(self, text: str):
        url = URL + f"sendMessage?text={text}&chat_id={self.chat_id}"
        return http.request("GET", url)
    
    def send_picture(self, image_url: str):
        url = URL + f"sendPhoto?photo={image_url}&chat_id={self.chat_id}"
        return http.request("GET", url)

    @staticmethod
    def create_answer_keyboard(arm: str, corr_answer: str = None):
        return json.dumps(
            { 
                "inline_keyboard":[
                    [{ "text": "Да", "callback_data": f"{arm}_yes_correct_{corr_answer}"},
                    { "text": "Нет", "callback_data": f"{arm}_no_correct_{corr_answer}"}]
                ]
            }
        )
    
    @staticmethod
    def create_begin_keyboard(text_message: str = "Начать"):
        return json.dumps(
            { 
                "inline_keyboard":[
                    [{ "text": text_message, "callback_data": "ready_begin"}]
                ]
            }
        )
    
    def send_begin_question(self, text: str = None, keyboard_message: str = "Начать"):
        data = {
                'text': (None, START_TEXT if text is None else text),
                'chat_id': (None, self.chat_id),
                'parse_mode': (None, 'Markdown'),
                'reply_markup': (None, TelegramUtils.create_begin_keyboard(keyboard_message))
            }
        url = URL + "sendMessage"
        http.request(
            'POST',
            url,
            fields=data
        )
    
    def send_question(self, arm, corr_answer):
  	# Create data dict
        data = {
            'text': (None, random.choice(QUESTION_OPTIONS)),
            'chat_id': (None, self.chat_id),
            'parse_mode': (None, 'Markdown'),
            'reply_markup': (None, self.create_answer_keyboard(arm, corr_answer))
        }
        url = URL + "sendMessage"
        http.request(
            'POST',
            url,
            fields=data
        )

    def send_statistics(self) -> str:
        correct = n_corr(self.chat_id)
        wrong = n_incorr(self.chat_id)
        if correct > wrong:
            changing_part = "Так держать! Мошенникам не так-то просто вас обмануть!\n"
        elif correct == wrong:
            changing_part = "Вы с мошенниками идёте нога в ногу.. Нужно ещё немного потренироваться, чтобы улучшить свои навыки обнаружения мошенников.\n"
        else:
            changing_part = "К сожалению, пока что мошенники обходят вас!\n"
        text = "Ваш счёт: " + correct + "\nСчёт мошенников: " + wrong + "\n" + changing_part
        return self.send_message(text)


    