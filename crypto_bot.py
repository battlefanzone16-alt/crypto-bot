import discord
import requests
import asyncio
import os

TOKEN = os.environ.get("DISCORD_TOKEN")
CMC_API_KEY = os.environ.get("CMC_API_KEY")
GUILD_NAME = "The Crypto Bro"

def get_crypto_data():
    url = "https://api.coinbase.com/v2/exchange-rates?currency=USD"
    r = requests.get(url)
    data = r.json()
    rates = data["data"]["rates"]
    btc_price = 1 / float(rates["BTC"])
    eth_price = 1 / float(rates["ETH"])
    return btc_price, eth_price

def get_dominance():
    r = requests.get("https://api.coingecko.com/api/v3/global")
    data = r.json()
    return round(data["data"]["market_cap_percentage"]["btc"], 1)

def get_fear_greed():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    r = requests.get("https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest", headers=headers)
    data = r.json()
    value = int(data["data"]["value"])
    classification = data["data"]["value_classification"]
    return value, classification

def make_channel_name(symbol, price, change):
    arrow = "▲" if change >= 0 else "▼"
    dot = "🟢" if change >= 0 else "🔴"
    return f"{dot}{symbol}-${price:,.0f}-{arrow}{abs(change):.1f}%"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def update_channels():
    await client.wait_until_ready()

    guild = None
    for g in client.guilds:
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

    while not client.is_closed():
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

            print(f"Mis à jour ! BTC=${btc_price:,.0f} F&G={fear_value}")

        except Exception as e:
            print(f"Erreur: {e}")

        await asyncio.sleep(300)

@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")
    client.loop.create_task(update_channels())

client.run(TOKEN)
