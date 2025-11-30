import discord
from discord.ext import commands
import random
import os
import re
import json
import sqlite3
from datetime import datetime, timedelta
from awake import awake

TOKEN = os.environ['MY_TOKEN']
CLIENT_ID = os.environ['MY_CLIENT_ID']

civ_union = os.environ['civ_union']
civ_vcstatus_channel = os.environ['civ_union_vcstatus_channel']

unreal = os.environ['unreal']
unreal_vcstatus_channel = os.environ['unreal_vcstatus_channel']

unreal19 = os.environ['unreal19']
unreal19_vcstatus_channel = os.environ['unreal19_vcstatus_channel']

# 入退室関数発火時のサーバ別コメント
access_ignition_comment = dict([
    (int(civ_union), "CivVC発火"), 
    (int(unreal), "UNREALVC発火"), 
    (int(unreal19), "UNREAL19VC発火")])

# 通知チャンネル辞書
inform_channel = dict([
    (int(civ_union), int(civ_vcstatus_channel)), 
    (int(unreal), int(unreal_vcstatus_channel)), 
    (int(unreal19), int(unreal19_vcstatus_channel))])

bot = commands.Bot(command_prefix='~',help_command=None)
greetarray = ["さん、こんにちは〜だよ！","さん、調子はどお？","さん、猫は好きですか？","さんにはあんまり返事したくないんだよね","さん、大好き！","さん、元気ですか？"]

@bot.event
async def on_ready():
    print("Chiru-Nyan! is ready!")
    print(bot.user.name)
    print(bot.user.id)
    print(discord.__version__)
    print('------')
    await bot.change_presence(activity=discord.Game(name="Python"))

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        color=0x53BBD3,
        description='''
        準備中なのです。
        ''')
    embed.set_author(name="Chiru-Nyan! Help", icon_url=bot.user.avatar_url)
    embed.set_footer(text=f'Childa BUNKYO 2025', icon_url="https://cdn.discordapp.com/app-icons/640478526507581440/203c3aeb1ea79c93ddb5efd9cb79ac11.png")
    await ctx.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author.bot:
        return 

    if message.content == "にゃん！":
        content = message.author.name + random.choice(greetarray)
        await message.channel.send(content)

    await bot.process_commands(message)


@bot.event
async def on_voice_state_update(member, before, after):
    print("VCUpdate発火")

    if(before.channel == after.channel):
        return

    # ログにどのサーバが発火したか残す
    server_ignition_comment = access_ignition_comment.get(member.guild.id, '登録されていないサーバーです')
    print(server_ignition_comment)

    # member.guild.idに「int(サーバ名)」が入ってくる
    # member.guild.idに応じた通知チャンネルに投稿
    alert_channel = bot.get_channel(inform_channel.get(member.guild.id, '登録されていないサーバーです'))

    if before.channel is None: 
        embed = discord.Embed(
            timestamp=datetime.utcnow(),
            color=0x00ff00,
            description=f':inbox_tray: **{member.name}** が :loud_sound: `{after.channel.name}` にいるよ！みんなも参加、どう？')
        embed.set_author(name=member.name, icon_url=member.avatar_url)
    elif after.channel is None: 
        embed = discord.Embed(
            timestamp=datetime.utcnow(),
            color=0xff0000,
            description=f':outbox_tray: **{member.name}** が :loud_sound: `{before.channel.name}` から退出だ！おやすみなさいかな？')
        embed.set_author(name=member.name, icon_url=member.avatar_url)
    await alert_channel.send(embed = embed)

awake()
bot.run(TOKEN)