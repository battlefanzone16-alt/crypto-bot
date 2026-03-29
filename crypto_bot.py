import discord
import requests
import asyncio
import os

TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_NAME = "The Crypto Bro"

def get_crypto_data():
    url = "https://min-api.cryptocompare.com/data/pricemultifull"
    params = {
        "fsyms": "BTC,ETH",
        "tsyms": "USD"
    }
    r = requests.get(url, params=params)
    data = r.json()
    return data["RAW"]

def get_dominance():
    r = requests.get("https://api.coingecko.com/api/v3/global")
    data = r.json()
    return round(data["data"]["market_cap_percentage"]["btc"], 1)

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
        print(f"Serveur trouvé : {g.name}")
        if g.name == GUILD_NAME:
            guild = g
            break

    if guild is None:
        print(f"Serveur introuvable : {GUILD_NAME}")
        return

    channel_names = ["bitcoin-price", "ethereum-price", "btc-dominance"]
    channels = {}
    for name in channel_names:
        ch = discord.utils.get(guild.channels, name=name)
        if ch is None:
            ch = await guild.create_voice_channel(name)
        channels[name] = ch

    while not client.is_closed():
        try:
            data = get_crypto_data()
            btc_price = data["BTC"]["USD"]["PRICE"]
            btc_change = data["BTC"]["USD"]["CHANGEPCT24HOUR"]
            eth_price = data["ETH"]["USD"]["PRICE"]
            eth_change = data["ETH"]["USD"]["CHANGEPCT24HOUR"]
            dominance = get_dominance()

            await channels["bitcoin-price"].edit(name=make_channel_name("BTC", btc_price, btc_change))
            await channels["ethereum-price"].edit(name=make_channel_name("ETH", eth_price, eth_change))

            dom_dot = "🟢" if dominance >= 50 else "🔴"
            await channels["btc-dominance"].edit(name=f"{dom_dot}BTC-Dom-{dominance}%")

            print(f"Prix mis à jour !")

        except Exception as e:
            print(f"Erreur: {e}")

        await asyncio.sleep(300)

@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")
    client.loop.create_task(update_channels())

client.run(TOKEN)
