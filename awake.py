import os
from threading import Thread

from flask import Flask

app = Flask(__name__)


@app.route('/')
def home():
    # HTTPプロセスの疎通確認。Discordの接続状態を表すものではない。
    return "wake"


def awake():
    port = int(os.environ.get("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT は1〜65535の整数で指定してください")
    thread = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port,
                                          "use_reloader": False}, daemon=True)
    thread.start()
    return thread
