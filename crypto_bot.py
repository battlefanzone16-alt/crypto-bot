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
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

GUILD_NAME = "The Crypto Bro"
DISCORD_ACTUS_CHANNEL = "actus"
DISCORD_CRYPTO_CHANNEL = "crypto"
BTC_ALERT_THRESHOLD = 3.0

TELEGRAM_CHANNELS = {
    "@WalterBloomberg": ("📢 **Walter Bloomberg**", True, False),
    "@watcherguru": ("👁️ **Watcher Guru**", True, False),
    "@cointelegraph": ("📰 **CoinTelegraph**", True, True),
    "@cryptoast_fr": ("🇫🇷 **CryptoAst**", False, True),
    "@journalducoin_fr": ("🇫🇷 **Journal du Coin**", False, False),
}

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)
telegram_client = TelegramClient(
    StringSession(TELEGRAM_SESSION),
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH
)

recent_posts = []

def is_duplicate(text):
    now = datetime.now(timezone.utc)
    key = text[:50].lower().strip()
    for past_key, past_time in recent_posts:
        if past_key == key and (now - past_time).total_seconds() <= 300:
            return True
    return False

def add_to_recent(text):
    now = datetime.now(timezone.utc)
    key = text[:50].lower().strip()
    recent_posts.append((key, now))
    if len(recent_posts) > 50:
        recent_posts.pop(0)

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
        r = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
        data = r.json()
        high_24h = round(float(data["highPrice"]), 0)
        low_24h = round(float(data["lowPrice"]), 0)

        r2 = requests.get("https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1d&limit=7")
        klines = r2.json()
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        high_7d = round(max(highs), 0)
        low_7d = round(min(lows), 0)

        return low_24h, high_24h, low_7d, high_7d
    except:
        return None, None, None, None

def get_weekly_calendar():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", headers=headers)
        data = r.json()

        important = []
        for event in data:
            if event.get("country") == "USD" and event.get("impact") == "High":
                date_str = event.get("date", "")
                title = event.get("title", "")
                forecast = event.get("forecast", "")
                previous = event.get("previous", "")

                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    paris_dt = dt.astimezone(timezone(timedelta(hours=2)))
                    day = paris_dt.strftime("%A %d/%m")
                    time = paris_dt.strftime("%H:%M")
                except:
                    paris_dt = datetime.now()
                    day = date_str[:10]
                    time = "?"

                line = f"📌 **{day}** à {time} — {title}"
                if forecast:
                    line += f" | Prévision: `{forecast}`"
                if previous:
                    line += f" | Précédent: `{previous}`"

                important.append((paris_dt, line))

        important.sort(key=lambda x: x[0])
        return [line for _, line in important]

    except Exception as e:
        print(f"❌ Erreur calendrier: {e}")
        return []

async def get_actus_last_24h(actus_channel):
    try:
        print("📖 Lecture des messages #actus des dernières 24h...")
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        messages = []

        async for message in actus_channel.history(limit=500, after=since):
            if message.author.bot and message.content:
                content = message.content
                skip_keywords = [
                    "Résumé des marchés", "Résumé matinal", "Résumé de démarrage",
                    "Récap IA", "Calendrier éco", "ALERTE BTC", "test démarrage",
                    "Actus du jour"
                ]
                if any(kw in content for kw in skip_keywords):
                    continue
                if "Voir la source" in content or any(
                    src in content for src in ["Walter Bloomberg", "Watcher Guru", "CoinTelegraph", "CryptoAst", "Journal du Coin"]
                ):
                    lines = content.split("\n")
                    actu_lines = []
                    for line in lines:
                        if line.strip() and "Voir la source" not in line and "🔗" not in line:
                            actu_lines.append(line.strip())
                    clean_text = " ".join(actu_lines)
                    if clean_text and len(clean_text) > 20:
                        messages.append(clean_text[:1900])

        print(f"📖 {len(messages)} actus trouvées dans #actus")
        return messages

    except Exception as e:
        print(f"❌ Erreur lecture #actus: {e}")
        return []

def get_groq_summary(news_list):
    try:
        if not news_list:
            print("⚠️ Pas d'actus à résumer")
            return None

        print(f"📡 Appel API Groq avec {len(news_list)} actus...")
        news_text = "\n".join([f"- {n}" for n in news_list])

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": "Tu es un expert en crypto et finance. Tu résumes les actualités en français de façon concise et pertinente."
                    },
                    {
                        "role": "user",
                       # acienne requette
                        # "content": f"""Voici les actualités crypto et macro des dernières 24h. Fais un résumé complet en français en 1950 caractère maximum de ce que tu trouves important, chaque paragraphe commençant par un emoji pertinent, concentre toi sur ce qui pourrait avoir un impact sur le monde de la crypto et aussi d'un point de vue macro économique notamment si il y a des chiffres du jours qui sont important du genre NFP, Taux de chomage , inflation , FED etc

#Actualités :
#{news_text}"""
"content": f"""Voici les actualités crypto et macro des dernières 24h.

⚠️ IMPORTANT :
- Maximum 1500 caractères
- Format ULTRA lisible (PAS de gros paragraphes)
- Utilise des bullet points
- Va à l’essentiel (infos importantes uniquement)

📊 Structure OBLIGATOIRE :

📊 MARCHÉS
- ...

💰 CRYPTO
- ...

🌍 MACRO
- ...

⚠️ RISQUES
- ...

🧠 CONCLUSION
- 1 phrase max sur le sentiment global (bullish / bearish / neutre)

Actualités :
{news_text}"""




                        
                    }
                ],
                "max_tokens": 400,
                "temperature": 0.3
            },
            timeout=30
        )

        print(f"📡 Status HTTP Groq: {response.status_code}")
        data = response.json()
        print(f"📡 Réponse Groq: {data}")

        if "error" in data:
            print(f"❌ Erreur Groq: {data['error']}")
            return None

        text = data["choices"][0]["message"]["content"]
        print("✅ Résumé Groq généré !")
        return text.strip()

    except requests.exceptions.Timeout:
        print("❌ Timeout Groq (30s dépassé)")
        return None
    except Exception as e:
        print(f"❌ Erreur Groq inattendue: {type(e).__name__}: {e}")
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
{brent_line}{levels_section}
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

async def post_weekly_calendar(actus_channel):
    try:
        events = get_weekly_calendar()
        paris_time = datetime.now(timezone(timedelta(hours=2)))
        monday = paris_time - timedelta(days=paris_time.weekday())
        sunday = monday + timedelta(days=6)
        week_str = f"{monday.strftime('%d/%m')} au {sunday.strftime('%d/%m/%Y')}"

        if not events:
            await actus_channel.send(f"📅 **Calendrier éco US — semaine du {week_str}**\n\nAucun événement majeur cette semaine !")
            return

        content = f"📅 **Calendrier éco US — semaine du {week_str}**\n\n"
        content += "\n".join(events)
        content += "\n\n_Source : Forex Factory | Heure de Paris_"

        await actus_channel.send(content)
        print("✅ Calendrier éco posté")
    except Exception as e:
        print(f"❌ Erreur calendrier: {e}")

async def post_ai_recap(actus_channel):
    try:
        print("🤖 Démarrage récap IA Groq...")

        news_list = await get_actus_last_24h(actus_channel)

        if not news_list:
            print("⚠️ Aucune actu trouvée")
            return

        summary = get_groq_summary(news_list)

        if not summary:
            print("❌ Récap IA échoué")
            return

        paris_time = datetime.now(timezone(timedelta(hours=2)))
        date_str = paris_time.strftime("%d %B %Y")

        message = f"🤖 **Récap IA du jour — {date_str}**\n\n{summary}"

        # ✅ UNPIN ancien
        pins = await actus_channel.pins()
        for pin in pins:
            if "Récap IA du jour" in pin.content:
                try:
                    await pin.unpin()
                except:
                    pass

        # ✅ SPLIT message
        def split_message(message, max_length=2000):
            return [message[i:i+max_length] for i in range(0, len(message), max_length)]

        chunks = split_message(message)

        for i, chunk in enumerate(chunks):
            sent_message = await actus_channel.send(chunk)

            if i == 0:
                await sent_message.pin()

        print("✅ Récap IA posté + épinglé")

    except Exception as e:
        print(f"❌ Erreur récap IA: {type(e).__name__}: {e}")

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

    btc_history = []
    alert_sent = False

    while True:
        try:
            btc, eth = get_crypto_data()
            btc_history.append(btc)
            if len(btc_history) > 3:
                btc_history.pop(0)

            btc_change = ((btc - btc_history[0]) / btc_history[0] * 100) if len(btc_history) == 3 else 0

            if len(btc_history) == 3 and abs(btc_change) >= BTC_ALERT_THRESHOLD:
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
                    alert_msg = f"🚨 **ALERTE BTC** 🚨\n\n{direction} de **{arrow} {abs(btc_change):.2f}%** en 15 minutes !\n💰 Prix actuel : **${btc:,.0f}**"
                    if actus_channel:
                        await actus_channel.send(alert_msg)
                    if crypto_channel:
                        await crypto_channel.send(alert_msg)
                    alert_sent = True
                    print(f"🚨 Alerte BTC envoyée : {btc_change:.2f}%")
            else:
                alert_sent = False

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

    # Test récap IA au démarrage
    print("🤖 Test récap IA Groq au démarrage...")
    await post_ai_recap(actus_channel)

    while True:
        paris_now = datetime.now(timezone(timedelta(hours=2)))

        next_8h = paris_now.replace(hour=8, minute=0, second=0, microsecond=0)
        if paris_now >= next_8h:
            next_8h += timedelta(days=1)

        next_20h = paris_now.replace(hour=20, minute=0, second=0, microsecond=0)
        if paris_now >= next_20h:
            next_20h += timedelta(days=1)

        next_event = min(next_8h, next_20h)
        wait_seconds = (next_event - paris_now).total_seconds()
        print(f"⏰ Prochain événement dans {int(wait_seconds // 3600)}h {int((wait_seconds % 3600) // 60)}min")
        await asyncio.sleep(wait_seconds)

        paris_now = datetime.now(timezone(timedelta(hours=2)))

        if paris_now.hour == 8:
            await post_summary(actus_channel, label="🌅 **Résumé matinal**")
            if paris_now.weekday() == 0:
                await post_weekly_calendar(actus_channel)
        elif paris_now.hour == 20:
            await post_ai_recap(actus_channel)

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

    print("👀 Polling Telegram actif (toutes les 60 secondes)")

    while True:
        await asyncio.sleep(60)

        for channel_username, (label, translate, suppress) in TELEGRAM_CHANNELS.items():
            try:
                entity = await telegram_client.get_entity(channel_username)
                username = channel_username.strip("@")
                new_last_id = last_ids.get(channel_username, 0)

                async for message in telegram_client.iter_messages(entity, limit=10):
                    if message.id <= last_ids.get(channel_username, 0):
                        break

                    if not message.text and not message.photo:
                        new_last_id = max(new_last_id, message.id)
                        continue

                    text = translate_to_french(message.text) if translate and message.text else message.text or ""
                    post_link = f"https://t.me/{username}/{message.id}"
                    header = f"{label}\n\n"
                    footer = f"\n\n🔗 [Voir la source]({post_link})"
                    content = f"{header}{text}{footer}"

                    if len(content) > 2000:
                        print(f"⚠️ Message {channel_username} trop long, ignoré")
                        new_last_id = max(new_last_id, message.id)
                        continue

                    if is_duplicate(text):
                        print(f"⚠️ Doublon détecté {channel_username}, ignoré")
                        new_last_id = max(new_last_id, message.id)
                        continue

                    add_to_recent(text)

                    try:
                        if message.photo:
                            path = await message.download_media()
                            with open(path, 'rb') as f:
                                await actus_channel.send(content=content, file=discord.File(f), suppress_embeds=suppress)
                            if os.path.exists(path):
                                os.remove(path)
                        else:
                            await actus_channel.send(content, suppress_embeds=suppress)
                        print(f"✅ Nouveau message {channel_username} envoyé")
                    except Exception as e:
                        print(f"❌ Erreur envoi Discord {channel_username}: {e}")

                    new_last_id = max(new_last_id, message.id)

                last_ids[channel_username] = new_last_id

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
