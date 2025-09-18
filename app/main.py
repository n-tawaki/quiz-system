from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from fastapi import Depends
from fastapi.staticfiles import StaticFiles
from typing import List
import psycopg2
import os
from datetime import datetime
import logging
import sys

logging.basicConfig(level=logging.DEBUG)  # これで print 同等の出力保証
logger = logging.getLogger("app")  # 任意のロガー名

logger.info("サーバー起動時に出るはずのログ")


app = FastAPI()

# 接続しているクライアントを管理
clients: List[WebSocket] = []
current_state = "WAITING"
current_question_id = 0
question_start_time = None

""""
websocket接続用API
"""
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        # 初回接続時に最新状態を送ってあげる
        await ws.send_json({"state": current_state})
        while True:
            await ws.receive_text()  # 今回はクライアントからは受け取らない
    except WebSocketDisconnect:
        clients.remove(ws)

"""
出題状況状態取得API
現在の状態(待機中or出題中)と今何問目かを返す
"""
@app.get("/state")
async def get_state():
    return {"state": current_state, "question_id": current_question_id}

"""
出題状況更新API
引数 変更後のステータス、今何問目か
"""
@app.post("/state")
async def change_state(new: dict):
    global current_state
    global current_question_id
    current_state = new["state"]
    current_question_id = new["question_id"]
    
    # 出題開始時刻を記録
    logger.info(current_question_id)
    conn = get_db_connection()
    cur = conn.cursor()
    if current_state == "ANSWERING":

        cur.execute("UPDATE questions SET start_time = %s WHERE id = %s",  (datetime.now(), current_question_id))
        conn.commit()
    cur.close()
    conn.close()

    # 接続中の全クライアントに通知
    for ws in clients:
        await ws.send_json({"state": current_state, "question_id": current_question_id})
    return {"success": True, "state": current_state, "question_id": current_question_id}

"""
DB接続用関数
"""
def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "yourdb"),
        user=os.getenv("POSTGRES_USER", "youruser"),
        password=os.getenv("POSTGRES_PASSWORD", "yourpass"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
    )
    return conn

"""
全問題取得API(未使用？)
"""
@app.get("/questions")
def get_questions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, question_text, choice_a, choice_b, choice_c, choice_d FROM questions;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"id": r[0], "question_text": r[1], "choice_a": r[2], "choice_b": r[3], "choice_c": r[4], "choice_d": r[5]}
        for r in rows
    ]

"""
回答を保持するクラス
回答者名,問題ID,回答を保持する
"""
class AnswerRequest(BaseModel):
    user_name: str
    question_id: int
    selected_choice: str  # "1", "2", "3", "4"

"""
回答登録API
AnswerRequestクラス内の情報をDBに保存する
"""
@app.post("/answers")
def submit_answer(req: AnswerRequest):
    conn = None
    try:
        conn = psycopg2.connect(
            dbname="yourdb",
            user="youruser",
            password="yourpass",
            host="postgres",
            port=5432
        )
        cur = conn.cursor()

        # 正解取得
        cur.execute("SELECT correct_answer, start_time FROM questions WHERE id = %s", (req.question_id,))
        result = cur.fetchone()
        if not result:
            return {"success": False, "error": "Question not found"}
        
        logger.info("正誤判定")
        
        correct_answer, start_time = result
        is_correct = (req.selected_choice == correct_answer)
        
        logger.info("回答時間計測")
        
        answered_at = datetime.now()
        answer_time_ms = None
        if start_time:
            delta = answered_at - start_time
            answer_time_ms = int(delta.total_seconds()*1000)
            
        logger.info("DB記録開始")
        
        # DBに記録
        cur.execute(
            "INSERT INTO user_answers (user_name, question_id, selected_choice, is_correct, answered_at, answer_time_ms) VALUES (%s, %s, %s, %s, %s, %s)",
            (req.user_name, req.question_id, req.selected_choice, is_correct, answered_at, answer_time_ms)
        )
        conn.commit()
        
        logger.info("DB記録終了")

        return {"success": True, "is_correct": is_correct}

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()

"""
スコア取得API
パスパラメータにユーザ名を含めると、そのユーザのユーザ名と得点を返す
"""
@app.get("/scores/{user_name}")
def get_score(user_name: str):
    conn = None
    try:
        conn = psycopg2.connect(
            dbname="yourdb",
            user="youruser",
            password="yourpass",
            host="postgres",
            port=5432
        )
        cur = conn.cursor()

        # 正解数取得
        cur.execute("SELECT COUNT(*) FROM user_answers WHERE is_correct = true AND user_name = %s", (user_name,))
        score = cur.fetchone()[0]

        return {"user_name": user_name, "score": score}

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()

"""
回答取得API
パスパラメータにユーザ名と問題IDを含めると、その回答の正誤を返す
"""
@app.get("/answers/{user_name}/{question_id}")
def get_answer(user_name: str, question_id: int):
    conn = None
    try:
        conn = psycopg2.connect(
            dbname="yourdb",
            user="youruser",
            password="yourpass",
            host="postgres",
            port=5432
        )
        cur = conn.cursor()

        cur.execute(
            "SELECT selected_choice FROM user_answers WHERE user_name = %s AND question_id = %s",
            (user_name, question_id)
        )
        result = cur.fetchone()
        cur.close()

        if result:
            return {"answered": True, "selected_choice": result[0]}
        else:
            return {"answered": False}

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()

"""
回答集計API
各選択肢を選んだ人数を取得する
"""
@app.get("/answer_check/{question_id}")
def answer_check(question_id: int):
    conn = None
    try:
        conn = psycopg2.connect(
            dbname="yourdb",
            user="youruser",
            password="yourpass",
            host="postgres",
            port=5432
        )
        cur = conn.cursor()

        cur.execute(
            """
            SELECT c.choice, COALESCE(a.count, 0) AS count
            FROM (VALUES ('1'), ('2'), ('3'), ('4')) AS c(choice)
            LEFT JOIN (
            SELECT selected_choice, COUNT(*) AS count
            FROM user_answers
            WHERE question_id = %s
            GROUP BY selected_choice
            ) a ON c.choice = a.selected_choice;
            """,
            (question_id,)
        )
        columns = ["choice", "count"]
        result = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()

"""
ランキング取得API
全ユーザのランキングを取得する
"""
@app.get("/ranking")
def get_ranking():
    conn = None
    try:
        conn = psycopg2.connect(
            dbname="yourdb",
            user="youruser",
            password="yourpass",
            host="postgres",
            port=5432
        )
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 
            RANK() OVER (ORDER BY COUNT(*) FILTER (WHERE is_correct = 't') DESC, 
            SUM(CASE WHEN is_correct = 't' THEN answer_time_ms ELSE 0 END)) AS rank, user_name, COUNT(*) FILTER (WHERE is_correct = 't') AS point, ROUND(SUM(CASE WHEN is_correct = 't' THEN answer_time_ms ELSE 0 END)::numeric/1000, 2) AS time
            FROM user_answers
            GROUP BY user_name
            """,
        )
        columns = ["rank", "user_name", "point", "time"]
        result = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()

"""
回答取得API
パスパラメータで指定したIDの回答を取得する
"""
@app.get("/correct_answer/{question_id}")
def get_correct_answer(question_id: int):
    conn = None
    try:
        conn = psycopg2.connect(
            dbname="yourdb",
            user="youruser",
            password="yourpass",
            host="postgres",
            port=5432
        )
        cur = conn.cursor()

        cur.execute(
            """
            SELECT correct_answer FROM questions WHERE id = %s
            """,
            (question_id,)
        )
        result = cur.fetchone()
        cur.close()

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if conn:
            conn.close()
    

# 現在のファイル位置から static フォルダまでの絶対パス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# static フォルダを / でアクセス可能にする
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")