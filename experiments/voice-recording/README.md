# VC録音の実験

既存のPython botと別に動かす、最大30秒・累計5人までの録音テスト。
録音以外（Whisper・AI議事録化・Macへの自動転送）はまだ実装していません。

Node.js + `discord.js` + `@discordjs/voice` を使用します。Python全体をNode.jsへ移行する決定ではありません。
採用した `@discordjs/voice 0.19.2` の配布コードにはDAVE受信復号処理があります。
ただし音声受信はDiscordの正式な公開仕様ではなく、ライブラリも安定動作を保証していません。
実際のDiscord VC・Renderネットワークでの疎通と音声品質は実機テストが必要です。

## テストbotを準備

1. Discord Developer Portalで**別のテスト用Application/Bot**を作成します。
2. OAuth2の `bot` と `applications.commands` スコープでテストサーバーに招待します。
3. botに「チャンネルを見る」「接続」「メッセージを送信」「ファイルを添付」を許可します。
   スレッドを使う場合は「スレッドでメッセージを送信」も必要です。管理者権限は不要です。
4. 自分のユーザーIDとサーバーIDをコピーし、下記の環境変数を設定します。
   Message Content / Server Membersの特権Intentはこのテストには不要です。

| 変数 | 内容 |
| --- | --- |
| `CHIRU_TEST_TOKEN` | テスト用botトークン。本番の `MY_TOKEN` は使わない |
| `TEST_GUILD_ID` | テスト対象のサーバーID |
| `TEST_USER_ID` | 開始・終了を操作できる自分のユーザーID |
| `PORT` | HTTPヘルスチェックのポート。Renderの設定を自動使用 |

## Macで実行

Node.js 22.12以上（Node 24推奨）を使用します。

```sh
cd /Users/nyanmodel/GitHub/chiru-nyan/experiments/voice-recording
npm ci --ignore-scripts
cp .env.example .env
```

`.env` を編集してから実行します（Gitでは無視されます）。

```sh
node --env-file=.env register.mjs
node --env-file=.env index.mjs
```

登録スクリプトは指定したサーバーに2つのコマンドを作成・更新します。他の名前のコマンドは削除しません。
別のMac/Renderから**同じテストトークンを同時起動しない**でください。

## Render無料枠で実行

本番サービスとは別の **Node Web Service** を作成します。リポジトリにコードをpushしてから設定します。

| 設定 | 値 |
| --- | --- |
| Runtime | Node（既存のPython Dockerfileを使用しない） |
| Root Directory | `experiments/voice-recording` |
| Build Command | `npm ci --ignore-scripts` |
| Start Command | `npm run register && npm start` |
| Health Check Path | `/` |
| Instance | Free |
| 環境変数 | 上表の3変数、および `NODE_VERSION=24.13.0` |

まずサービスURLを開いて起動を待ち、ログの「録音テストbot準備完了」を確認します。
起動時にDAVE/Opusの依存診断も表示します。DAVEは `@snazzah/davey` が検出される必要があります。
接続タイムアウトの場合は、Discord権限・音声UDPの疎通・Renderログを確認します。
テストサービス追加分もRenderのワークスペース内の無料稼働時間を消費します。

## 実機で確認する順序

録音される全員に、音声をコマンド実行先のテキストチャンネルに添付することを説明し、了承を得てから開始してください。
VC参加者より閲覧範囲が広いチャンネルへの投稿は避けてください。

1. 2人で通常のVCに入り、指定した利用者が `/録音テスト開始` を実行します。
2. 「録音中です」の通知後、それぞれ名前を話し、数秒空け、交互・同時に短く話します。
3. `/録音テスト終了` を実行し、参加者ID別のWAVと `manifest.json` が添付されることを確認します。
4. WAVをダウンロード・再生し、各ファイルで本人の声が明瞭に聞こえることを確認します。
   VCに入れただけ／ファイルができただけでは成功としません。
5. 再度開始して全員退出し、自動終了することを確認します。
6. 再度開始して放置し、30秒で終了することを確認します。
7. 途中参加・退出後の再参加・二重開始・他ユーザーからの操作・botの強制切断を試します。
   同時終了は1回だけ回収され、次の開始ができることを確認します。

## 保存形式と制限

- 音声は48kHz・16bit・ステレオWAVで、参加者ごとにディスクへ逐次書き込みます。
- **無音時間の補完・パケット並べ替え・欠落補正は未実装**です。WAVだけで話者間の時間は揃いません。
  `manifest.json` に受信時刻の相対ミリ秒、PCMのバイト位置、長さを記録します。
  受信時刻にはネットワーク遅延が含まれるため、本格的な議事録用の時刻同期は次の段階です。
- 1人あたりPCM上限5,760,000バイト。添付は1ファイルずつ8,000,000バイト以下に制限します。
  音声受信・保存エラー、6人目の録音対象、VC接続状態の変化でも終了します。
- 全添付成功後はローカルの当該録音フォルダを削除します。添付失敗時は一時保存を残して通知します。
  自動再送・長時間録音・永続ジョブ・音声の恒久保管はありません。
- Render無料枠は15分間対象の受信トラフィックがないと停止し、ローカルディスクも永続ではありません。
  Discordに接続していることだけで常時稼働を保証できません。強制終了や再起動時の音声回収も保証できません。
  終了シグナルでは回収を試みますが、長期運用には外部ストレージへの分割保存が必要です。
- 添付済み音声はDiscordに残ります。テスト終了後、必要に応じて投稿を削除してください。

## オフライン確認

```sh
npm test
node --check index.mjs
node --check register.mjs
```

合成音声のOpusエンコード→デコード→WAV保存、サイズ上限、途中保存、時刻メタデータ、設定検証をテストします。
これらはDAVEの実通信・コマンドの応答・自動退出・添付の実機テストを代替しません。

## 参照

- [discord.js Voice（DAVE依存・音声受信の制限）](https://discord.js.org/docs/packages/voice/0.19.2)
- [Render無料枠](https://render.com/docs/free)
- [Renderの永続ディスク](https://render.com/docs/disks)
