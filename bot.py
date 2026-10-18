import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
import random
import time

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)
GREETINGS = [
    "さん、こんにちは〜だよ！", "さん、調子はどお？", "さん、猫は好きですか？",
    "さんにはあんまり返事したくないんだよね", "さん、大好き！", "さん、元気ですか？",
]


@dataclass(frozen=True)
class Settings:
    token: str
    notification_channels: dict[int, int]

    @classmethod
    def from_env(cls):
        def required(name):
            value = os.environ.get(name, '').strip()
            if not value:
                raise ValueError(f'環境変数 {name} を設定してください')
            return value

        channels = {}
        for guild_key, channel_key in (
            ('civ_union', 'civ_union_vcstatus_channel'),
            ('unreal19', 'unreal19_vcstatus_channel'),
        ):
            ids = []
            for name in (guild_key, channel_key):
                try:
                    value = int(required(name))
                    if value <= 0:
                        raise ValueError
                except ValueError:
                    raise ValueError(f'環境変数 {name} には正の整数IDを設定してください') from None
                ids.append(value)
            if ids[0] in channels:
                raise ValueError('サーバーIDが重複しています')
            channels[ids[0]] = ids[1]
        return cls(token=required('MY_TOKEN'), notification_channels=channels)


def build_voice_embed(member, before, after):
    if before.channel == after.channel:
        return None
    if before.channel is None:
        color = 0x00ff00
        description = f':inbox_tray: **{member.name}** が :loud_sound: `{after.channel.name}` にいるよ！みんなも参加、どう？'
    elif after.channel is None:
        color = 0xff0000
        description = f':outbox_tray: **{member.name}** が :loud_sound: `{before.channel.name}` から退出だ！おやすみなさいかな？'
    else:
        return None
    embed = discord.Embed(timestamp=datetime.now(timezone.utc), color=color, description=description)
    embed.set_author(name=member.name, icon_url=member.display_avatar.url)
    return embed


class ChiruBot(commands.Bot):
    def __init__(self, notification_channels):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix='~', help_command=None, intents=intents)
        self.notification_channels = dict(notification_channels)
        self.notifications = asyncio.Queue(maxsize=1000)
        self.notification_task = None
        self.ready_at = None
        self.startup_grace = 5.0
        self.notification_interval = 0.5
        @self.command(name='help')
        async def help_command(ctx):
            await self.send_help_message(ctx)

    async def setup_hook(self):
        self.notification_task = asyncio.create_task(self.send_notifications())

    async def close(self):
        if self.notification_task is not None:
            self.notification_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.notification_task
        await super().close()

    async def on_ready(self):
        # READY can also occur after a reconnect; apply the grace period again.
        self.ready_at = time.monotonic()
        logger.info('Chiru-Nyan! is ready! user=%s discord.py=%s', self.user, discord.__version__)
        await self.change_presence(activity=discord.Game(name='Python'))

    async def send_help_message(self, ctx):
        embed = discord.Embed(color=0x53BBD3, description='準備中なのです。')
        embed.set_author(name='Chiru-Nyan! Help', icon_url=self.user.display_avatar.url)
        embed.set_footer(
            text='Childa BUNKYO 2025',
            icon_url='https://cdn.discordapp.com/app-icons/640478526507581440/203c3aeb1ea79c93ddb5efd9cb79ac11.png',
        )
        await ctx.send(embed=embed)

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.content == 'にゃん！':
            await message.channel.send(message.author.name + random.choice(GREETINGS))
        await self.process_commands(message)

    async def on_voice_state_update(self, member, before, after):
        if self.ready_at is None or time.monotonic() - self.ready_at < self.startup_grace:
            return
        channel_id = self.notification_channels.get(member.guild.id)
        if channel_id is None:
            return
        embed = build_voice_embed(member, before, after)
        if embed is None:
            return
        try:
            self.notifications.put_nowait((channel_id, embed))
        except asyncio.QueueFull:
            logger.warning('通知キューが満杯です：guild_id=%s', member.guild.id)

    async def send_notifications(self):
        await self.wait_until_ready()
        while True:
            channel_id, embed = await self.notifications.get()
            try:
                channel = self.get_channel(channel_id)
                if channel is None:
                    logger.warning('通知チャンネルが見つかりません：channel_id=%s', channel_id)
                else:
                    await channel.send(embed=embed)
            except discord.HTTPException:
                # One failed notification must not stop subsequent sends.
                logger.exception('通知の送信に失敗しました：channel_id=%s', channel_id)
            finally:
                self.notifications.task_done()
            await asyncio.sleep(self.notification_interval)


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    from awake import awake

    bot = ChiruBot(settings.notification_channels)
    awake()
    bot.run(settings.token)


if __name__ == '__main__':
    main()
