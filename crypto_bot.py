import discord
import requests
import asyncio
import os

TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_NAME = "The Crypto Bro"

def get_crypto_data():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    r = requests.get(url, params=params)
    return r.json()

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
    guild = discord.utils.get(client.guilds, name=GUILD_NAME)
    
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
            btc_price = data["bitcoin"]["usd"]
            btc_change = data["bitcoin"]["usd_24h_change"]
            eth_price = data["ethereum"]["usd"]
            eth_change = data["ethereum"]["usd_24h_change"]
            dominance = get_dominance()

            await channels["bitcoin-price"].edit(name=make_channel_name("BTC", btc_price, btc_change))
            await channels["ethereum-price"].edit(name=make_channel_name("ETH", eth_price, eth_change))
            
            dom_dot = "🟢" if dominance >= 50 else "🔴"
            await channels["btc-dominance"].edit(name=f"{dom_dot}BTC-Dom-{dominance}%")
            
        except Exception as e:
            print(f"Erreur: {e}")
        
        await asyncio.sleep(300)

@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")
    client.loop.create_task(update_channels())

client.run(TOKEN)