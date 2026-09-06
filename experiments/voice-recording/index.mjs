import { createServer } from 'node:http';
import { mkdirSync, writeFileSync, statSync, rmSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import { Client, GatewayIntentBits, ChannelType, PermissionFlagsBits, MessageFlags } from 'discord.js';
import { joinVoiceChannel, entersState, VoiceConnectionStatus, EndBehaviorType, generateDependencyReport } from '@discordjs/voice';
import OpusScript from 'opusscript';
import { config } from './config.mjs';
import { WavTrack } from './wav.mjs';

const { token, guildId, userId } = config();
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates],
  allowedMentions: { parse: [] } });
const root = resolve('recordings');
const MAX_SPEAKERS = 5;
let session = null;
let shuttingDown = false;

function humans(channel) { return channel.members.filter(member => !member.user.bot); }
function report(error) { console.error(error instanceof Error ? error.message : String(error)); }
async function notify(channel, content) {
  try { await channel.send({ content, allowedMentions: { parse: [] } }); } catch (error) { report(error); }
}

function subscribe(s, member) {
  if (s.phase !== 'recording' || member.user.bot || s.tracks.has(member.id)) return;
  if (s.tracks.size >= MAX_SPEAKERS) {
    void stop(s, '参加者上限（累計5人）に達したため終了');
    return;
  }
  const path = join(s.dir, `${member.id}.wav`);
  const decoder = new OpusScript(48000, 2, OpusScript.Application.AUDIO);
  let wav;
  try { wav = new WavTrack(path); } catch (error) { decoder.delete(); throw error; }
  const stream = s.connection.receiver.subscribe(member.id, { end: { behavior: EndBehaviorType.Manual } });
  const track = { path, decoder, wav, stream, name: member.displayName };
  s.tracks.set(member.id, track);
  stream.on('data', packet => {
    if (s.phase !== 'recording') return;
    try {
      wav.append(decoder.decode(packet), Math.round(performance.now() - s.startedMono));
    } catch (error) {
      report(error);
      void stop(s, '音声の復号・デコード・保存に失敗したため終了');
    }
  });
  stream.on('error', error => {
    report(error);
    void stop(s, '音声受信エラーで終了（Renderログを確認してください）');
  });
}

// First caller owns finalization. Keep the session reserved until uploads complete.
function stop(s, reason) {
  if (s.finish) return s.finish;
  s.phase = 'stopping';
  s.finish = Promise.resolve().then(async () => {
    clearTimeout(s.timer);
    const cleanupErrors = [];
    for (const track of s.tracks.values()) {
      for (const cleanup of [() => track.stream.destroy(), () => track.wav.close(), () => track.decoder.delete()]) {
        try { cleanup(); } catch (error) { cleanupErrors.push(error); }
      }
    }
    if (s.connection.state.status !== VoiceConnectionStatus.Destroyed) s.connection.destroy();
    if (cleanupErrors.length) throw new AggregateError(cleanupErrors, '音声リソースの終了処理に失敗しました。');
    const manifest = {
      startedAt: s.startedAt, endedAt: new Date().toISOString(), reason,
      voiceChannelId: s.voice.id, textChannelId: s.text.id,
      timing: 'WAVは受信PCMを連結。無音の間隔は未補完。offsetMsは受信時刻で厳密な発話時刻ではありません。',
      tracks: [...s.tracks].map(([id, t]) => ({ userId: id, name: t.name,
        file: `${id}.wav`, pcmBytes: t.wav.bytes, packets: t.wav.packets })),
    };
    const manifestPath = join(s.dir, 'manifest.json');
    writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), { mode: 0o600 });
    const audio = [...s.tracks.values()].filter(t => t.wav.bytes > 0);
    await s.text.send({ content: `録音テスト終了：${reason}\n音声を受信できた人数：${audio.length}人。${audio.length ? '添付を再生して声が聞こえるか確認してください。' : '録音成功ではありません。VC接続・DAVE・マイク入力を確認してください。'}` });
    // Conservative ceiling and one file per message, even on higher upload tiers.
    const limit = 8_000_000;
    for (const path of [...audio.map(t => t.path), manifestPath]) {
      if (statSync(path).size > limit) throw new Error('添付サイズ上限を超えました。');
      await s.text.send({ files: [path] });
    }
    rmSync(s.dir, { recursive: true }); // delete only after every attachment succeeds
  }).catch(async error => {
    report(error);
    await notify(s.text, '終了処理または添付に失敗しました。保存済み音声は一時ディスクに残りますが、Renderの再起動で失われます。ログを確認してください。');
  }).finally(() => { if (session === s) session = null; });
  return s.finish;
}

async function start(interaction) {
  if (session) return interaction.reply({ content: '録音の準備・実行・回収中です。', flags: MessageFlags.Ephemeral });
  const member = await interaction.guild.members.fetch(interaction.user.id);
  const voice = member.voice.channel;
  if (!voice || voice.type !== ChannelType.GuildVoice) throw new Error('通常のVCに参加してから実行してください。');
  if (humans(voice).size > MAX_SPEAKERS) throw new Error('テストは5人以下のVCで実行してください。');
  const me = interaction.guild.members.me;
  if (!voice.permissionsFor(me)?.has([PermissionFlagsBits.ViewChannel, PermissionFlagsBits.Connect])) {
    throw new Error('botにVCの「チャンネルを見る」「接続」権限が必要です。');
  }
  const text = interaction.channel;
  const sendPermission = text.isThread() ? PermissionFlagsBits.SendMessagesInThreads : PermissionFlagsBits.SendMessages;
  if (!text.permissionsFor(me)?.has([PermissionFlagsBits.ViewChannel, sendPermission, PermissionFlagsBits.AttachFiles])) {
    throw new Error('botに投稿先の閲覧・送信・ファイル添付権限が必要です。');
  }
  // Recheck after the member fetch; two commands may have overlapped.
  if (session) throw new Error('録音の準備・実行・回収中です。');
  const s = { phase: 'connecting', voice, text, tracks: new Map() };
  session = s;
  try {
    await interaction.reply('🔴 録音テストのためVCに接続します。参加者全員が録音・このチャンネルへの音声添付を了承していることを確認してください。接続後、最大30秒で自動終了します。');
    s.connection = joinVoiceChannel({ guildId, channelId: voice.id,
      adapterCreator: interaction.guild.voiceAdapterCreator, selfDeaf: false, selfMute: true });
    s.connection.on('error', error => {
      report(error);
      if (s.phase === 'recording') void stop(s, 'VC接続エラーで終了');
    });
    await entersState(s.connection, VoiceConnectionStatus.Ready, 20_000);
    if (shuttingDown) throw new Error('シャットダウン中です。');
    s.dir = join(root, randomUUID());
    mkdirSync(s.dir, { recursive: true, mode: 0o700 });
    s.startedAt = new Date().toISOString();
    s.startedMono = performance.now();
    s.phase = 'recording';
    s.timer = setTimeout(() => void stop(s, '30秒の上限に到達'), 30_000);
    s.connection.on('stateChange', (_, next) => {
      if (s.phase === 'recording' && next.status !== VoiceConnectionStatus.Ready) {
        void stop(s, 'VC接続状態が変化したため終了');
      }
    });
    for (const participant of humans(voice).values()) subscribe(s, participant);
    if (!humans(voice).size) await stop(s, '全員が退出');
    else await notify(text, '🔴 録音中です。短い会話をしてください。`/録音テスト終了` でも終了できます。');
  } catch (error) {
    if (s.phase === 'recording') await stop(s, '録音開始処理中のエラー');
    else {
      if (s.connection && s.connection.state.status !== VoiceConnectionStatus.Destroyed) s.connection.destroy();
      if (session === s) session = null;
    }
    throw error;
  }
}

client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand() || !['録音テスト開始', '録音テスト終了'].includes(interaction.commandName)) return;
  try {
    if (shuttingDown || interaction.guildId !== guildId || interaction.user.id !== userId) {
      await interaction.reply({ content: 'この操作は指定したテスト利用者・サーバーのみで利用できます。', flags: MessageFlags.Ephemeral });
      return;
    }
    if (interaction.commandName === '録音テスト開始') await start(interaction);
    else {
      const s = session;
      await interaction.reply({ content: s?.phase === 'recording' ? '録音を終了して回収します。' : '録音中ではありません（接続・回収中の場合はお待ちください）。', flags: MessageFlags.Ephemeral });
      if (s?.phase === 'recording') await stop(s, 'コマンドで終了');
    }
  } catch (error) {
    report(error);
    const content = '操作に失敗しました。権限・VC参加状態とRenderログを確認してください。';
    try {
      if (interaction.replied || interaction.deferred) await interaction.followUp({ content, flags: MessageFlags.Ephemeral });
      else await interaction.reply({ content, flags: MessageFlags.Ephemeral });
    } catch (replyError) { report(replyError); }
  }
});

client.on('voiceStateUpdate', (before, after) => {
  const s = session;
  if (!s || s.phase !== 'recording' || after.guild.id !== guildId) return;
  try {
    if (after.id === client.user.id && after.channelId !== s.voice.id) {
      void stop(s, 'botが退出または移動');
    } else if (!humans(s.voice).size) {
      void stop(s, '全員が退出');
    } else if (after.channelId === s.voice.id && after.member) {
      subscribe(s, after.member);
    }
  } catch (error) { report(error); void stop(s, '参加者の録音準備に失敗'); }
});

client.on('error', report);
client.once('clientReady', () => console.log(`録音テストbot準備完了: ${client.user.tag}`));
console.log(generateDependencyReport());
const server = createServer((req, res) => {
  res.writeHead(client.isReady() ? 200 : 503, { 'Content-Type': 'text/plain' });
  res.end(client.isReady() ? 'ready' : 'starting');
});
server.listen(Number(process.env.PORT || 8080), '0.0.0.0');
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, async () => {
    if (shuttingDown) return;
    shuttingDown = true;
    const deadline = setTimeout(() => process.exit(1), 10_000);
    if (session?.phase === 'recording' || session?.finish) await stop(session, signal);
    client.destroy();
    server.close();
    clearTimeout(deadline);
  });
}
try { await client.login(token); } catch (error) {
  report(error); client.destroy(); server.close(); process.exitCode = 1;
}
