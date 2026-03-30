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
        print(f"⚠️ Erreur traduction: {e}")
        return text

def get_crypto_data():
    url = "https://api.coinbase.com"
    r = requests.get(url)
    data = r.json()
    rates = data["data"]["rates"]

    btc_price = 1 / float(rates["BTC"])
    eth_price = 1 / float(rates["ETH"])

    return btc_price, eth_price

def get_dominance():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    r = requests.get(
        "https://pro-api.coinmarketcap.com",
        headers=headers
    )
    return round(r.json()["data"]["btc_dominance"], 1)

def get_fear_greed():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    r = requests.get(
        "https://pro-api.coinmarketcap.com",
        headers=headers
    )
    data = r.json()["data"]
    return int(data["value"]), data["value_classification"]

# ===== STYLE VISUEL =====
def make_channel_name(symbol, price, change):
    arrow = "▲" if change >= 0 else "▼"
    dot = "🟢" if change >= 0 else "🔴"
    return f"{dot}{symbol}-${price:,.0f}-{arrow}{abs(change):.1f}%"

# ===== UPDATE PRIX =====
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

            await channels["bitcoin-price"].edit(
                name=make_channel_name("BTC", btc, btc_change)
            )

            await channels["ethereum-price"].edit(
                name=make_channel_name("ETH", eth, 0)
            )

            dom_dot = "🟢" if dom >= 50 else "🔴"
            await channels["btc-dominance"].edit(
                name=f"{dom_dot}BTC-Dom-{dom}%"
            )

            if fg >= 60:
                fg_dot = "🟢"
            elif fg <= 40:
                fg_dot = "🔴"
            else:
                fg_dot = "🟡"

            await channels["fear-greed"].edit(
                name=f"{fg_dot}F&G-{fg}-{fg_class}"
            )

            print(f"✅ MAJ BTC={btc:,.0f} | Dom={dom}% | F&G={fg}")

        except Exception as e:
            print(f"❌ Erreur prix: {e}")

        await asyncio.sleep(300)

# ===== TELEGRAM → DISCORD (PARTIE MODIFIÉE) =====
async def setup_telegram_listener():
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

    print(f"✅ Channel trouvé : {actus_channel.name}")
    print("👀 Surveillance Telegram active")

    try:
        channel = await telegram_client.get_entity(TELEGRAM_CHANNEL)
    except Exception as e:
        print(f"❌ Erreur Telegram: {e}")
        return

    @telegram_client.on(events.NewMessage(chats=channel))
    async def handler(event):
        original_text = event.message.text
        
        # Ignorer si le message est totalement vide (ni texte ni image)
        if not original_text and not event.photo:
            return

        # Traduction si texte présent
        translated = translate_to_french(original_text) if original_text else ""
        
        # Construction du message Discord
        content = f"📢 **Walter Bloomberg**\n\n{translated}"
        if original_text:
            content += f"\n\n**Original :**\n||{original_text}||"

        try:
            if event.photo:
                # Téléchargement et envoi de l'image
                path = await event.download_media()
                with open(path, 'rb') as f:
                    await actus_channel.send(content=content, file=discord.File(f))
                if os.path.exists(path):
                    os.remove(path)
            else:
                # Envoi texte uniquement
                await actus_channel.send(content)
            print("✅ Message envoyé sur Discord")
        except Exception as e:
            print(f"❌ Erreur Discord: {e}")

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

    asyncio.create_task(telegram_client.run_until_disconnected())

    await discord_client.start(TOKEN)

asyncio.run(main())
