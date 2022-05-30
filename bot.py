import discord
import random
import os
from discord.ext import commands
from datetime import datetime, timedelta

TOKEN = os.environ['MY_TOKEN']
CLIENT_ID = os.environ['MY_CLIENT_ID']
civ_channel = os.environ['inform_channel']
unreal_vcstatus_channel = os.environ['unreal_vcstatus_channel']
civ_union = os.environ['civ_union']
unreal = os.environ['unreal']

bot = commands.Bot(command_prefix='~',help_command=None)
greetarray = ["さん、こんにちわだよ","さん、調子はどお？","さん、猫は好きですか？","さんにはあんまり返事したくないんだよね","さん、大好き！","さん、元気ですか？"]

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
        description='''**にゃん！**
            応答します。

            **~addevent**
            イベントを登録します。コマンドの後に``イベント名 年 月 日``を入力してください。

            **~countdown**
            登録したイベントまでの日数を表示します。コマンドの後に登録したイベント名を入力してください。

            **~eventlist**
            登録したイベントを一覧表示します。

            **その他**
            VC入室時に通知を送ったり…etc")''')
    embed.set_author(name="Chiru-Nyan! Help", icon_url=bot.user.avatar_url)
    embed.set_footer(text=f'This Bot is Written by Childa BUNKYO / 2022', icon_url="https://cdn.discordapp.com/app-icons/640478526507581440/203c3aeb1ea79c93ddb5efd9cb79ac11.png")
    await ctx.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author.bot:
        return 
    if message.content == "にゃん！":
        content = message.author.name + random.choice(greetarray)
        await message.channel.send(content)
    elif message.content == "おはよう":
        await message.channel.send("おはようだよ！！")
    await bot.process_commands(message)
    
@bot.event
async def on_voice_state_update(member, before, after):
    print("VCUpdate発火")
    # Civ連合
    if member.guild.id == int(civ_union) and (before.channel != after.channel):
        print("CivVC発火")
        alert_channel = bot.get_channel(int(civ_channel))

        if before.channel is None: 
            embed = discord.Embed(
                timestamp=datetime.utcnow(),
                color=0x00ff00,
                description=f':inbox_tray: **{member.name}** が :loud_sound: `{after.channel.name}` にいるよ！みんなも参加、どう？')
            embed.set_author(name=member.name, icon_url=member.avatar_url)
            await alert_channel.send(embed = embed)
        elif after.channel is None: 
            embed = discord.Embed(
                timestamp=datetime.utcnow(),
                color=0xff0000,
                description=f':outbox_tray: **{member.name}** が :loud_sound: `{before.channel.name}` から退出だ！おやすみなさいかな？')
            embed.set_author(name=member.name, icon_url=member.avatar_url)
            await alert_channel.send(embed = embed)

    # UNREAL
    if member.guild.id == int(unreal) and (before.channel != after.channel):
        print("UNREALVC発火")
        alert_channel = bot.get_channel(int(unreal_vcstatus_channel))

        if before.channel is None: 
            embed = discord.Embed(
                timestamp=datetime.utcnow(),
                color=0x00ff00,
                description=f':inbox_tray: **{member.name}** が :loud_sound: `{after.channel.name}` にいるよ！みんなも参加、どう？')
            embed.set_author(name=member.name, icon_url=member.avatar_url)
            await alert_channel.send(embed = embed)
        elif after.channel is None: 
            embed = discord.Embed(
                timestamp=datetime.utcnow(),
                color=0xff0000,
                description=f':outbox_tray: **{member.name}** が :loud_sound: `{before.channel.name}` から退出だ！おやすみなさいかな？')
            embed.set_author(name=member.name, icon_url=member.avatar_url)
            await alert_channel.send(embed = embed)

bot.run(TOKEN)