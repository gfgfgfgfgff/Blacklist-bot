import os
import sys
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands

TOKEN = os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERREUR : Token Discord non défini!")
    print("Configure la variable d'environnement 'TOKEN' ou 'DISCORD_TOKEN'")
    sys.exit(1)

PREFIX = "&"
THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/1467151867191496808/1467232922938638479/IMG_1620.jpg?ex=697fa2a4&is=697e5124&hm=a712241a364f6b68dc031cac0860e5e9b9af3f2df3e69c8f3b14e1817852ccde&"
SUPPORT_ID = 1399234120214909010
LOG_THUMBNAIL = THUMBNAIL_URL

ADMIN_USER_ID = 1399234120214909010

def init_database():
    conn = sqlite3.connect('akusa_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT,
            grade TEXT,
            reason TEXT,
            added_by INTEGER,
            added_by_name TEXT,
            banned INTEGER DEFAULT 0,
            on_server INTEGER DEFAULT 1,
            timestamp TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whitelist (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT,
            added_by INTEGER,
            added_by_name TEXT,
            timestamp TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_config (
            guild_id INTEGER,
            log_type TEXT,
            channel_id INTEGER,
            PRIMARY KEY (guild_id, log_type)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bl_limits (
            user_id INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0,
            last_reset TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_grades (
            user_id INTEGER,
            guild_id INTEGER,
            grade TEXT,
            granted_by INTEGER,
            granted_by_name TEXT,
            timestamp TEXT,
            PRIMARY KEY (user_id, guild_id)
        )
    ''')
    
    conn.commit()
    return conn, cursor

db_conn, db_cursor = init_database()
print("Base de données SQLite initialisée")

def add_to_blacklist(user_id, user_name, grade, reason, added_by, added_by_name, banned, on_server, timestamp):
    db_cursor.execute('''
        INSERT OR REPLACE INTO blacklist 
        (user_id, user_name, grade, reason, added_by, added_by_name, banned, on_server, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, user_name, grade, reason, added_by, added_by_name, banned, on_server, timestamp))
    db_conn.commit()

def remove_from_blacklist(user_id):
    db_cursor.execute('DELETE FROM blacklist WHERE user_id = ?', (user_id,))
    db_conn.commit()

def get_blacklist():
    db_cursor.execute('SELECT * FROM blacklist ORDER BY timestamp DESC')
    return db_cursor.fetchall()

def get_blacklist_user(user_id):
    db_cursor.execute('SELECT * FROM blacklist WHERE user_id = ?', (user_id,))
    return db_cursor.fetchone()

def clear_blacklist():
    db_cursor.execute('DELETE FROM blacklist')
    db_conn.commit()
    return db_cursor.rowcount

def add_to_whitelist(user_id, user_name, added_by, added_by_name, timestamp):
    db_cursor.execute('''
        INSERT OR REPLACE INTO whitelist (user_id, user_name, added_by, added_by_name, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, user_name, added_by, added_by_name, timestamp))
    db_conn.commit()

def remove_from_whitelist(user_id):
    db_cursor.execute('DELETE FROM whitelist WHERE user_id = ?', (user_id,))
    db_conn.commit()
    return db_cursor.rowcount > 0

def is_in_whitelist(user_id):
    db_cursor.execute('SELECT 1 FROM whitelist WHERE user_id = ?', (user_id,))
    return db_cursor.fetchone() is not None

def get_whitelist():
    db_cursor.execute('SELECT * FROM whitelist ORDER BY timestamp DESC')
    return db_cursor.fetchall()

def clear_whitelist():
    db_cursor.execute('DELETE FROM whitelist')
    db_conn.commit()
    return db_cursor.rowcount

def set_log_channel(guild_id, log_type, channel_id):
    db_cursor.execute('''
        INSERT OR REPLACE INTO logs_config (guild_id, log_type, channel_id)
        VALUES (?, ?, ?)
    ''', (guild_id, log_type, channel_id))
    db_conn.commit()

def get_log_channel(guild_id, log_type):
    db_cursor.execute('''
        SELECT channel_id FROM logs_config 
        WHERE guild_id = ? AND log_type = ?
    ''', (guild_id, log_type))
    result = db_cursor.fetchone()
    return result[0] if result else None

def get_all_logs(guild_id):
    db_cursor.execute('SELECT log_type, channel_id FROM logs_config WHERE guild_id = ?', (guild_id,))
    return db_cursor.fetchall()

def update_bl_limit(user_id, count, last_reset):
    db_cursor.execute('''
        INSERT OR REPLACE INTO bl_limits (user_id, count, last_reset)
        VALUES (?, ?, ?)
    ''', (user_id, count, last_reset))
    db_conn.commit()

def get_bl_limit(user_id):
    db_cursor.execute('SELECT count, last_reset FROM bl_limits WHERE user_id = ?', (user_id,))
    return db_cursor.fetchone()

def set_user_grade(user_id, guild_id, grade, granted_by, granted_by_name, timestamp):
    db_cursor.execute('''
        INSERT OR REPLACE INTO user_grades (user_id, guild_id, grade, granted_by, granted_by_name, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, guild_id, grade, granted_by, granted_by_name, timestamp))
    db_conn.commit()

def get_user_grade(user_id, guild_id):
    if user_id == ADMIN_USER_ID:
        return "Créateur++"
    
    db_cursor.execute('SELECT grade FROM user_grades WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
    result = db_cursor.fetchone()
    return result[0] if result else None

def remove_user_grade(user_id, guild_id):
    db_cursor.execute('DELETE FROM user_grades WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
    db_conn.commit()
    return db_cursor.rowcount > 0

def get_all_users_with_grade(guild_id, grade):
    db_cursor.execute('SELECT user_id FROM user_grades WHERE guild_id = ? AND grade = ?', (guild_id, grade))
    return db_cursor.fetchall()

class PaginatorWithCounter(discord.ui.View):
    def __init__(self, embeds, total_items, timeout=3600):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.total_items = total_items
        self.current_page = 0
        self.update_buttons()
    
    def update_buttons(self):
        self.children[0].disabled = (self.current_page == 0)
        self.children[2].disabled = (self.current_page == len(self.embeds) - 1)
        self.children[1].label = f"{self.current_page + 1}/{len(self.embeds)}"
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

def has_required_grade(min_grade: str = None):
    async def predicate(ctx):
        if ctx.author.id == ADMIN_USER_ID:
            return True
        
        user_grade = get_user_grade(ctx.author.id, ctx.guild.id)
        
        if not min_grade:
            if user_grade:
                return True
        else:
            if user_grade and GRADES.get(user_grade, 0) >= GRADES.get(min_grade, 0):
                return True
        
        embed = discord.Embed(
            description="Tu na pas la permission d'utiliser cette commande",
            color=0xFFFFFF
        )
        await ctx.send(embed=embed)
        return False
    return commands.check(predicate)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

GRADES = {
    "Créateur++": 5,
    "Créateur": 4,
    "Sys+": 3,
    "Sys": 2,
    "Owner": 1
}

async def get_user_by_id_or_mention(ctx, identifier: str):
    try:
        if identifier.startswith('<@') and identifier.endswith('>'):
            user_id = identifier[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
            user_id = int(user_id)
        else:
            user_id = int(identifier)
        
        member = ctx.guild.get_member(user_id)
        if member:
            return member, True
        
        try:
            member = await ctx.guild.fetch_member(user_id)
            return member, True
        except discord.NotFound:
            try:
                user = await bot.fetch_user(user_id)
                class MinimalMember:
                    def __init__(self, user):
                        self.id = user.id
                        self.name = user.name
                        self.mention = user.mention
                        self.display_name = user.name
                        self.avatar = user.avatar
                        self.bot = user.bot
                return MinimalMember(user), False
            except discord.NotFound:
                return None, False
    except:
        return None, False

def create_white_embed(description: str) -> discord.Embed:
    return discord.Embed(description=description, color=0xFFFFFF)

def create_log_embed(title: str, fields: dict) -> discord.Embed:
    embed = discord.Embed(title=title, color=0xFFFFFF)
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    embed.set_thumbnail(url=LOG_THUMBNAIL)
    embed.set_footer(text=get_current_time_french())
    return embed

def get_current_time_french():
    tz = timezone(timedelta(hours=1))
    now = datetime.now(tz)
    return now.strftime("%d/%m/%Y - %H:%M:%S")

def time_ago(timestamp_str: str) -> str:
    try:
        tz = timezone(timedelta(hours=1))
        date_format = "%d/%m/%Y - %H:%M:%S"
        bl_time = datetime.strptime(timestamp_str, date_format).replace(tzinfo=tz)
        now = datetime.now(tz)
        
        diff = now - bl_time
        
        if diff.days > 0:
            if diff.days == 1:
                return "Il y a 1 jour"
            return f"Il y a {diff.days} jours"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            if hours == 1:
                return "Il y a 1 heure"
            return f"Il y a {hours} heures"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            if minutes == 1:
                return "Il y a 1 minute"
            return f"Il y a {minutes} minutes"
        else:
            return "À l'instant"
    except:
        return "Date inconnue"

BL_LIMITS = {
    "Owner": 3,
    "Sys": 6,
    "Sys+": 8,
    "Créateur": 15,
    "Créateur++": 9999
}

BL_COOLDOWN = 7200

def check_bl_limit(user_id: str, grade: str) -> tuple[bool, str]:
    if int(user_id) == ADMIN_USER_ID:
        return True, ""
    
    if is_in_whitelist(str(user_id)):
        return True, ""
    
    result = get_bl_limit(str(user_id))
    
    if not result:
        update_bl_limit(str(user_id), 0, datetime.now().isoformat())
        return True, ""
    
    count, last_reset_str = result
    last_reset = datetime.fromisoformat(last_reset_str)
    
    if datetime.now() - last_reset > timedelta(seconds=BL_COOLDOWN):
        update_bl_limit(str(user_id), 0, datetime.now().isoformat())
        return True, ""
    
    limit = BL_LIMITS.get(grade, 3)
    if count >= limit:
        time_left = last_reset + timedelta(seconds=BL_COOLDOWN) - datetime.now()
        minutes_left = int(time_left.total_seconds() // 60)
        seconds_left = int(time_left.total_seconds() % 60)
        return False, f"Tu as atteint le limite de bl, attends `{minutes_left}min {seconds_left}s` avant de pouvoir bl"
    
    return True, ""

def increment_bl_count(user_id: str):
    if int(user_id) == ADMIN_USER_ID or is_in_whitelist(str(user_id)):
        return
    
    result = get_bl_limit(str(user_id))
    
    if not result:
        update_bl_limit(str(user_id), 1, datetime.now().isoformat())
    else:
        count, last_reset = result
        update_bl_limit(str(user_id), count + 1, last_reset)

async def send_log(ctx, log_type: str, fields: dict):
    channel_id = get_log_channel(ctx.guild.id, log_type)
    
    if not channel_id:
        channel_id = get_log_channel(ctx.guild.id, "general")
        if not channel_id:
            return
    
    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except:
            return
    
    title_map = {
        "bl": "BL",
        "unbl": "UNBL",
        "rank": "ATTRIBUTION DE GRADE",
        "unrank": "RETRAIT DE GRADE",
        "wl": "WL",
        "unwl": "UNWL",
        "clearwl": "CLEARWL"
    }
    
    title = title_map.get(log_type, log_type.upper())
    embed = create_log_embed(title, fields)
    
    try:
        await channel.send(embed=embed)
    except:
        pass

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user}")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

@bot.command()
@has_required_grade()
async def help(ctx):
    embed1 = discord.Embed(color=0xFFFFFF)
    embed1.description = "Page 1/4 - Modération\n"
    embed1.add_field(
        name="Modération",
        value=(
            "`&bl @user/id raison` - Blacklist\n"
            "`&unbl @user/id` - Unblacklist\n"
            "`&bllist` - Liste des blacklist\n"
            "`&blinfo @user/id` - Infos blacklist\n"
            "`&myrole` - Vérifier ses rôles\n"
            "`&ping` - Vérifier la latence"
        ),
        inline=False
    )
    embed1.set_footer(text=f"Page 1/4 • {get_current_time_french()}")
    embed1.description += "\n\n-# Effectué la commande `&perm` pour voir votre grade et les commandes au quels vous avez accès"

    embed2 = discord.Embed(color=0xFFFFFF)
    embed2.description = "Page 2/4 - Information\n"
    embed2.add_field(
        name="Informations",
        value=(
            "`&grades` - Hiérarchie des grades\n"
            "`&perm` - Voir les permissions par grade\n"
            "`&wllist` - Voir les whitelists\n"
            "`&logs` - Configuration des logs\n"
            "`&changelimit grade nombre` - Changer limite BL par heure"
        ),
        inline=False
    )
    embed2.set_footer(text=f"Page 2/4 • {get_current_time_french()}")

    embed3 = discord.Embed(color=0xFFFFFF)
    embed3.description = "Page 3/4 - Modification des grades\n"
    embed3.add_field(
        name="Modification des grades",
        value=(
            "`&owner @user/id` - Donner grade Owner\n"
            "`&sys @user/id` - Donner grade Sys\n"
            "`&sys+ @user/id` - Donner grade Sys+\n"
            "`&crea @user/id` - Donner grade Créateur\n"
            "`&crea++ @user/id` - Donner grade Créateur++\n"
            "_(sans argument: liste des utilisateurs)_"
        ),
        inline=False
    )
    embed3.set_footer(text=f"Page 3/4 • {get_current_time_french()}")

    embed4 = discord.Embed(color=0xFFFFFF)
    embed4.description = "Page 4/4 - Créateur++ uniquement\n"
    embed4.add_field(
        name="Commandes réservées",
        value=(
            "`&wl @user/id` - Whitelist\n"
            "`&unwl @user/id` - Retirer WL\n"
            "`&clearwl` - Vider la whitelist\n"
            "`&unblall` - Tout unblacklist\n"
            "`&setlogs #salon` - Configurer logs\n"
            "`&setlogsbl #salon` - Logs BL\n"
            "`&setlogsunbl #salon` - Logs UNBL\n"
            "`&setlogsrank #salon` - Logs RANK\n"
            "`&setlogsunrank #salon` - Logs UNRANK\n"
            "`&setlogswl #salon` - Logs WL\n"
            "`&setlogsunwl #salon` - Logs UNWL\n"
            "`&help_logs` - Aide logs"
        ),
        inline=False
    )
    embed4.set_footer(text=f"Page 4/4 • {get_current_time_french()}")

    view = discord.ui.View(timeout=3600)
    view.add_item(discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.gray, disabled=True))
    view.add_item(discord.ui.Button(label="1/4", style=discord.ButtonStyle.gray, disabled=True))
    view.add_item(discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.gray))
    await ctx.send(embed=embed1, view=view)

@bot.command()
@has_required_grade()
async def help_logs(ctx):
    embed = create_white_embed(
        "Logs\n\n"
        "Pour définir un salon logs vous devez mettre obligatoirement le type et le salon\n"
        "exemple : &setlogsbl #salon\n\n"
        "&setlogs (les différents logs disponibles) #salon\n"
        "&setlogsbl #salon\n"
        "&setlogsunbl #salon\n"
        "&setlogsrank #salon\n"
        "&setlogsunrank #salon\n"
        "&setlogswl #salon\n"
        "&setlogsunwl #salon\n\n"
        "&logs"
    )
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def perm(ctx):
    description = "──────────────\n"
    description += "Créateur++\n"
    description += "──────────────\n"
    description += "Toutes les commandes\n\n"
    
    description += "──────────────\n"
    description += "Créateur\n"
    description += "──────────────\n"
    description += "Blacklist/Unblacklist\n"
    description += "Bllist/Blinfo\n"
    description += "Grades (owner, sys, sys+, crea) avec WL\n"
    description += "Wllist\n"
    description += "Myrole/Grades\n\n"
    
    description += "──────────────\n"
    description += "Sys+\n"
    description += "──────────────\n"
    description += "Blacklist/Unblacklist\n"
    description += "Bllist/Blinfo\n"
    description += "Myrole/Grades\n\n"
    
    description += "──────────────\n"
    description += "Sys\n"
    description += "──────────────\n"
    description += "Blacklist/Unblacklist\n"
    description += "Bllist/Blinfo\n"
    description += "Myrole/Grades\n\n"
    
    description += "──────────────\n"
    description += "Owner\n"
    description += "──────────────\n"
    description += "Blacklist/Unblacklist\n"
    description += "Bllist/Blinfo\n"
    description += "Myrole/Grades"
    
    embed = create_white_embed(description)
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def grades(ctx):
    lines = []
    
    for grade, value in sorted(GRADES.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"──────────────")
        lines.append(f"{grade} • Permission {value}")
    
    lines.append(f"──────────────")
    embed = create_white_embed("HIÉRARCHIE DES GRADES\n\n" + "\n".join(lines))
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def myrole(ctx):
    grade = get_user_grade(ctx.author.id, ctx.guild.id)
    if grade:
        embed = create_white_embed(
            f"T'es gradé : {grade}\n\n"
            f"Fais `&perm` pour voir les commandes aux quels tu as accès"
        )
    else:
        embed = create_white_embed("Tu n'as aucun grade de la hiérarchie.")
    await ctx.send(embed=embed)

async def handle_grade_command(ctx, member_identifier, grade_name, grade_display):
    if not member_identifier:
        users = get_all_users_with_grade(ctx.guild.id, grade_name)
        
        if not users:
            embed = create_white_embed(f"**Liste des {grade_display}**\n\nAucun utilisateur n'a le grade {grade_display}.")
            return await ctx.send(embed=embed)
        
        members_list = []
        for user_id in users:
            user_id = user_id[0]
            try:
                user = await bot.fetch_user(user_id)
                members_list.append(f"{user.mention}\n`{user.id}`")
            except:
                members_list.append(f"<@{user_id}>\n`{user_id}`")
        
        embed = create_white_embed(
            f"**Liste des {grade_display}** ({len(users)}):\n\n" +
            "\n\n".join(members_list)
        )
        await ctx.send(embed=embed)
        return
    
    result = await get_user_by_id_or_mention(ctx, member_identifier)
    
    if not result:
        embed = create_white_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    executor_grade = get_user_grade(ctx.author.id, ctx.guild.id)
    
    if ctx.author.id != ADMIN_USER_ID:
        if not executor_grade:
            embed = create_white_embed("Tu na pas la permission d'utiliser cette commande")
            return await ctx.send(embed=embed)
        
        if grade_name == "Créateur++" and executor_grade != "Créateur++":
            embed = create_white_embed("Tu na pas la permission d'utiliser cette commande")
            return await ctx.send(embed=embed)
        
        if grade_name == "Créateur" and executor_grade not in ["Créateur++", "Créateur"]:
            embed = create_white_embed("Tu na pas la permission d'utiliser cette commande")
            return await ctx.send(embed=embed)
        
        if grade_name in ["Sys+", "Sys", "Owner"] and executor_grade == "Créateur":
            if not is_in_whitelist(str(ctx.author.id)):
                embed = create_white_embed("Tu na pas la permission d'utiliser cette commande")
                return await ctx.send(embed=embed)
        
        executor_grade_value = GRADES[executor_grade]
        target_grade_value = GRADES[grade_name]
        
        if target_grade_value >= executor_grade_value:
            embed = create_white_embed("Tu ne peux pas donner un grade égal ou supérieur au tien")
            return await ctx.send(embed=embed)
    
    current_grade = get_user_grade(member.id, ctx.guild.id)
    
    try:
        if current_grade:
            remove_user_grade(member.id, ctx.guild.id)
        
        set_user_grade(
            member.id,
            ctx.guild.id,
            grade_name,
            ctx.author.id,
            ctx.author.name,
            get_current_time_french()
        )
        
        embed = create_white_embed(f"{member.mention} a bien reçu le grade (**{grade_display}**)")
        await ctx.send(embed=embed)
        
        executor_display = "Créateur++" if ctx.author.id == ADMIN_USER_ID else f"{executor_grade}"
        await send_log(ctx, "rank", {
            "Donné par": f"{ctx.author.mention} ({executor_display})",
            "À": member.mention,
            "Grade donné": grade_display
        })
        
    except Exception as e:
        embed = create_white_embed(f"Erreur technique. Impossible d'ajouter le grade.")
        await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur")
async def owner(ctx, member: str = None):
    await handle_grade_command(ctx, member, "Owner", "Owner")

@bot.command()
@has_required_grade("Créateur")
async def sys(ctx, member: str = None):
    await handle_grade_command(ctx, member, "Sys", "Sys")

@bot.command()
@has_required_grade("Créateur")
async def sysplus(ctx, member: str = None):
    await handle_grade_command(ctx, member, "Sys+", "Sys+")

@bot.command()
@has_required_grade("Créateur++")
async def crea(ctx, member: str = None):
    await handle_grade_command(ctx, member, "Créateur", "Créateur")

@bot.command()
@has_required_grade("Créateur++")
async def creapp(ctx, member: str = None):
    await handle_grade_command(ctx, member, "Créateur++", "Créateur++")

@bot.command()
@has_required_grade()
async def ungrade(ctx, member: str = None):
    if not member:
        embed = create_white_embed("Usage : `&ungrade @user/id`")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, member)
    
    if not result:
        embed = create_white_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    current_grade = get_user_grade(member.id, ctx.guild.id)
    
    if not current_grade:
        embed = create_white_embed(f"{member.mention} n'a aucun grade.")
        return await ctx.send(embed=embed)
    
    executor_grade = get_user_grade(ctx.author.id, ctx.guild.id)
    
    if ctx.author.id != ADMIN_USER_ID:
        if not executor_grade:
            embed = create_white_embed("Tu na pas la permission d'utiliser cette commande")
            return await ctx.send(embed=embed)
        
        if current_grade == "Créateur++":
            embed = create_white_embed("Tu ne peux pas retirer le grade d'un Créateur++")
            return await ctx.send(embed=embed)
        
        executor_grade_value = GRADES[executor_grade]
        target_grade_value = GRADES[current_grade]
        
        if target_grade_value >= executor_grade_value:
            embed = create_white_embed("Tu ne peux pas retirer un grade égal ou supérieur au tien")
            return await ctx.send(embed=embed)
    
    remove_user_grade(member.id, ctx.guild.id)
    
    embed = create_white_embed(f"{member.mention} n'est plus (**{current_grade}**)")
    await ctx.send(embed=embed)
    
    executor_display = "Créateur++" if ctx.author.id == ADMIN_USER_ID else f"{executor_grade}"
    await send_log(ctx, "unrank", {
        "Retiré par": f"{ctx.author.mention} ({executor_display})",
        "De": member.mention,
        "Grade retiré": current_grade
    })

@bot.command()
@has_required_grade()
async def bl(ctx, identifier: str = None, *, reason: str = None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_member = replied_message.author
            identifier = str(target_member.id)
        except:
            pass
    
    if not identifier:
        embed = create_white_embed("**Usage Incorrecte**\nUsage : `&bl id/@ raison`")
        return await ctx.send(embed=embed)
    
    if not reason:
        embed = create_white_embed("**Usage Incorrecte**\nUsage : `&bl id/@ raison`\n\nRaison obligatoire pour blacklister un utilisateur.")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_white_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    target_member, is_on_server = result
    
    if target_member.id == ctx.author.id:
        embed = create_white_embed("Wsh ? T'es con ou quoi? Tu veux te suicider?")
        return await ctx.send(embed=embed)
    
    existing = get_blacklist_user(target_member.id)
    if existing:
        embed = create_white_embed(f"Cet utilisateur est déjà dans la blacklist.")
        return await ctx.send(embed=embed)
    
    executor_grade = get_user_grade(ctx.author.id, ctx.guild.id)
    
    if ctx.author.id == ADMIN_USER_ID:
        if target_member.id == ADMIN_USER_ID:
            embed = create_white_embed("Tu ne peux pas te blacklist toi-même.")
            return await ctx.send(embed=embed)
    else:
        if not executor_grade:
            embed = create_white_embed("Tu na pas la permission d'utiliser cette commande")
            return await ctx.send(embed=embed)
    
    if is_on_server and isinstance(target_member, discord.Member):
        target_grade = get_user_grade(target_member.id, ctx.guild.id)
        
        if target_grade == "Créateur++":
            embed = create_white_embed("Impossible de blacklist un Créateur++.")
            return await ctx.send(embed=embed)
        
        if ctx.author.id != ADMIN_USER_ID and target_grade:
            if GRADES[executor_grade] <= GRADES[target_grade]:
                embed = create_white_embed(f"Tu ne peux pas bl {target_member.mention} car il est égal ou supérieur à toi")
                return await ctx.send(embed=embed)
        
        target_grade_display = target_grade if target_grade else "Aucun grade"
    else:
        target_grade_display = "Inconnu (hors serveur)"
    
    if ctx.author.id != ADMIN_USER_ID and not is_in_whitelist(str(ctx.author.id)):
        can_bl, error_msg = check_bl_limit(str(ctx.author.id), executor_grade)
        if not can_bl:
            embed = create_white_embed(error_msg)
            return await ctx.send(embed=embed)
    
    ban_success = False
    if is_on_server:
        try:
            await target_member.ban(reason=f"Blacklist par {ctx.author}: {reason}")
            ban_success = True
        except:
            ban_success = False
    else:
        ban_success = False
    
    user_name = target_member.name if hasattr(target_member, 'name') else str(target_member.id)
    added_by_name = ctx.author.name
    
    add_to_blacklist(
        target_member.id,
        user_name,
        target_grade_display,
        reason,
        ctx.author.id,
        added_by_name,
        1 if ban_success else 0,
        1 if is_on_server else 0,
        get_current_time_french()
    )
    
    if ctx.author.id != ADMIN_USER_ID and not is_in_whitelist(str(ctx.author.id)):
        increment_bl_count(str(ctx.author.id))
    
    try:
        dm_message = (
            f"Vous avez été blacklisté de `Akusa` #🎐 pour `{reason}`\n\n"
            f"Rejoignez le serveur prison d'Akusa pour vous faire unbl\n"
            f"lien : https://discord.gg/Cr8K2N48fe"
        )
        await target_member.send(dm_message)
    except:
        pass
    
    embed = create_white_embed(f"{target_member.mention} à bien etait blacklister\n`{reason}`")
    await ctx.send(embed=embed)
    
    executor_display = "Créateur++" if ctx.author.id == ADMIN_USER_ID else f"{executor_grade}"
    
    if is_on_server:
        await send_log(ctx, "bl", {
            "Blacklist par": f"{ctx.author.mention} ({executor_display})",
            "Utilisateur BL": target_member.mention,
            "Raison": reason,
        })
    else:
        await send_log(ctx, "bl", {
            "Blacklist par": f"{ctx.author.mention} ({executor_display})",
            "Utilisateur BL": f"{user_name} (ID: {target_member.id})",
            "Raison": reason,
        })

@bot.command()
@has_required_grade()
async def unbl(ctx, identifier: str = None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_member = replied_message.author
            identifier = str(target_member.id)
        except:
            pass
    
    if not identifier:
        embed = create_white_embed("MAUVAISE UTILISATION\nUsage : `&unbl id/@`")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_white_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    existing = get_blacklist_user(member.id)
    
    if not existing:
        embed = create_white_embed("Cet utilisateur n'est pas dans la blacklist.")
        return await ctx.send(embed=embed)
    
    user_id, user_name, grade, reason, added_by, added_by_name, banned, on_server, timestamp = existing
    
    executor_grade = get_user_grade(ctx.author.id, ctx.guild.id)
    
    if ctx.author.id != ADMIN_USER_ID:
        if not executor_grade:
            embed = create_white_embed("Tu na pas la permission d'utiliser cette commande")
            return await ctx.send(embed=embed)
    
    if added_by != ctx.author.id and ctx.author.id != ADMIN_USER_ID:
        try:
            bl_by_user = await bot.fetch_user(added_by)
            bl_by_grade = get_user_grade(added_by, ctx.guild.id)
            
            if bl_by_grade:
                if GRADES[bl_by_grade] > GRADES[executor_grade]:
                    embed = create_white_embed(f"Tu ne peux pas unbl cette utilisateur car il a etait bl par un **({bl_by_grade})**")
                    return await ctx.send(embed=embed)
        except:
            pass
    
    if added_by == ADMIN_USER_ID and ctx.author.id != ADMIN_USER_ID:
        try:
            embed = create_white_embed(f"Cette utilisateur a etait Bl par <@{added_by}>")
            return await ctx.send(embed=embed)
        except:
            embed = create_white_embed(f"Cette utilisateur a etait Bl par @akusa")
            return await ctx.send(embed=embed)
    
    unban_success = False
    if is_on_server:
        try:
            try:
                ban_entry = await ctx.guild.fetch_ban(discord.Object(id=member.id))
                await ctx.guild.unban(ban_entry.user, reason=f"Unblacklist par {ctx.author}")
                unban_success = True
            except discord.NotFound:
                pass
        except:
            pass
    
    try:
        dm_message = (
            f"Vous avez été unbl de `Akusa` #🎐\n\n"
            f"Voici le lien du serveur : https://discord.gg/fH2ur9ffSa"
        )
        await member.send(dm_message)
    except:
        pass
    
    remove_from_blacklist(member.id)
    
    embed = create_white_embed(f"{member.mention} à bien etait unbl")
    await ctx.send(embed=embed)
    
    if is_on_server:
        await send_log(ctx, "unbl", {
            "Unblacklist par": ctx.author.mention,
            "Utilisateur unBL": member.mention,
            "Statut": "Sur serveur"
        })
    else:
        await send_log(ctx, "unbl", {
            "Unblacklist par": ctx.author.mention,
            "Utilisateur unBL": f"{member.name} (ID: {member.id})",
            "Statut": "Hors serveur"
        })

@bot.command()
@has_required_grade("Créateur++")
async def unblall(ctx):
    count = clear_blacklist()
    
    unbanned_count = 0
    try:
        async for ban_entry in ctx.guild.bans():
            await ctx.guild.unban(ban_entry.user, reason=f"Unblacklist all par {ctx.author}")
            unbanned_count += 1
    except:
        pass
    
    if count == 0:
        msg = "0 utilisateur a été unblacklist avec succès"
    elif count == 1:
        msg = "1 utilisateur a été unblacklist avec succès"
    else:
        msg = f"{count} utilisateurs ont été unblacklist avec succès"
    
    embed = create_white_embed(msg)
    await ctx.send(embed=embed)
    
    await send_log(ctx, "unbl", {
        "Unblacklist par": ctx.author.mention,
        "Action": "Tout unblacklist",
        "Nombre": str(count)
    })

@bot.command()
@has_required_grade()
async def bllist(ctx):
    bl_data = get_blacklist()
    
    if not bl_data:
        embed = create_white_embed("Aucun utilisateur blacklist")
        return await ctx.send(embed=embed)
    
    items_per_page = 10
    pages = []
    
    for i in range(0, len(bl_data), items_per_page):
        description_lines = ["**Liste des utilisateurs blacklister**\n"]
        items = bl_data[i:i+items_per_page]
        
        for item in items:
            user_id, user_name, grade, reason, added_by, added_by_name, banned, on_server, timestamp = item
            user_mention = f"<@{user_id}>"
            
            description_lines.append(f"{user_mention}\n`{reason}`")
            description_lines.append("─" * 30)
        
        embed = create_white_embed("\n".join(description_lines))
        embed.set_footer(text=f"blacklist : {len(bl_data)}")
        pages.append(embed)
    
    if len(pages) == 1:
        await ctx.send(embed=pages[0])
        return
    
    view = PaginatorWithCounter(pages, len(bl_data))
    await ctx.send(embed=pages[0], view=view)

@bot.command()
@has_required_grade()
async def blinfo(ctx, identifier: str):
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_white_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    existing = get_blacklist_user(member.id)
    
    if not existing:
        embed = create_white_embed("Cet utilisateur n'est pas dans la blacklist.")
        return await ctx.send(embed=embed)
    
    user_id, user_name, grade, reason, added_by, added_by_name, banned, on_server, timestamp = existing
    
    bl_by_grade = None
    try:
        if added_by:
            bl_by_grade = get_user_grade(added_by, ctx.guild.id)
    except:
        pass
    
    if not bl_by_grade and added_by == ADMIN_USER_ID:
        bl_by_grade = "Créateur++"
    
    hide_identity = False
    if bl_by_grade in ["Créateur", "Créateur++"]:
        hide_identity = True
    
    embed_lines = ["BLACKLIST INFO\n"]
    embed_lines.append("")
    
    embed_lines.append(f"blacklist : {member.mention}")
    embed_lines.append(f"`{user_id}`")
    embed_lines.append(f"`{reason}`")
    embed_lines.append("")
    
    if hide_identity:
        embed_lines.append(f"Blacklist par : ❌❌❌")
    else:
        if added_by:
            embed_lines.append(f"Blacklist par : <@{added_by}>")
        else:
            embed_lines.append(f"Blacklist par : Inconnu")
    
    embed_lines.append("")
    
    time_ago_text = time_ago(timestamp)
    embed_lines.append(f"{time_ago_text}")
    
    embed = create_white_embed("\n".join(embed_lines))
    
    if hasattr(member, 'avatar') and member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def grade(ctx, identifier: str = None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_member = replied_message.author
            identifier = str(target_member.id)
        except:
            pass
    
    if not identifier:
        target_member = ctx.author
        is_on_server = True
    else:
        result = await get_user_by_id_or_mention(ctx, identifier)
        
        if not result:
            embed = create_white_embed("Utilisateur introuvable.")
            return await ctx.send(embed=embed)
        
        target_member, is_on_server = result
    
    if is_on_server and isinstance(target_member, discord.Member):
        grade = get_user_grade(target_member.id, ctx.guild.id)
        
        if grade:
            embed = create_white_embed(f"{target_member.mention} a le grade **{grade}**")
        else:
            embed = create_white_embed(f"{target_member.mention} n'a aucun grade de la hiérarchie")
    else:
        embed = create_white_embed(f"{target_member.mention} n'est pas sur le serveur, impossible de vérifier son grade")
    
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def limits(ctx):
    lines = []
    
    for grade, limit in sorted(BL_LIMITS.items(), key=lambda x: GRADES.get(x[0], 0), reverse=True):
        if limit == 9999:
            limit_display = "Illimité"
        else:
            limit_display = str(limit)
        
        lines.append(f"**{grade}** : {limit_display} BL/heure")
    
    lines.append(f"\n> La limite de bl par heure ce reset toute les **2 heures**")
    
    embed = create_white_embed("\n".join(lines))
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def wl(ctx, identifier: str = None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_member = replied_message.author
            identifier = str(target_member.id)
        except:
            pass
    
    if not identifier:
        embed = create_white_embed("MAUVAISE UTILISATION\nUsage : `&wl id/@`")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_white_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    if is_in_whitelist(member.id):
        if is_on_server:
            embed = create_white_embed(f"{member.mention} est déjà dans la whitelist.")
        else:
            embed = create_white_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) est déjà dans la whitelist.")
        return await ctx.send(embed=embed)
    
    user_name = member.name if hasattr(member, 'name') else str(member.id)
    added_by_name = ctx.author.name
    
    add_to_whitelist(
        member.id,
        user_name,
        ctx.author.id,
        added_by_name,
        get_current_time_french()
    )
    
    if is_on_server:
        embed = create_white_embed(f"{member.mention} ajouté à la whitelist.")
    else:
        embed = create_white_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) ajouté à la whitelist.")
    
    await ctx.send(embed=embed)
    
    if is_on_server:
        await send_log(ctx, "wl", {
            "Ajouté par": ctx.author.mention,
            "À": member.mention
        })
    else:
        await send_log(ctx, "wl", {
            "Ajouté par": ctx.author.mention,
            "À": f"{member.name} (ID: {member.id})"
        })

@bot.command()
@has_required_grade("Créateur++")
async def unwl(ctx, identifier: str = None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_member = replied_message.author
            identifier = str(target_member.id)
        except:
            pass
    
    if not identifier:
        embed = create_white_embed("MAUVAISE UTILISATION\nUsage : `&unwl id/@`")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_white_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    removed = remove_from_whitelist(member.id)
    
    if removed:
        if is_on_server:
            embed = create_white_embed(f"{member.mention} retiré de la whitelist.")
        else:
            embed = create_white_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) retiré de la whitelist.")
        
        if is_on_server:
            await send_log(ctx, "unwl", {
                "Retiré par": ctx.author.mention,
                "De": member.mention
            })
        else:
            await send_log(ctx, "unwl", {
                "Retiré par": ctx.author.mention,
                "De": f"{member.name} (ID: {member.id})"
            })
    else:
        if is_on_server:
            embed = create_white_embed(f"{member.mention} n'est pas dans la whitelist.")
        else:
            embed = create_white_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) n'est pas dans la whitelist.")
    
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def clearwl(ctx):
    count = clear_whitelist()
    
    if count == 0:
        embed = create_white_embed("La whitelist est déjà vide.")
    else:
        embed = create_white_embed(f"Whitelist vidée avec succès. {count} utilisateur(s) retiré(s).")
        
        await send_log(ctx, "clearwl", {
            "Vidée par": ctx.author.mention,
            "Nombre retiré": str(count)
        })
    
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def wllist(ctx):
    data = get_whitelist()
    
    description_lines = ["Whitelist\n"]
    
    if data:
        for item in data:
            user_id, user_name, added_by, added_by_name, timestamp = item
            description_lines.append(f"• <@{user_id}>")
    else:
        description_lines.append("Aucun utilisateur dans la whitelist")
    
    embed = create_white_embed("\n".join(description_lines))
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def setlogs(ctx, channel: discord.TextChannel):
    set_log_channel(ctx.guild.id, "general", channel.id)
    embed = create_white_embed(f"Salon de logs configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def setlogsbl(ctx, channel: discord.TextChannel):
    set_log_channel(ctx.guild.id, "bl", channel.id)
    embed = create_white_embed(f"Salon de logs BL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def setlogsunbl(ctx, channel: discord.TextChannel):
    set_log_channel(ctx.guild.id, "unbl", channel.id)
    embed = create_white_embed(f"Salon de logs UNBL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def setlogsrank(ctx, channel: discord.TextChannel):
    set_log_channel(ctx.guild.id, "rank", channel.id)
    embed = create_white_embed(f"Salon de logs RANK configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def setlogsunrank(ctx, channel: discord.TextChannel):
    set_log_channel(ctx.guild.id, "unrank", channel.id)
    embed = create_white_embed(f"Salon de logs UNRANK configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def setlogswl(ctx, channel: discord.TextChannel):
    set_log_channel(ctx.guild.id, "wl", channel.id)
    embed = create_white_embed(f"Salon de logs WL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def setlogsunwl(ctx, channel: discord.TextChannel):
    set_log_channel(ctx.guild.id, "unwl", channel.id)
    embed = create_white_embed(f"Salon de logs UNWL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def logs(ctx):
    data = get_all_logs(ctx.guild.id)
    
    if not data:
        embed = create_white_embed("Aucun salon de logs configuré.")
        return await ctx.send(embed=embed)
    
    lines = ["Logs\n"]
    log_types = {
        "general": "General",
        "bl": "Bl",
        "unbl": "Unbl",
        "rank": "Rank",
        "unrank": "Unrank",
        "wl": "Wl",
        "unwl": "Unwl"
    }
    
    for key, name in log_types.items():
        channel_id = None
        for log_type, cid in data:
            if log_type == key:
                channel_id = cid
                break
        
        if channel_id:
            lines.append(f"{name} : <#{channel_id}>")
        else:
            lines.append(f"{name} : Non configuré")
    
    embed = create_white_embed("\n".join(lines))
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade("Créateur++")
async def changelimit(ctx, grade: str, limit: int):
    grade = grade.lower()
    valid_grades = ["owner", "sys", "sys+", "crea", "crea++"]
    
    if grade not in valid_grades:
        embed = create_white_embed(f"Grade invalide. Grades : {', '.join(valid_grades)}")
        return await ctx.send(embed=embed)
    
    if limit < 0 or limit > 9999:
        embed = create_white_embed("Limite invalide. Utilise un nombre entre 0 et 9999.")
        return await ctx.send(embed=embed)
    
    grade_map = {
        "owner": "Owner",
        "sys": "Sys",
        "sys+": "Sys+",
        "crea": "Créateur",
        "crea++": "Créateur++"
    }
    
    grade_display = grade_map[grade]
    BL_LIMITS[grade_display] = limit
    
    embed = create_white_embed(f"Limite de BL par heure pour **{grade_display}** définie à **{limit}**.")
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = create_white_embed(f"Pong! Latence : **{latency}ms**")
    await ctx.send(embed=embed)

if __name__ == "__main__":
    print("Démarrage du bot Akusa...")
    bot.run(TOKEN)