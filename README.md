# Chiru-Nyan!

Discordのメッセージ応答（「にゃん！」）、`~help`、VC入退室通知を提供するBotです。
Python 3.11 / discord.py 2.7.1を使用します。

## セットアップ

```sh
python -m pip install -r requirements.txt
python bot.py
```

以下の環境変数を設定してください。トークンをリポジトリへ保存しないでください。

| 環境変数 | 内容 |
| --- | --- |
| `MY_TOKEN` | Botトークン |
| `civ_union` | 1つ目のサーバーID |
| `civ_union_vcstatus_channel` | 1つ目の通知用テキストチャンネルID |
| `unreal19` | 2つ目のサーバーID |
| `unreal19_vcstatus_channel` | 2つ目の通知用テキストチャンネルID |

既存の環境変数名は維持しています。`MY_CLIENT_ID` は不要になりました。

Discord Developer Portalで対象アプリの **Bot → Privileged Gateway Intents → Message Content Intent** を有効にしてください。
「にゃん！」への応答とプレフィックスコマンドに必要です。Server Members IntentとPresence Intentは不要です。
Botには通知先の「チャンネルを見る」「メッセージを送信」「埋め込みリンク」の権限を付与してください。

## 動作

- 起動・再接続時のREADYから5秒間はVC通知を抑制します。
- VCへの参加・退出を通知します。ミュート変更とVC間移動は通知しません。
- VC通知は共通キューで受け付け、送信処理の完了から次の送信まで0.5秒空けます。
- キューの上限は1,000件です。上限超過、通知先が見つからない場合、送信失敗はログに記録します。
- 失敗した通知は再送しません。キューはメモリ上にあり、終了時の未送信分は保持しません。
- Flaskの `/` は従来どおりポート8080で `wake` を返します。Bot終了時は同時に終了します。

## テスト

```sh
python -m unittest discover -s tests -v
```

Discordへの接続や投稿なしで、設定検証、VC通知、送信間隔、送信失敗後の継続、起動時の抑制、メッセージ応答を検証します。
実環境ではMessage Content Intentを有効にしたうえで、`~help`、「にゃん！」、VC入退室を確認してください。

動的なサーバー設定と議事録機能は、今後の設計対象です。
