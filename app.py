import os
import requests
from dotenv import load_dotenv
from flask import request,Flask,render_template,redirect,url_for,flash
from user_utils import add_user,init_db
import sqlite3
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from post_linebot import post_func
from pytz import timezone


#グローバル変数の設定
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
USER_ID = os.getenv('USER_ID') #テスト用の管理者lineID
DB_NAME = 'users.db'
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
city = 'Tokyo'


app = Flask(__name__)
app.secret_key = 'boyan'
init_db()



#ルーティング==========================================

@app.route('/')
# 管理画面URL
def dashboard():
     users = get_all_users()
     return render_template('dashboard.html',users=users)


@app.route('/push_test',methods=['POST'])
# 個別送信のテスト
def push_test():    
    bot_message = request.form.get('message')
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    message = {
                "to": USER_ID,
                "messages":
                [{"type": "text", "text": bot_message}]
            }
    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=message
        )
    print(f'入力されたメッセージ：\n{bot_message}')
    print(f'レスポンスのステータスコード：\n{response.status_code}')
    print(f'レスポンスのテキスト：\n{response.text}')
     
    if response.status_code == 200:
         flash('テスト送信が成功しました(200)')  
    else:
         flash('テスト送信に失敗しました')
    return redirect(url_for('dashboard'))


@app.route('/broadcast',methods=['POST'])
# お友達登録者(ID一覧表示者)に一斉送信
def send_multicast():
    user_ids = get_all_users_ids()
    bot_message = request.form.get('message')

    if not user_ids:
         return '送信対象がいません',400
     
    headers = {
         "Content-Type":"application/json",
         "Authorization":f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "to": user_ids,
        "messages": [
            {
                "type": "text",
                "text": bot_message
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
         flash('一斉送信が成功しました(200)')  
    else:
         flash('一斉送信に失敗しました')
    return redirect(url_for('dashboard'))


@app.route('/webhook',methods=['POST'])
#ユーザーIDの管理
def webhook():
    body = request.get_json()   
    print(f'リクエストAPI（辞書データ）：\n{body}ここまで')
    events = body.get('events',[])

    for event in events:
        event_type = event.get('type')
        if event_type in ['message','follow']:
            #userIdを取得
            user_id = event['source']['userId']
            #DBに保存
            add_user(user_id)
            print(f'追加したユーザーID：\n{user_id}')
        elif event_type == 'unfollow':
             user_id = event['source']['userId']
             delete_user(user_id)
             print(f'削除したユーザーID：\n{user_id}')

    return 'ok',200

    
def get_all_users():
# DBからすべてのuserを取得してリストで返す
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id , created_at FROM users")
    rows = cur.fetchall()
    conn.close()
    print(f'usersの生データ:\n{rows}')
    return rows

def get_all_users_ids():
# userIdだけのリストを返す
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]


@app.route('/users')
#　DBから全てのデータを取得してrender_template()でリストを返す
def show_users():
        users = get_all_users()
        return render_template('users.html',users=users)

def delete_user(user_id):
#削除のDB操作    
     conn = sqlite3.connect(DB_NAME)
     cur = conn.cursor()
     cur.execute("DELETE FROM users WHERE user_id = ?",(user_id,))
     conn.commit()
     conn.close()
     

def get_weather():
# 今日の天気予報の取得
    forecast_url = ( f"https://api.openweathermap.org/data/2.5/forecast"
                        f"?q={city},jp&appid={WEATHER_API_KEY}&lang=ja&units=metric" )
    try:
        response = requests.get(forecast_url)
        data = response.json()
        if not data:
             print(f'天気予報APIの入手に失敗😿')
             return
        print(f"天気予報の生データ：\n{data}") # 今日の日付（例: "2025-08-26"） 
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        # 今日のデータだけ抽出 
        today_list = [ item for item in data["list"] if item["dt_txt"].startswith(today_str) ] # 今日の最高・最低気温を計算 
        temp_max = round(max(item["main"]["temp_max"] for item in today_list)) 
        temp_min = round(min(item["main"]["temp_min"] for item in today_list)) 
        description = today_list[0]["weather"][0]["description"] 
        messages = f"🌤 今日の天気予報（{city}）\n" f"天気：{description}\n" f"最高気温：{temp_max}℃\n" f"最低気温：{temp_min}℃"
        return messages
    except Exception as e: 
        print(f"天気予報の取得中にエラーが発生しました: {e}") 
        messages = '天気予報の取得に失敗しました🥲'
        return messages

def job_func():
# APSchedulerへ渡すfunc
    today_forcast = get_weather()

    print(f'today_forcast:\n{today_forcast}')

    text_data = today_forcast
    post_func(text_data)


def job_weather():
    URL = "https://www.jma.go.jp/bosai/warning/data/warning/130000.json"
    SHIBUYA = "1311300"  # 渋谷区コード
    WARNING_CODES = {
        "14": "雷注意報",
        "10": "大雨注意報",
        "15": "強風注意報"
    }

    try:
        res = requests.get(URL, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f'⚠️ 気象庁のAPI取得に失敗しました：\n{e}')
        return

    status_msgs = []
    for at in data.get("areaTypes", []):
        for area in at.get("areas", []):
            if area.get("code") == SHIBUYA:
                for w in area.get("warnings", []):
                    code = w.get("code")
                    status = w.get("status", "不明")
                    if not code:
                        continue  # 「なし」は無視
                    if code in WARNING_CODES:
                        name = WARNING_CODES[code]
                        status_msgs.append(f"{name}：{status}")

    # --- 出力 ---
    if status_msgs:
        msg = "⚡【渋谷区 注意報】\n" + "\n".join(status_msgs)
        print(msg)
        post_func(msg)
    else:
        msg = "☀️ 渋谷区に気象注意報はありません。"
        print(msg)
        post_func(msg)


scheduler = BackgroundScheduler()
def start_scheduler():
# スケジューラーのスタート関数
    if not scheduler.running:
        print("🚀 Schedulerを開始します")
        # 天気予報
        scheduler.add_job(job_func,'cron', hour=20,minute=30,timezone=timezone("Asia/Tokyo"),id="weather_evning", replace_existing=True)
        scheduler.add_job(job_func,'cron', hour="8,11,14,17",minute=30,timezone=timezone("Asia/Tokyo"),id="weather_morning", replace_existing=True)
        print("スケジューラースタート👻")
        # 雷通知
        scheduler.add_job(job_weather,'cron',hour="8-23",minute=0,timezone=timezone("Asia/Tokyo"),id="thunder_alert", replace_existing=True)
        
        scheduler.start()
        print("✅ Schedulerがスタートしました")
        for job in scheduler.get_jobs():
            print("登録ジョブ:", job)

start_scheduler()



if __name__ == '__main__':
    app.run(port=5000)


