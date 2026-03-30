import discord
import requests
import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from deep_translator import GoogleTranslator

# ===== ENV =====
TOKEN = os.environ.get("DISCORD_TOKEN")
CMC_API_KEY = os.environ.get("CMC_API_KEY")
TELEGRAM_API_ID = int(os.environ.get("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH")
TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION")

GUILD_NAME = "The Crypto Bro"
TELEGRAM_CHANNEL = "@WalterBloomberg"
DISCORD_ACTUS_CHANNEL = "actus"

# ===== DISCORD =====
intents = discord.Intents.default()
discord_client = discord.Client(intents=intents)

# ===== TELEGRAM =====
telegram_client = TelegramClient(
    StringSession(TELEGRAM_SESSION),
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH
)

# ===== UTILS =====
def translate_to_french(text):
    try:
        return GoogleTranslator(source="auto", target="fr").translate(text)
    except Exception as e:
        print(f"Erreur traduction: {e}")
        return text

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
    return round(r.json()["data"]["btc_dominance"], 1)

def get_fear_greed():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    r = requests.get("https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest", headers=headers)
    data = r.json()["data"]
    return int(data["value"]), data["value_classification"]

def make_channel_name(symbol, price):
    return f"{symbol}-${price:,.0f}"

# ===== UPDATE PRIX =====
async def update_channels():
    await discord_client.wait_until_ready()

    guild = discord.utils.get(discord_client.guilds, name=GUILD_NAME)
    if not guild:
        print("❌ Serveur Discord introuvable")
        return

    channels = {}
    names = ["bitcoin-price", "ethereum-price", "btc-dominance", "fear-greed"]

    for name in names:
        ch = discord.utils.get(guild.channels, name=name)
        if ch is None:
            ch = await guild.create_voice_channel(name)
        channels[name] = ch

    while True:
        try:
            btc, eth = get_crypto_data()
            dom = get_dominance()
            fg, fg_class = get_fear_greed()

            await channels["bitcoin-price"].edit(name=make_channel_name("BTC", btc))
            await channels["ethereum-price"].edit(name=make_channel_name("ETH", eth))
            await channels["btc-dominance"].edit(name=f"BTC-Dom-{dom}%")
            await channels["fear-greed"].edit(name=f"F&G-{fg}-{fg_class}")

            print(f"✅ Prix MAJ BTC={btc}")

        except Exception as e:
            print(f"❌ Erreur prix: {e}")

        await asyncio.sleep(300)

# ===== TELEGRAM → DISCORD =====
async def setup_telegram_listener():
    await discord_client.wait_until_ready()

    guild = discord.utils.get(discord_client.guilds, name=GUILD_NAME)
    if not guild:
        print("❌ Serveur introuvable")
        return

    actus_channel = discord.utils.get(guild.text_channels, name=DISCORD_ACTUS_CHANNEL)
    if not actus_channel:
        print("❌ Channel 'actus' introuvable")
        return

    print("👀 Surveillance Telegram active")

    try:
        channel = await telegram_client.get_entity(TELEGRAM_CHANNEL)
    except Exception as e:
        print(f"❌ Erreur récupération Telegram: {e}")
        return

    @telegram_client.on(events.NewMessage(chats=channel))
    async def handler(event):
        print("📩 Message Telegram reçu")

        if event.message.text:
            translated = translate_to_french(event.message.text)

            try:
                await actus_channel.send(
                    f"📢 **Walter Bloomberg**\n\n{translated}"
                )
                print("✅ Envoyé sur Discord")
            except Exception as e:
                print(f"❌ Erreur envoi Discord: {e}")

# ===== EVENTS =====
@discord_client.event
async def on_ready():
    print(f"🤖 Connecté : {discord_client.user}")

    asyncio.create_task(update_channels())
    asyncio.create_task(setup_telegram_listener())

# ===== MAIN =====
async def main():
    await telegram_client.connect()

    if not await telegram_client.is_user_authorized():
        print("❌ Session Telegram invalide")
        return

    print("✅ Telegram connecté")

    # TEST DEBUG
    async for msg in telegram_client.iter_messages(TELEGRAM_CHANNEL, limit=2):
        print("🧪 TEST TELEGRAM:", msg.text)

    # Lance Telegram en fond
    asyncio.create_task(telegram_client.run_until_disconnected())

    # Lance Discord
    await discord_client.start(TOKEN)

asyncio.run(main())
