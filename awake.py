from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "wake"

def run():
    app.run(host='0.0.0.0', port=8080)

def awake():
    t = Thread(target=run)
    t.start()