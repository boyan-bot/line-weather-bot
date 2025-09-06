import os
import requests

CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
USER_ID = os.getenv('USER_ID') #テスト用の管理者lineID
user_id = USER_ID 


def post_func(text_data):
     
    headers = {
            "Content-Type":"application/json",
            "Authorization":f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
    data = {
        "to": [user_id],
        "messages": [
            {
                "type": "text",
                "text": text_data
            }
        ]
        }

    response = requests.post(
        "https://api.line.me/v2/bot/message/multicast",
        headers=headers,
        json=data
        )
    print(f'レスポンス：{response.status_code},{response.text}')

    if response.status_code == 200:
        print('一斉送信が成功しました(200)')  
    else:
        print('一斉送信に失敗しました')
