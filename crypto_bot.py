import discord
import asyncio
import os

TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_NAME = "The Crypto Bro"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")
    for g in client.guilds:
        if g.name == GUILD_NAME:
            perms = g.me.guild_permissions
            print(f"Gérer les salons : {perms.manage_channels}")
            print(f"Voir les salons : {perms.view_channel}")
            print(f"Envoyer des messages : {perms.send_messages}")
            for ch in g.channels:
                print(f"Salon: {ch.name} - permissions: {ch.permissions_for(g.me)}")

client.run(TOKEN)
