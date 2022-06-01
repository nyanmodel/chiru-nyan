import discord
import random
import os
from discord.ext import commands
from datetime import datetime, timedelta
from janome.tokenizer import Tokenizer
import os, re, json, random

TOKEN = os.environ['MY_TOKEN']
CLIENT_ID = os.environ['MY_CLIENT_ID']
civ_channel = os.environ['inform_channel']
unreal_vcstatus_channel = os.environ['unreal_vcstatus_channel']
civ_union = os.environ['civ_union']
unreal = os.environ['unreal']


# ここからコピペ / ソース： https://ai-coordinator.jp/slackbot

# 自分で育てるbotモデル作成
dict_file = "chatbot-data.json"
dic = {}
tokenizer = Tokenizer() # janome

# 辞書があれば最初に読み込む
if os.path.exists(dict_file):
    dic = json.load(open(dict_file,"r"))

# 辞書に単語を記録する
def register_dic(words):
    global dic
    if len(words) == 0: return
    tmp = ["@"]
    for i in words:
        word = i.surface
        if word == "" or word == "\r\n" or word == "\n": continue
        tmp.append(word)
        if len(tmp) < 3: continue
        if len(tmp) > 3: tmp = tmp[1:]
        set_word3(dic, tmp)
        if word == "。" or word == "？":
            tmp = ["@"]
            continue
    # 辞書を更新するごとにファイルへ保存
    json.dump(dic, open(dict_file,"w", encoding="utf-8"))

# 三要素のリストを辞書として登録
def set_word3(dic, s3):
    w1, w2, w3 = s3
    if not w1 in dic: dic[w1] = {}
    if not w2 in dic[w1]: dic[w1][w2] = {}
    if not w3 in dic[w1][w2]: dic[w1][w2][w3] = 0
    dic[w1][w2][w3] += 1

# 文章を生成する
def make_sentence(head):
    if not head in dic: return ""
    ret = []
    if head != "@": ret.append(head)
    top = dic[head]
    w1 = word_choice(top)
    w2 = word_choice(top[w1])
    ret.append(w1)
    ret.append(w2)
    while True:
        if w1 in dic and w2 in dic[w1]:
            w3 = word_choice(dic[w1][w2])
        else:
            w3 = ""
        ret.append(w3)
        if w3 == "。" or w3 == "？" or w3 == "": break
        w1, w2 = w2, w3
    return "".join(ret)

def word_choice(sel):
    keys = sel.keys()
    return random.choice(list(keys))

# botに返答させる
def make_reply(text):
    # まず単語を学習する
    if text[-1] != "。": text += "。"
    words = tokenizer.tokenize(text)
    register_dic(words)
    # 辞書に単語があれば、そこから話す
    for w in words:
        face = w.surface
        ps = w.part_of_speech.split(',')[0]
        if ps == "感動詞":
            return face + "。"
        if ps == "名詞" or ps == "形容詞":
            if face in dic: return make_sentence(face)
    return make_sentence("@")

#ここまでコピペ


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
        description='''
        準備中です。
        ''')
    embed.set_author(name="Chiru-Nyan! Help", icon_url=bot.user.avatar_url)
    embed.set_footer(text=f'Childa BUNKYO 2022', icon_url="https://cdn.discordapp.com/app-icons/640478526507581440/203c3aeb1ea79c93ddb5efd9cb79ac11.png")
    await ctx.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author.bot:
        return 
    if message.content == "にゃん！":
        content = message.author.name + random.choice(greetarray)
        await message.channel.send(content)
    else:
        if message.attachments:
            pass
        else:
            usertext = message.content
            bottext = make_reply(usertext)
            await bot.send_message(message.channel, bottext)
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