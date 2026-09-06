export function config(env = process.env) {
  for (const key of ['CHIRU_TEST_TOKEN', 'TEST_GUILD_ID', 'TEST_USER_ID']) {
    if (!env[key]) throw new Error(`環境変数 ${key} が必要です。`);
  }
  for (const key of ['TEST_GUILD_ID', 'TEST_USER_ID']) {
    if (!/^\d{17,20}$/.test(env[key])) throw new Error(`${key} はDiscord IDを指定してください。`);
  }
  return { token: env.CHIRU_TEST_TOKEN, guildId: env.TEST_GUILD_ID, userId: env.TEST_USER_ID };
}
