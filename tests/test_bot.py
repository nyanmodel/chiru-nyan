import asyncio
import time
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch

import discord

from bot import ChiruBot, load_channels
from awake import app, awake


class ConfigTests(unittest.TestCase):
    def test_optional_servers_and_no_client_id(self):
        self.assertEqual(load_channels({'civ_union': '1', 'civ_union_vcstatus_channel': '2'}), {1: 2})

    def test_invalid_config(self):
        for config in ({}, {'civ_union': '1'}, {'civ_union': 'x', 'civ_union_vcstatus_channel': '2'},
                       {'civ_union': '-1', 'civ_union_vcstatus_channel': '2'},
                       {'civ_union': '1', 'civ_union_vcstatus_channel': '2',
                        'unreal': '1', 'unreal_vcstatus_channel': '3'}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                load_channels(config)

    def test_http_probe(self):
        response = app.test_client().get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'wake')

    def test_port_and_daemon(self):
        with patch.dict('os.environ', {'PORT': '12345'}), patch('awake.Thread') as thread:
            awake()
            self.assertEqual(thread.call_args.kwargs['kwargs']['port'], 12345)
            self.assertTrue(thread.call_args.kwargs['daemon'])
            thread.return_value.start.assert_called_once()


class BotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = ChiruBot({1: 2})
        self.bot.ready_at = time.monotonic() - 10
        self.member = NS(name='ねこ', guild=NS(id=1), display_avatar=NS(url='https://example.com/avatar.png'))
        self.alert = NS(guild=NS(id=1), send=AsyncMock())
        self.bot.get_channel = Mock(return_value=self.alert)
        self.empty = NS(channel=None)
        self.voice = NS(channel=NS(id=3, name='雑談'))

    async def asyncTearDown(self):
        await self.bot.close()

    async def test_intents_and_help(self):
        self.assertTrue(self.bot.intents.message_content)
        self.assertTrue(self.bot.intents.voice_states)
        self.bot._connection.user = self.member
        ctx = NS(send=AsyncMock())
        await self.bot.get_command('help').callback(ctx)
        embed = ctx.send.call_args.kwargs['embed']
        self.assertIn('にゃん！', embed.description)
        self.assertEqual(embed.author.icon_url, self.member.display_avatar.url)

    async def test_join_and_leave(self):
        with patch('bot.NOTIFICATION_INTERVAL_SECONDS', 0):
            await self.bot.on_voice_state_update(self.member, self.empty, self.voice)
            await self.bot.on_voice_state_update(self.member, self.voice, self.empty)
        embeds = [call.kwargs['embed'] for call in self.alert.send.call_args_list]
        self.assertIn('にいるよ', embeds[0].description)
        self.assertIn('退出', embeds[1].description)
        self.assertIsNotNone(embeds[0].timestamp.tzinfo)
        self.assertEqual(embeds[0].author.icon_url, self.member.display_avatar.url)

    async def test_no_notification_for_move_or_mute(self):
        await self.bot.on_voice_state_update(self.member, self.voice, NS(channel=NS(id=4, name='別室')))
        await self.bot.on_voice_state_update(self.member, self.voice, self.voice)
        self.alert.send.assert_not_awaited()

    async def test_unknown_guild_missing_or_wrong_channel(self):
        self.member.guild.id = 9
        await self.bot.on_voice_state_update(self.member, self.empty, self.voice)
        self.bot.get_channel.assert_not_called()
        self.member.guild.id = 1
        for channel in (None, NS(guild=NS(id=1)), NS(guild=NS(id=9), send=AsyncMock())):
            self.bot.get_channel.return_value = channel
            with self.assertLogs('bot', level='WARNING'):
                await self.bot.on_voice_state_update(self.member, self.empty, self.voice)
        self.alert.send.assert_not_awaited()

    async def test_startup_disconnect_and_resume_suppression(self):
        self.bot.change_presence = AsyncMock()
        await self.bot.on_ready()
        await self.bot.on_voice_state_update(self.member, self.empty, self.voice)
        await self.bot.on_disconnect()
        await self.bot.on_voice_state_update(self.member, self.empty, self.voice)
        await self.bot.on_resumed()
        await self.bot.on_voice_state_update(self.member, self.empty, self.voice)
        self.alert.send.assert_not_awaited()

    async def test_concurrent_notifications_are_spaced(self):
        sent_at = []
        async def send(**kwargs):
            sent_at.append(time.monotonic())
            await asyncio.sleep(0.01)
        self.alert.send.side_effect = send
        with patch('bot.NOTIFICATION_INTERVAL_SECONDS', 0.03):
            await asyncio.gather(*(self.bot.on_voice_state_update(self.member, self.empty, self.voice)
                                   for _ in range(3)))
        self.assertEqual(len(sent_at), 3)
        self.assertTrue(all(b - a >= 0.03 for a, b in zip(sent_at, sent_at[1:])))

    async def test_send_failure_does_not_block_next_notification(self):
        self.alert.send.side_effect = [discord.Forbidden(NS(status=403, reason='Forbidden'), 'no permission'), None]
        with patch('bot.NOTIFICATION_INTERVAL_SECONDS', 0):
            with self.assertLogs('bot', level='ERROR'):
                await self.bot.on_voice_state_update(self.member, self.empty, self.voice)
            await self.bot.on_voice_state_update(self.member, self.empty, self.voice)
        self.assertEqual(self.alert.send.await_count, 2)

    async def test_greeting_commands_and_bot_ignore(self):
        message = NS(author=NS(name='ねこ', bot=False), content='にゃん！', channel=NS(send=AsyncMock()))
        self.bot.process_commands = AsyncMock()
        await self.bot.on_message(message)
        self.assertTrue(message.channel.send.call_args.args[0].startswith('ねこさん'))
        self.bot.process_commands.assert_awaited_once_with(message)
        message.author.bot = True
        await self.bot.on_message(message)
        self.assertEqual(message.channel.send.await_count, 1)
        self.assertEqual(self.bot.process_commands.await_count, 1)


if __name__ == '__main__':
    unittest.main()
