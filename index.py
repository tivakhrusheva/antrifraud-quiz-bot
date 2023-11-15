import urllib3
import json
import os
import random
import numpy as np
from function import eGreedy
from db import select_picture_from_table, insert_log, select_unique_users
from telegram import TelegramUtils


http = urllib3.PoolManager()
TOKEN=os.getenv('TOKEN')
URL = f"https://api.telegram.org/bot{TOKEN}/"

from texts import texts as contents
QUESTION_OPTIONS: list[str] = contents["question"]
CORRECT_TEXTS: list[str] = contents["correct"]
INCORRECT_TEXTS: list[str] = contents["incorrect"]
REMINDER_TEXT: str = contents["reminder"]
EMAIL_CHECK_RUNNING: bool = False
egreedy_policy = eGreedy(e = 0.5)


def check_email(email_text: str):
    url = "https://spamcheck.postmarkapp.com/filter"
    data = json.dumps({
        "email": email_text,
        "options":"long"
        })
    r = http.request("POST", url, headers={'Content-Type': 'application/json'}, body=data)._body
    return json.loads(r.decode('utf-8'))


def send_question(arm, chat_id, corr_answer):
  	# Create data dict
	data = {
		'text': (None, random.choice(QUESTION_OPTIONS)),
		'chat_id': (None, chat_id),
		'parse_mode': (None, 'Markdown'),
		'reply_markup': (None, TelegramUtils(chat_id).create_answer_keyboard(arm, corr_answer))
	}
	url = URL + "sendMessage"
	http.request(
		'POST',
		url,
		fields=data
	)


def handler(event, context):
    global EMAIL_CHECK_RUNNING
    # return {
	# 	'statusCode': 200
	# }
    print(f"event = {event}")
    # cron
    if 'event_metadata' in event:
        users_ids = select_unique_users()
        users_ids = [user.decode("utf-8") for user in users_ids if user is not None]
        for unique_id in users_ids:
            TelegramUtils(unique_id).send_begin_question(text=REMINDER_TEXT, keyboard_message="Да")
    if 'body' in event:
        message = json.loads(event['body'])
        print(f"message = {message}")
        if 'message' in message.keys():
            print("!Got message in message.keys()!")
            chat_id = message['message']['chat']['id']
            tg_helper = TelegramUtils(chat_id)
            message_text = message['message']['text']
            if message_text == "/start":
                print(f"text is /start")
                #TelegramUtils(chat_id).send_begin_question()
                tg_helper.send_begin_question()
            
            if message_text == "/show_score":
                tg_helper.send_statistics()
                #TelegramUtils(chat_id).send_statistics()
            if message_text == "/check_email":
                print("!got command /check_email!")
                EMAIL_CHECK_RUNNING = True
                print(f"EMAIL_CHECK_RUNNING = {EMAIL_CHECK_RUNNING}")
                #TelegramUtils(chat_id).send_message("Введите текст письма:")
                tg_helper.send_message("Введите текст письма:")
            print(f"EMAIL_CHECK_RUNNING = {EMAIL_CHECK_RUNNING}, message_text = {message_text}")
            if (EMAIL_CHECK_RUNNING is True) & (not message_text.startswith("/")):
                check_res = check_email(message_text)
                print(f"check res = {check_res}")
                if check_res['success']:
                    score = check_res['score']
                    print(f"spam score: {score}")
                    expl = str([check_res['rules'][i]['description'] for i in range(0, len(check_res['rules']))]).replace("[", "").replace("]", "").replace("\\n", "")
                    resulting_text = "Индекс спама: " + check_res['score'] + " (значение выше 5 указывает на то, что письмо является спамом)\n" + "Объяснение:\n" + str(expl)
                    #TelegramUtils(chat_id).send_message(resulting_text)
                    tg_helper.send_message(resulting_text)
                else:
                    #TelegramUtils(chat_id).send_message("На нашей стороне что-то пошло не так.. Попробуй отправить запрос позднее.") 
                    tg_helper.send_message("На нашей стороне что-то пошло не так.. Попробуй отправить запрос позднее.")

        if 'callback_query' in message.keys():
            print("callback in message.keys(")
            chat_id = message['callback_query']['message']['chat']['id']
            tg_helper = TelegramUtils(chat_id)
            if message['callback_query']['data'] != "ready_begin":
                category, user_answer, _, correct_answer = message['callback_query']['data'].split("_")
                print(f"user answer: {user_answer}")
                if user_answer == correct_answer:
                    tg_helper.send_message(random.choice(CORRECT_TEXTS))
                    #TelegramUtils(chat_id).send_message(random.choice(CORRECT_TEXTS))
                    verdict = 'correct'
                    #insert_log(tablename="quiz_results", answer=, category, chat_id=chat_id)
                else:
                    tg_helper.send_message(random.choice(INCORRECT_TEXTS))
                    #TelegramUtils(chat_id).send_message(random.choice(INCORRECT_TEXTS))
                    verdict = 'wrong'
                insert_log(tablename="quiz_results", answer=verdict, category=category, chat_id=chat_id)
            egreedy_policy.get_next(chat_id)
   
    # print(select_all('quiz_results')[0].rows)
    return {
		'statusCode': 200
	}