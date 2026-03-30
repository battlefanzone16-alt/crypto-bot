import discord
import requests
import asyncio
import os
from datetime import datetime, timezone, timedelta
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
DISCORD_CRYPTO_CHANNEL = "crypto"
BTC_ALERT_THRESHOLD = 4.9

TELEGRAM_CHANNELS = {
    "@WalterBloomberg": ("📢 **Walter Bloomberg**", True, False),
    "@watcherguru": ("👁️ **Watcher Guru**", True, False),
    "@cointelegraph": ("📰 **CoinTelegraph**", True, True),
    "@cryptoast_fr": ("🇫🇷 **CryptoAst**", False, True),
    "@journalducoin_fr": ("🇫🇷 **Journal du Coin**", False, False),
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

def get_funding_rate():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT")
        data = r.json()
        rate = float(data["lastFundingRate"]) * 100
        return round(rate, 4)
    except:
        return None

def get_volume_24h():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
        data = r.json()
        volume = float(data["quoteVolume"]) / 1_000_000_000
        return round(volume, 2)
    except:
        return None

def get_btc_change_24h():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
        data = r.json()
        return round(float(data["priceChangePercent"]), 2)
    except:
        return None

def get_eth_change_24h():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=ETHUSDT")
        data = r.json()
        return round(float(data["priceChangePercent"]), 2)
    except:
        return None

def get_gold_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F", headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return round(price, 2)
    except:
        return None

def get_brent_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/BZ=F", headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return round(price, 2)
    except:
        return None

def make_channel_name(symbol, price, change):
    arrow = "▲" if change >= 0 else "▼"
    dot = "🟢" if change >= 0 else "🔴"
    return f"{dot}{symbol}-${price:,.0f}-{arrow}{abs(change):.1f}%"

def build_summary(btc, eth, btc_change, eth_change, dom, fg, fg_class, funding, volume, gold, brent, label="📊"):
    paris_time = datetime.now(timezone(timedelta(hours=2)))
    date_str = paris_time.strftime("%A %d %B %Y")

    btc_dot = "🟢" if btc_change >= 0 else "🔴"
    eth_dot = "🟢" if eth_change >= 0 else "🔴"
    btc_arrow = "▲" if btc_change >= 0 else "▼"
    eth_arrow = "▲" if eth_change >= 0 else "▼"
    dom_dot = "🟢" if dom >= 50 else "🔴"

    if fg >= 60:
        fg_dot = "🟢"
    elif fg <= 40:
        fg_dot = "🔴"
    else:
        fg_dot = "🟡"

    if funding is not None:
        if funding > 0.01:
            f_dot = "🔴"
            f_label = "suracheté"
        elif funding < -0.01:
            f_dot = "🟢"
            f_label = "survendu"
        else:
            f_dot = "🟡"
            f_label = "neutre"
        funding_line = f"{f_dot} Funding Rate BTC : {funding}% ({f_label})"
    else:
        funding_line = "⚠️ Funding Rate indisponible"

    volume_line = f"📊 Volume 24h BTC : ${volume}B" if volume else "⚠️ Volume indisponible"
    gold_line = f"🥇 Gold : ${gold:,.2f}" if gold else "⚠️ Gold indisponible"
    brent_line = f"🛢️ Brent : ${brent:,.2f}" if brent else "⚠️ Brent indisponible"

    return f"""
{label} **Résumé des marchés — {date_str}**

**💰 Crypto**
{btc_dot} BTC : ${btc:,.0f} — {btc_arrow} {abs(btc_change):.2f}% (24h)
{eth_dot} ETH : ${eth:,.0f} — {eth_arrow} {abs(eth_change):.2f}% (24h)

**🧠 Sentiment**
{fg_dot} Fear & Greed : {fg} — {fg_class}
{dom_dot} Dominance BTC : {dom}%

**📈 Marché**
{volume_line}
{funding_line}

**🌍 Macro**
{gold_line}
{brent_line}
""".strip()

async def post_summary(actus_channel, label="📊"):
    try:
        btc, eth = get_crypto_data()
        btc_change = get_btc_change_24h() or 0
        eth_change = get_eth_change_24h() or 0
        dom = get_dominance()
        fg, fg_class = get_fear_greed()
        funding = get_funding_rate()
        volume = get_volume_24h()
        gold = get_gold_price()
        brent = get_brent_price()

        message = build_summary(btc, eth, btc_change, eth_change, dom, fg, fg_class, funding, volume, gold, brent, label)
        await actus_channel.send(message)
        print(f"✅ Résumé posté dans #actus")
    except Exception as e:
        print(f"❌ Erreur résumé: {e}")

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
    alert_sent = False

    while True:
        try:
            btc, eth = get_crypto_data()
            btc_change = ((btc - prev_btc) / prev_btc * 100) if prev_btc else 0

            if prev_btc and abs(btc_change) >= BTC_ALERT_THRESHOLD:
                if not alert_sent:
                    guild = discord.utils.get(discord_client.guilds, name=GUILD_NAME)
                    actus_channel = discord.utils.find(
                        lambda c: DISCORD_ACTUS_CHANNEL.lower() in c.name.lower(),
                        guild.text_channels
                    )
                    crypto_channel = discord.utils.find(
                        lambda c: DISCORD_CRYPTO_CHANNEL.lower() in c.name.lower(),
                        guild.text_channels
                    )
                    direction = "📈 PUMP" if btc_change > 0 else "📉 DUMP"
                    arrow = "▲" if btc_change > 0 else "▼"
                    alert_msg = f"🚨 **ALERTE BTC** 🚨\n\n{direction} de **{arrow} {abs(btc_change):.2f}%** en 5 minutes !\n💰 Prix actuel : **${btc:,.0f}**"
                    if actus_channel:
                        await actus_channel.send(alert_msg)
                    if crypto_channel:
                        await crypto_channel.send(alert_msg)
                    alert_sent = True
                    print(f"🚨 Alerte BTC envoyée : {btc_change:.2f}%")
            else:
                alert_sent = False

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

async def daily_summary():
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

    await post_summary(actus_channel, label="🚀 **Résumé de démarrage**")

    while True:
        paris_now = datetime.now(timezone(timedelta(hours=2)))
        next_8h = paris_now.replace(hour=8, minute=0, second=0, microsecond=0)
        if paris_now >= next_8h:
            next_8h += timedelta(days=1)
        wait_seconds = (next_8h - paris_now).total_seconds()
        print(f"⏰ Prochain résumé dans {int(wait_seconds // 3600)}h {int((wait_seconds % 3600) // 60)}min")
        await asyncio.sleep(wait_seconds)
        await post_summary(actus_channel, label="🌅 **Résumé matinal**")

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

    for channel_username, (label, translate, suppress) in TELEGRAM_CHANNELS.items():
        try:
            entity = await telegram_client.get_entity(channel_username)
            username = channel_username.strip("@")
            async for message in telegram_client.iter_messages(entity, limit=10):
                if message.text and len(message.text) > 5:
                    text = translate_to_french(message.text) if translate else message.text
                    post_link = f"https://t.me/{username}/{message.id}"
                    content = f"{label} _(test démarrage)_\n\n{text}\n\n🔗 [Voir la source]({post_link})"
                    await actus_channel.send(content, suppress_embeds=suppress)
                    print(f"✅ Message test {channel_username} envoyé")
                    break
        except Exception as e:
            print(f"❌ Erreur test {channel_username}: {e}")

    print("👀 Polling Telegram actif (toutes les 60 secondes)")

    while True:
        await asyncio.sleep(60)

        for channel_username, (label, translate, suppress) in TELEGRAM_CHANNELS.items():
            try:
                entity = await telegram_client.get_entity(channel_username)
                username = channel_username.strip("@")

                async for message in telegram_client.iter_messages(entity, limit=10):
                    if message.id <= last_ids.get(channel_username, 0):
                        break

                    if not message.text and not message.photo:
                        continue

                    text = translate_to_french(message.text) if translate and message.text else message.text or ""
                    post_link = f"https://t.me/{username}/{message.id}"
                    content = f"{label}\n\n{text}\n\n🔗 [Voir la source]({post_link})"

                    if message.photo:
                        path = await message.download_media()
                        with open(path, 'rb') as f:
                            await actus_channel.send(content=content, file=discord.File(f), suppress_embeds=suppress)
                        if os.path.exists(path):
                            os.remove(path)
                    else:
                        await actus_channel.send(content, suppress_embeds=suppress)

                    print(f"✅ Nouveau message {channel_username} envoyé")

                async for message in telegram_client.iter_messages(entity, limit=1):
                    last_ids[channel_username] = message.id

            except Exception as e:
                print(f"❌ Erreur polling {channel_username}: {e}")

@discord_client.event
async def on_ready():
    print(f"🤖 Connecté : {discord_client.user}")
    asyncio.create_task(update_channels())
    asyncio.create_task(daily_summary())
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
