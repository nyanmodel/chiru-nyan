import { REST, Routes, SlashCommandBuilder } from 'discord.js';
import { config } from './config.mjs';

const { token, guildId } = config();
const rest = new REST({ version: '10' }).setToken(token);
const application = await rest.get(Routes.oauth2CurrentApplication());
// POST upserts only these names; do not replace unrelated guild commands.
for (const [name, description] of [
  ['録音テスト開始', '参加中のVCを最大30秒録音し、このチャンネルに音声を添付します'],
  ['録音テスト終了', '録音テストを終了し、音声を回収します'],
]) {
  await rest.post(Routes.applicationGuildCommands(application.id, guildId), {
    body: new SlashCommandBuilder().setName(name).setDescription(description).toJSON(),
  });
}
console.log('テストサーバーに録音コマンドを登録しました。');
