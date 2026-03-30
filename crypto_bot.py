import discord
import requests
import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from deep_translator import GoogleTranslator

TOKEN = os.environ.get("DISCORD_TOKEN")
CMC_API_KEY = os.environ.get("CMC_API_KEY")
TELEGRAM_API_ID = int(os.environ.get("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH")
TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION")

GUILD_NAME = "The Crypto Bro"
DISCORD_ACTUS_CHANNEL = "actus"

TELEGRAM_CHANNELS = {
    "@WalterBloomberg": "📢 **Walter Bloomberg**",
    "@watcherguru": "👁️ **Watcher Guru**"
}

intents = discord.Intents.default()
discord_client = discord.Client(intents=intents)
telegram_client = TelegramClient(
    StringSession(TELEGRAM_SESSION),
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH
)

def translate_to_french(text):
    try:
        return GoogleTranslator(source="auto", target="fr").translate(text)
    except Exception as e:
        print(f"⚠️ Erreur traduction: {e}")
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
    data = r.json()
    return round(data["data"]["btc_dominance"], 1)

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

async def update_channels():
    await discord_client.wait_until_ready()

    guild = discord.utils.get(discord_client.guilds, name=GUILD_NAME)
    if not guild:
        print("❌ Serveur Discord introuvable")
        return

    names = ["bitcoin-price", "ethereum-price", "btc-dominance", "fear-greed"]
    channels = {}

    for name in names:
        ch = discord.utils.get(guild.channels, name=name)
        if ch is None:
            ch = await guild.create_voice_channel(name)
        channels[name] = ch

    prev_btc = None

    while True:
        try:
            btc, eth = get_crypto_data()
            btc_change = ((btc - prev_btc) / prev_btc * 100) if prev_btc else 0
            prev_btc = btc
            dom = get_dominance()
            fg, fg_class = get_fear_greed()

            await channels["bitcoin-price"].edit(name=make_channel_name("BTC", btc, btc_change))
            await channels["ethereum-price"].edit(name=make_channel_name("ETH", eth, 0))

            dom_dot = "🟢" if dom >= 50 else "🔴"
            await channels["btc-dominance"].edit(name=f"{dom_dot}BTC-Dom-{dom}%")

            if fg >= 60:
                fg_dot = "🟢"
            elif fg <= 40:
                fg_dot = "🔴"
            else:
                fg_dot = "🟡"
            await channels["fear-greed"].edit(name=f"{fg_dot}F&G-{fg}-{fg_class}")

            print(f"✅ MAJ BTC={btc:,.0f} | Dom={dom}% | F&G={fg}")

        except Exception as e:
            print(f"❌ Erreur prix: {e}")

        await asyncio.sleep(300)

async def poll_telegram():
    await discord_client.wait_until_ready()

    guild = discord.utils.get(discord_client.guilds, name=GUILD_NAME)
    if not guild:
        print("❌ Serveur introuvable")
        return

    actus_channel = discord.utils.find(
        lambda c: DISCORD_ACTUS_CHANNEL.lower() in c.name.lower(),
        guild.text_channels
    )

    if not actus_channel:
        print("❌ Channel 'actus' introuvable")
        return

    # Mémorise le dernier ID de message pour chaque canal
    last_ids = {}

    for channel_username in TELEGRAM_CHANNELS:
        try:
            entity = await telegram_client.get_entity(channel_username)
            async for message in telegram_client.iter_messages(entity, limit=1):
                last_ids[channel_username] = message.id
            print(f"✅ Dernier ID mémorisé pour {channel_username} : {last_ids[channel_username]}")
        except Exception as e:
            print(f"❌ Erreur init {channel_username}: {e}")
            last_ids[channel_username] = 0

    print("👀 Polling Telegram actif (toutes les 60 secondes)")

    while True:
        await asyncio.sleep(60)

        for channel_username, label in TELEGRAM_CHANNELS.items():
            try:
                entity = await telegram_client.get_entity(channel_username)
                username = channel_username.strip("@")

                async for message in telegram_client.iter_messages(entity, limit=10):
                    if message.id <= last_ids.get(channel_username, 0):
                        break

                    if not message.text and not message.photo:
                        continue

                    translated = translate_to_french(message.text) if message.text else ""
                    post_link = f"https://t.me/{username}/{message.id}"
                    content = f"{label}\n\n{translated}\n\n🔗 [Voir la source]({post_link})"

                    if message.photo:
                        path = await message.download_media()
                        with open(path, 'rb') as f:
                            await actus_channel.send(content=content, file=discord.File(f))
                        if os.path.exists(path):
                            os.remove(path)
                    else:
                        await actus_channel.send(content)

                    print(f"✅ Nouveau message {channel_username} envoyé")

                # Met à jour le dernier ID
                async for message in telegram_client.iter_messages(entity, limit=1):
                    last_ids[channel_username] = message.id

            except Exception as e:
                print(f"❌ Erreur polling {channel_username}: {e}")

@discord_client.event
async def on_ready():
    print(f"🤖 Connecté : {discord_client.user}")
    asyncio.create_task(update_channels())
    asyncio.create_task(poll_telegram())

async def main():
    await telegram_client.connect()

    if not await telegram_client.is_user_authorized():
        print("❌ Session Telegram invalide")
        return

    print("✅ Telegram connecté")
    asyncio.create_task(telegram_client.run_until_disconnected())
    await discord_client.start(TOKEN)

asyncio.run(main())
