# ちるにゃん！

Discordの「にゃん！」への挨拶、`~help`、ボイスチャンネルの入退室通知を行います。
VC間の移動・ミュート変更は通知しません。接続準備中および接続・再接続後5秒間は
入退室通知を抑制します（この間の通常の入退室も通知されません）。
同じサーバーの通知は前回の送信完了から0.5秒以上空けます。
通知件数の集約や永続保存は行いません。

## 設定と起動

Python 3.11以上を使用します。

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python bot.py
```

実行前に以下の環境変数を設定してください。`.env`ファイルは自動読込しません。

| 環境変数 | 内容 |
| --- | --- |
| `MY_TOKEN` | Botトークン（必須） |
| `civ_union` / `civ_union_vcstatus_channel` | サーバーID / 通知先チャンネルID |
| `unreal19` / `unreal19_vcstatus_channel` | サーバーID / 通知先チャンネルID |
| `unreal` / `unreal_vcstatus_channel` | サーバーID / 通知先チャンネルID（旧ローカル版用） |
| `PORT` | HTTP待受ポート（既定8080） |

サーバー設定は使用する組だけ指定し、少なくとも1組が必要です。
既存環境に`unreal`の設定が残っている場合は、そのサーバーでも通知が有効になります。
使わない組は両方の変数を削除してください。`MY_CLIENT_ID`は不要です。

**discord.py 1.xからの更新時:** Discord Developer Portal → 対象アプリ → Bot →
Privileged Gateway Intentsで **Message Content Intent** を有効にしてください。
「にゃん！」とプレフィックスコマンドに必要です。Server Members Intentは不要です。
Botには通知先の「チャンネルを見る」「メッセージを送信」「埋め込みリンク」の権限を付与します。

ローカルも`python bot.py`を使用します。Git管理外の`bot-local.py`は同じ実装を呼ぶ互換入口です。
HTTPの`/`はプロセスの疎通確認用で、Discordの接続状態や常時稼働を保証しません。
Bot終了時はHTTPスレッドも終了します。Flaskの組込サーバーを使用しています。

## 検証

```sh
python -m unittest discover -s tests -v
python -m pip check
```

テストはDiscordへの接続・投稿を行いません。デプロイ後に挨拶、`~help`、
入退室通知を実サーバーで確認してください。録音実験は`experiments/voice-recording/`の独立した実装です。

更新の根拠: [discord.py 2.x移行ガイド](https://discordpy.readthedocs.io/en/stable/migrating.html)、
[Gateway Intents](https://discordpy.readthedocs.io/en/stable/intents.html)、
[discord.py配布情報](https://pypi.org/project/discord.py/)、[Flask配布情報](https://pypi.org/project/Flask/)。
