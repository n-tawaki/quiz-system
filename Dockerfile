# ベースイメージ（軽量版）
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# 依存ファイルをコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリ本体をコピー
COPY ./app ./app

# コンテナ起動時にFastAPIを立ち上げるコマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
