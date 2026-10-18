import asyncio
import os
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

import discord
from bot import ChiruBot, Settings, build_voice_embed


def member():
    return NS(name='猫', guild=NS(id=1), display_avatar=NS(url='https://example.com/avatar.png'))


def state(name=None):
    return NS(channel=NS(name=name) if name else None)


class SettingsTests(unittest.TestCase):
    def test_legacy_environment(self):
        env = dict(MY_TOKEN='test', civ_union='1', civ_union_vcstatus_channel='2',
                   unreal19='3', unreal19_vcstatus_channel='4')
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(Settings.from_env().notification_channels, {1: 2, 3: 4})
            for key, value in [('civ_union', 'invalid'), ('unreal19', '1'), ('MY_TOKEN', '')]:
                with patch.dict(os.environ, {key: value}):
                    with self.assertRaises(ValueError):
                        Settings.from_env()

    def test_import_without_environment_or_startup(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, '-c', 'import bot; assert not hasattr(bot, "bot")'],
            env={key: value for key, value in os.environ.items()
                 if key not in ('MY_TOKEN', 'civ_union', 'unreal19',
                                'civ_union_vcstatus_channel', 'unreal19_vcstatus_channel')},
            capture_output=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())


class EmbedTests(unittest.TestCase):
    def test_join_leave_and_ignored_events(self):
        joined = build_voice_embed(member(), state(), state('雑談'))
        self.assertIn('雑談', joined.description)
        self.assertIn('いるよ', joined.description)
        self.assertEqual(joined.author.icon_url, member().display_avatar.url)
        self.assertIsNotNone(joined.timestamp.tzinfo)
        self.assertIn('退出', build_voice_embed(member(), state('雑談'), state()).description)
        self.assertIsNone(build_voice_embed(member(), state('A'), state('B')))
        unchanged = state('A')
        self.assertIsNone(build_voice_embed(member(), unchanged, unchanged))


class BotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = ChiruBot({1: 2})

    async def asyncTearDown(self):
        await self.bot.close()

    async def test_ready_grace_and_event_filtering(self):
        self.assertTrue(self.bot.intents.message_content)
        self.assertTrue(self.bot.intents.voice_states)
        await self.bot.on_voice_state_update(member(), state(), state('A'))
        self.assertTrue(self.bot.notifications.empty())
        self.bot.change_presence = AsyncMock()
        await self.bot.on_ready()
        await self.bot.on_voice_state_update(member(), state(), state('A'))
        self.assertTrue(self.bot.notifications.empty())
        self.bot.ready_at -= 6
        await self.bot.on_voice_state_update(member(), state(), state('A'))
        await self.bot.on_voice_state_update(member(), state('A'), state())
        await self.bot.on_voice_state_update(member(), state('A'), state('B'))
        other = member()
        other.guild.id = 99
        await self.bot.on_voice_state_update(other, state(), state('A'))
        self.assertEqual(self.bot.notifications.qsize(), 2)
        await self.bot.on_ready()
        await self.bot.on_voice_state_update(member(), state(), state('A'))
        self.assertEqual(self.bot.notifications.qsize(), 2)

    async def test_serial_delivery_and_failure_recovery(self):
        times = []
        loop = asyncio.get_running_loop()
        async def send(**kwargs):
            times.append(loop.time())
            if len(times) == 1:
                raise discord.Forbidden(NS(status=403, reason='Forbidden'), 'denied')
        channel = NS(send=AsyncMock(side_effect=send))
        self.bot.wait_until_ready = AsyncMock()
        self.bot.get_channel = lambda channel_id: channel if channel_id == 2 else None
        self.bot.notification_interval = 0.02
        for channel_id in (99, 2, 2, 2):
            self.bot.notifications.put_nowait((channel_id, discord.Embed()))
        await self.bot.setup_hook()
        with self.assertLogs('bot', level='WARNING'):
            await asyncio.wait_for(self.bot.notifications.join(), 2)
        self.assertEqual(len(times), 3)
        self.assertTrue(all(b - a >= 0.018 for a, b in zip(times, times[1:])))
        await self.bot.close()
        self.assertTrue(self.bot.notification_task.cancelled())

    async def test_greeting_commands_and_bot_messages(self):
        self.bot.process_commands = AsyncMock()
        message = NS(author=NS(bot=False, name='猫'), content='にゃん！',
                     channel=NS(send=AsyncMock()))
        await self.bot.on_message(message)
        message.channel.send.assert_awaited_once()
        self.bot.process_commands.assert_awaited_once_with(message)
        message.author.bot = True
        await self.bot.on_message(message)
        self.assertEqual(self.bot.process_commands.await_count, 1)
        with patch.object(type(self.bot), 'user', new_callable=lambda: property(lambda _: member())):
            ctx = NS(send=AsyncMock())
            await self.bot.get_command('help').callback(ctx)
            ctx.send.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
