from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "wake"

def run():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

def awake():
    t = Thread(target=run, daemon=True)
    t.start()