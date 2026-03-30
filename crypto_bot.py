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
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

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

# Stocke les actus de la journée
daily_news = []

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

def get_btc_levels():
    try:
        # Niveaux 24h
        r = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
        data = r.json()
        high_24h = round(float(data["highPrice"]), 0)
        low_24h = round(float(data["lowPrice"]), 0)

        # Niveaux 7 jours via klines
        r2 = requests.get("https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1d&limit=7")
        klines = r2.json()
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        high_7d = round(max(highs), 0)
        low_7d = round(min(lows), 0)

        return low_24h, high_24h, low_7d, high_7d
    except:
        return None, None, None, None

def get_ai_summary(news_list):
    try:
        if not news_list:
            return None

        news_text = "\n".join([f"- {n}" for n in news_list])

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": f"""Voici les actualités crypto du jour. Fais un résumé en français en exactement 5 points clés, chacun sur une ligne commençant par un emoji pertinent. Sois concis et informatif. Ne mets pas de titre, juste les 5 points.

Actualités :
{news_text}"""
                }]
            }
        )
        data = response.json()
        return data["content"][0]["text"]
    except Exception as e:
        print(f"❌ Erreur IA: {e}")
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

    # Supports et résistances
    low_24h, high_24h, low_7d, high_7d = get_btc_levels()
    if low_24h:
        levels_section = f"""
**🎯 Niveaux BTC**
🔴 Résistance 24h : ${high_24h:,.0f}
🟢 Support 24h : ${low_24h:,.0f}
🔴 Résistance 7j : ${high_7d:,.0f}
🟢 Support 7j : ${low_7d:,.0f}"""
    else:
        levels_section = ""

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
{levels_section}
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

async def post_ai_recap(actus_channel):
    global daily_news
    try:
        if not daily_news:
            print("⚠️ Pas d'actus aujourd'hui pour le récap IA")
            return

        print(f"🤖 Génération récap IA avec {len(daily_news)} actus...")
        summary = get_ai_summary(daily_news)

        if not summary:
            return

        paris_time = datetime.now(timezone(timedelta(hours=2)))
        date_str = paris_time.strftime("%d %B %Y")

        message = f"🤖 **Récap IA du jour — {date_str}**\n\n{summary}"
        await actus_channel.send(message)
        print("✅ Récap IA posté")

        # Remet à zéro pour le lendemain
        daily_news = []

    except Exception as e:
        print(f"❌ Erreur récap IA: {e}")

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

        # Résumé matinal à 8h
        next_8h = paris_now.replace(hour=8, minute=0, second=0, microsecond=0)
        if paris_now >= next_8h:
            next_8h += timedelta(days=1)

        # Récap IA à 20h
        next_20h = paris_now.replace(hour=20, minute=0, second=0, microsecond=0)
        if paris_now >= next_20h:
            next_20h += timedelta(days=1)

        # Attend le prochain événement
        next_event = min(next_8h, next_20h)
        wait_seconds = (next_event - paris_now).total_seconds()
        print(f"⏰ Prochain événement dans {int(wait_seconds // 3600)}h {int((wait_seconds % 3600) // 60)}min")
        await asyncio.sleep(wait_seconds)

        paris_now = datetime.now(timezone(timedelta(hours=2)))

        if paris_now.hour == 8:
            await post_summary(actus_channel, label="🌅 **Résumé matinal**")
        elif paris_now.hour == 20:
            await post_ai_recap(actus_channel)

async def poll_telegram():
    global daily_news
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

                    # Ajoute au récap IA
                    if text and len(text) > 10:
                        daily_news.append(f"[{label.replace('*', '').replace('_', '').strip()}] {text[:200]}")

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
