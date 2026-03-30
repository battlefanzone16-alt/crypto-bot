import discord
import requests
import asyncio
import os
from telethon import TelegramClient, events
from deep_translator import GoogleTranslator

TOKEN = os.environ.get("DISCORD_TOKEN")
CMC_API_KEY = os.environ.get("CMC_API_KEY")
TELEGRAM_API_ID = int(os.environ.get("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH")
GUILD_NAME = "The Crypto Bro"
TELEGRAM_CHANNEL = "WalterBloomberg"
DISCORD_ACTUS_CHANNEL = "actus"

def get_crypto_data():
    url = "https://api.coinbase.com/v2/exchange-rates?currency=USD"
    r = requests.get(url)
    data = r.json()
    rates = data["data"]["rates"]
    btc_price = 1 / float(rates["BTC"])
    eth_price = 1 / float(rates["ETH"])
    return btc_price, eth_price

def get_dominance():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    r = requests.get("https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest", headers=headers)
    data = r.json()
    return round(data["data"]["btc_dominance"], 1)

def get_fear_greed():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    r = requests.get("https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest", headers=headers)
    data = r.json()
    value = int(data["data"]["value"])
    classification = data["data"]["value_classification"]
    return value, classification

def translate_to_french(text):
    try:
        return GoogleTranslator(source="auto", target="fr").translate(text)
    except:
        return text

def make_channel_name(symbol, price, change):
    arrow = "▲" if change >= 0 else "▼"
    dot = "🟢" if change >= 0 else "🔴"
    return f"{dot}{symbol}-${price:,.0f}-{arrow}{abs(change):.1f}%"

intents = discord.Intents.default()
discord_client = discord.Client(intents=intents)
telegram_client = TelegramClient("session", TELEGRAM_API_ID, TELEGRAM_API_HASH)

async def update_channels():
    await discord_client.wait_until_ready()

    guild = None
    for g in discord_client.guilds:
        if g.name == GUILD_NAME:
            guild = g
            break

    if guild is None:
        print(f"Serveur introuvable : {GUILD_NAME}")
        return

    channel_names = ["bitcoin-price", "ethereum-price", "btc-dominance", "fear-greed"]
    channels = {}
    for name in channel_names:
        ch = discord.utils.get(guild.channels, name=name)
        if ch is None:
            ch = await guild.create_voice_channel(name)
        channels[name] = ch

    prev_btc = None

    while not discord_client.is_closed():
        try:
            btc_price, eth_price = get_crypto_data()
            btc_change = ((btc_price - prev_btc) / prev_btc * 100) if prev_btc else 0
            prev_btc = btc_price
            dominance = get_dominance()
            fear_value, fear_class = get_fear_greed()

            await channels["bitcoin-price"].edit(name=make_channel_name("BTC", btc_price, btc_change))
            await channels["ethereum-price"].edit(name=make_channel_name("ETH", eth_price, 0))

            dom_dot = "🟢" if dominance >= 50 else "🔴"
            await channels["btc-dominance"].edit(name=f"{dom_dot}BTC-Dom-{dominance}%")

            if fear_value >= 60:
                fg_dot = "🟢"
            elif fear_value <= 40:
                fg_dot = "🔴"
            else:
                fg_dot = "🟡"
            await channels["fear-greed"].edit(name=f"{fg_dot}F&G-{fear_value}-{fear_class}")

            print(f"Mis à jour ! BTC=${btc_price:,.0f} Dom={dominance}% F&G={fear_value}")

        except Exception as e:
            print(f"Erreur prix: {e}")

        await asyncio.sleep(300)

async def watch_telegram():
    await discord_client.wait_until_ready()

    guild = None
    for g in discord_client.guilds:
        if g.name == GUILD_NAME:
            guild = g
            break

    actus_channel = discord.utils.get(guild.text_channels, name=DISCORD_ACTUS_CHANNEL)

    @telegram_client.on(events.NewMessage(chats=TELEGRAM_CHANNEL))
    async def handler(event):
        if event.message.text:
            translated = translate_to_french(event.message.text)
            await actus_channel.send(f"📢 **Walter Bloomberg**\n\n{translated}")
            print(f"Nouveau tweet posté dans #actus")

    await telegram_client.run_until_disconnected()

@discord_client.event
async def on_ready():
    print(f"Bot connecté : {discord_client.user}")
    discord_client.loop.create_task(update_channels())
    discord_client.loop.create_task(watch_telegram())

async def main():
    await telegram_client.start()
    await discord_client.start(TOKEN)

asyncio.run(main())
