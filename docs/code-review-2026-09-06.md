# 既存botのレビュー（2026-09-06）

対象：`bot.py`、`awake.py`、`requirements.txt`、`Dockerfile`、Git管理外の `bot-local.py`。
本番実行ファイルは変更していません。静的レビューであり、現在Renderにデプロイされているコミット・設定は未確認です。

## 修正すべき点

### [P1] 起動直後の通知抑制が上書きされている — bot.py:40–58, 85–86

`on_ready` と `on_voice_state_update` がそれぞれ2回 `@bot.event` で登録されています。
後の定義が前の定義を上書きするので、`bot_start_time` の設定と5秒ガードがどちらも実行されません。
再接続などでイベントが集中したとき、意図した抑制が一切働きません。
各イベントを1つに統合し、経過時間には `time.monotonic()` を使ってください。
なお「起動後5秒を捨てる」方式は正規の入退室も捨てるため、再接続時に何を通知したいか決める必要があります。

### [P2] 各イベント内のsleepは通知の間隔制限にならない — bot.py:120–122

イベントハンドラは並行に動くため、同時に20件来ると20件とも0.5秒後に送信へ進みます。
`asyncio.sleep(0.5)` ではコメントの「大量リクエスト対策」になりません。
通知をまとめたいならサーバー単位のキューと1つの送信タスク、あるいは短時間のイベント集約を使います。
Discord側のレート制限処理と、ユーザー向け通知を減らす処理は別です。

### [P2] 依存更新はコードとセットで行う必要がある — requirements.txt:1, bot.py:34, 68, 109, 115

`discord.py==1.7.3` のまま音声受信を追加する土台にはできません。
2.xへバージョン指定だけを変えると `commands.Bot` の必須 `intents` がなく起動に失敗し、
さらに旧 `avatar_url` は削除されているためEmbed生成も壊れます。
2.x対応時は `Intents` を明示し、`display_avatar.url` へ変更してください。
`にゃん！` と `~` コマンドを維持する場合、コード側とDeveloper Portal側のMessage Content Intent設定を確認します。
`datetime.utcnow()` も `datetime.now(timezone.utc)` などへ更新するのが適切です。
DockerのPython 3.11と旧依存の再ビルド互換性は、隔離環境で確認する必要があります。

### [P2] ローカル版はVC移動と未登録サーバーで例外になる — bot-local.py:84–98

別VCへの移動では `before.channel` と `after.channel` の両方に値があるため、
どちらの分岐も通らず未定義の `embed` を送ろうとして `UnboundLocalError` になります。
未登録サーバーや見つからない通知先では `alert_channel` が `None` になり、`.send()` が失敗します。
本番版には両方のガードがあります。ローカル専用コピーの維持をやめ、同じファイルを環境変数で切り替えるのが確実です。

### [P2] 無料Renderのディスクは録音の保存先として永続ではない — 新機能の設計

Macの停止から独立している点はそのとおりですが、Render自体のスリープ・再起動・再デプロイは別の障害要因です。
HTTPサーバーを立てるだけでは常時稼働になりません。無料枠のローカル保存を処理待ちキューの正本にすると音声が失われます。
今回の実験は終了後にDiscord添付で回収します。本運用は外部ストレージへ分割保存し、永続ジョブとしてMacが取得する形が必要です。

## 小さな整理候補

- `CLIENT_ID` は未使用なのに必須環境変数です。不足すると機能に関係なく起動に失敗します（bot.py:11）。
- `awake.py:12` の8080固定は `PORT` 環境変数優先へ。現在の8080が必ず失敗するという指摘ではなく、Renderの契約に合わせる改善です。
- `awake.py` のFlask開発サーバーとbotの生存状態は連動していません。bot接続断中もHTTP 200になるため、疎通監視に利用するなら接続状態を返す必要があります。
- `Janome` は管理対象Pythonコードに利用箇所が見つかりません。不要なら依存から外します。
- `__pycache__/awake.cpython-313.pyc` が既にGit管理されています。`.gitignore` 追加だけでは既存追跡は外れないため、別途インデックスから除外してください。
- 未使用import・古いコメント・固定年号は、上記の動作不具合を直す際に整理できます。

## 推奨する作業順

1. 今回の独立した録音実験で、Render上のDAVE受信・音声品質を確認。
2. Python botのイベント重複を修正し、依存とIntentsをまとめて更新。既存の挨拶・入退室通知を回帰確認。
3. 録音実装の採用方式を決定し、永続保存・Mac側の処理待ち・Whisperを追加。

## 根拠資料

- [discord.py 2.0移行ガイド](https://discordpy.readthedocs.io/en/stable/migrating.html)
- [Gateway Intents](https://discordpy.readthedocs.io/en/stable/intents.html)
- [Render無料枠](https://render.com/docs/free)
- [Render Web ServicesのPORT](https://render.com/docs/web-services)
