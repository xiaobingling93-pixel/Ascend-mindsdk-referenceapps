import json
import logging
import random
import threading

import requests

logging.basicConfig(level=logging.INFO)
SERVICE_URL = 'http://127.0.0.1:8000/query/'

QUESTION = [
    "请描述2024年高考作文",
    "中国的绿色发展有哪些好处",
    "描述一下可持续发展战略",
    "解释一下极昼极夜",
    "介绍一下台风",
    "解释一下地球的内部结构",
    "黄土高原的环境问题该怎么解决",
    "介绍一下巴西",
    "介绍一下爪哇岛",
    "高技术工业特区有什么特点",
    "台风来了怎么办",
    "台风的发生条件？",
    "洋流有几种",
    "地球上为什么会产生昼夜更替",
    "坚持以人民为中心的内涵是什么",
    "圣诞节这一天，哈尔滨的白昼为什么最短",
    "西北太平洋热带气旋出现的纬度？",
    "东部地区重要的地理界线是什么？",
    "印尼五大岛屿分别是哪些？",
    "描述一下地球的内部结构"
]

DATA_TEMPLATE = {
    'question': 'value1',
}


# 定义一个函数来发送POST请求
def send_post_request(post_data, thread_id):
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVICE_URL, data=json.dumps(post_data), headers=headers)
        logging.info('\nThread %d: Status Code %d, Response Body: %s', thread_id, response.status_code, response.text)
    except Exception as e:
        logging.debug('Thread %d encountered an error: %s', thread_id, e)


# 创建线程列表
threads = []

# 创建并启动多个线程
for i in range(20):
    # 为每个线程准备不同的数据
    data = DATA_TEMPLATE.copy()
    data['question'] = f'{QUESTION[random.randint(0, 19)]}'

    # 创建线程
    thread = threading.Thread(target=send_post_request, args=(data, i))
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()

logging.info('All threads have finished execution')
