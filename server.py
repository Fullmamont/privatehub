from flask import Flask, request, jsonify
import requests
import tempfile
import subprocess
import openai
import os

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")  # Убедитесь, что ключ установлен в переменных окружения

PROMPT = """
Проанализируй это аудио. Сформулируй краткую выжимку смысла: основная тема, ключевые тезисы, если есть инсайды или идеи — тоже выдели. Пиши в 2–4 предложениях, просто и понятно.
"""

def download_file(url):
    r = requests.get(url)
    if r.status_code == 200:
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(r.content)
        f.close()
        return f.name
    return None

def download_youtube_audio(link):
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, 'audio.%(ext)s')
    subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "-o", path, link], check=True)
    for f in os.listdir(tmp_dir):
        if f.endswith(".mp3"):
            return os.path.join(tmp_dir, f)
    return None

def transcribe(path):
    with open(path, "rb") as f:
        result = openai.Audio.transcribe("whisper-1", f)
        return result["text"]

def summarize(text):
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": text}]
    )
    return res.choices[0].message.content

@app.route("/process", methods=["POST"])
def process():
    data = request.json
    if data.get("type") == "audio":
        url = data.get("file_url")
        path = download_file(url)
        if not path:
            return jsonify({"error": "Не удалось скачать аудио"}), 400
        text = transcribe(path)
        summary = summarize(text)
        return jsonify({"summary": summary, "link": url})

    elif data.get("type") == "youtube":
        link = data.get("link")
        path = download_youtube_audio(link)
        if not path:
            return jsonify({"error": "Не удалось скачать видео"}), 400
        text = transcribe(path)
        summary = summarize(text)
        return jsonify({"summary": summary, "link": link})

    return jsonify({"error": "Неверный тип"}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
