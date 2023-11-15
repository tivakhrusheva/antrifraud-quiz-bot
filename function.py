import numpy as np
from db import select_count_cls, select_picture_from_table, select_worst_cls, select_unique_users
import random
from telegram import TelegramUtils


class eGreedy:
    def __init__(self, arms=['sms', 'telegram', 'whatsapp', 'email', 'dating site'], e=0.01):
        self.arms = arms
        self.e = e

    def decide(self, user_id: str, tablename='quiz_results') -> str:
        # дернуть каждую ручку один раз для первоначальной статистики
        for arm in self.arms:
            if select_count_cls(category=arm, user_id=user_id, tablename=tablename)[0].rows[0]['hits'] == 0:
                print(f'Дергаю неинициализированную ручку {arm}')
                return arm

        # если случайное число меньше epsilon, то выбрать ручку случайно и закончить
        if np.random.rand() < self.e:
            print('Случайный выбор категории!')
            return random.choice(self.arms)
        print('Осознанный выбор самой слабой категории юзера')
        worst_cls = select_worst_cls(user_id, "quiz_results")
        return worst_cls

    def get_next(self, chat_id):
        # выбираем ручку
        arm = self.decide(chat_id)
        print(f'Selected arm: {arm}')
        # т.к. send_pic() в качестве параметра принимает текст, то преобразуем к тексту. Можно поменять send_pic и сделать выбор API по числу
        pict_info = select_picture_from_table(arm)
        correct_answer = pict_info['is_fraud'].decode("utf-8")
        print(f"correct_answer = {correct_answer}")
        link = pict_info['link'].decode("utf-8")
        print(f"picture url = {link}")
        # sending picture
        TelegramUtils(chat_id).send_picture(link)
        # sending question + button menu
        TelegramUtils(chat_id).send_question(arm, correct_answer)
