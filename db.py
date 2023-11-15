import os
import ydb
from datetime import datetime
import random
import string


driver_config = ydb.DriverConfig(
    endpoint=os.getenv('YDB_ENDPOINT'), 
    database=os.getenv('YDB_DATABASE'),
    credentials=ydb.iam.ServiceAccountCredentials.from_file("key.json")
)

driver = ydb.Driver(driver_config)
# Wait for the driver to become active for requests.
driver.wait(fail_fast=True, timeout=5)
# Create the session pool instance to manage YDB sessions.
pool = ydb.SessionPool(driver)


def select_all(tablename):
    # create the transaction and execute query.
    text = f"SELECT * FROM {tablename};"
    return pool.retry_operation_sync(lambda s: s.transaction().execute(
        text,
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    ))

def select_picture_from_table(category: str, tablename: str = "fraud_examples") -> dict[str, str]:
    query = f"SELECT is_fraud, link FROM {tablename} WHERE category='{category}'"
    res = pool.retry_operation_sync(lambda s: s.transaction().execute(
        query,
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    ))
    return random.choice(res[0].rows)

def randomword(length: int = 10) -> str:
	letters = string.ascii_lowercase
	return ''.join(random.choice(letters) for i in range(length))
    
def insert_log(tablename: str, answer: str, category: str, chat_id: str):
    curr_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    # create the transaction and execute query.
    text = f"INSERT INTO {tablename} SELECT '{randomword()}' as id, '{answer}' as answer, '{category}' as category, '{chat_id}' as user_id, Datetime('{curr_time}') as answer_datetime;"
    return pool.retry_operation_sync(lambda s: s.transaction().execute(
        text,
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    ))

def select_count_cls(category: str, user_id: str, tablename: str = "quiz_results"):
    # create the transaction and execute query.
    text = f"SELECT COUNT(*) as hits FROM {tablename} WHERE category == '{category}' AND user_id='{user_id}';"
    return pool.retry_operation_sync(lambda s: s.transaction().execute(
        text,
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    ))
    

def get_n_answers(user_id: str, tablename: str = "quiz_results") -> int:
    overall_num= f"""
            SELECT COUNT(answer), category FROM {tablename} GROUP BY user_id, category HAVING user_id='{user_id}';
            """
    overall_sum = pool.retry_operation_sync(lambda s: s.transaction().execute(
            overall_num,
            commit_tx=True,
            settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
        ))
    return overall_sum[0].rows

def select_worst_cls(user_id: str, tablename: str = "quiz_results") -> str:
    # create the transaction and execute query.
    query = f"""
            SELECT COUNT(answer)*1.00000, category
            FROM {tablename}
            GROUP BY answer, user_id, category
            HAVING (answer="correct" AND user_id ='{user_id}')
        """
    res_correct = pool.retry_operation_sync(lambda s: s.transaction().execute(
        query,
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    ))[0].rows
    overall_sum = get_n_answers(user_id, tablename)

    all_answers_dict = {}
    only_correct_dict = {}
    results = {}

    print(f"overall_sum = {overall_sum}")
    
    for elem in overall_sum:
        all_answers_dict[elem['category'].decode("utf8")] = elem['column0']

    for pair in res_correct:
        only_correct_dict[pair['category'].decode("utf8")] = pair['column0']
    
    for item in all_answers_dict.items():
        try:
            print(f"n correct answers: {only_correct_dict[item[0]]}. n answers in category {item[0]}: {item[1]}")
            results[item[0]] = only_correct_dict[item[0]]/item[1]
            print(f"results = {results}")
        except KeyError:
            print(f"no correct answers in category {item[0]}. putting 0")
            print(f"results = {results}")
            results[item[0]] = 0.0
    
    print(f"resulting results = {results}")
    min_value = min(results.values())
    min_values_idxs = [i for i, x in enumerate(results.items()) if x[1] == min_value]
    if len(min_values_idxs) > 1:
        print("multiple minimum values. randoming..")
        return list(results.keys())[random.choice(min_values_idxs)]
    else: 
        print("single min value. returning only it")
        return min(results, key=results.get)

def select_unique_users(tablename: str = "quiz_results") -> list[dict[str, str]]:
    text = f"SELECT DISTINCT user_id FROM {tablename};"
    users = pool.retry_operation_sync(lambda s: s.transaction().execute(
            text,
            commit_tx=True,
            settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
        ))
    return [uid['user_id'] for uid in users[0].rows if 'user_id' in uid]

def n_corr(user_id: str, tablename: str = "quiz_results") -> str:
    query= f"""
            SELECT COUNT(answer) FROM {tablename} WHERE user_id='{user_id}' AND answer='correct'
            """
    n_corr = pool.retry_operation_sync(lambda s: s.transaction().execute(
        query,
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    ))
    return str(n_corr[0].rows[0]['column0'])

def n_incorr(user_id: str, tablename: str = "quiz_results") -> str:
    n_incorr= f"""
            SELECT COUNT(answer) FROM {tablename} WHERE user_id='{user_id}' AND answer='wrong'
            """
    n_incorr = pool.retry_operation_sync(lambda s: s.transaction().execute(
            n_incorr,
            commit_tx=True,
            settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
        ))
    return str(n_incorr[0].rows[0]['column0'])