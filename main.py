import os
import sys
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

# ============ IMPORT DISCORD ============
import discord
from discord.ext import commands

# ============ CONFIGURATION ============
TOKEN = os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERREUR : Token Discord non défini!")
    print("Configure la variable d'environnement 'TOKEN' ou 'DISCORD_TOKEN'")
    sys.exit(1)

PREFIX = "&"
THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/1467151867191496808/1467232922938638479/IMG_1620.jpg?ex=697fa2a4&is=697e5124&hm=a712241a364f6b68dc031cac0860e5e9b9af3f2df3e69c8f3b14e1817852ccde&"
SUPPORT_ID = 1399234120214909010
LOG_THUMBNAIL = THUMBNAIL_URL

# ============ ADMIN USER ID ============
ADMIN_USER_ID = 1399234120214909010

# IDs des rôles
CREATOR_PP_ROLE_ID = 1466459905736183879
CREATOR_ROLE_ID = 1466514624718307562
SYS_PLUS_ROLE_ID = 1466515541828309195
SYS_ROLE_ID = 1466462217808642263
OWNER_ROLE_ID = 1466773492388073482

# ============ BASE DE DONNÉES SQLITE ============
def init_database():
    """Initialise la base de données SQLite"""
    conn = sqlite3.connect('akusa_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Table blacklist
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
    
    # Table whitelist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whitelist (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT,
            added_by INTEGER,
            added_by_name TEXT,
            timestamp TEXT
        )
    ''')
    
    # Table logs configuration
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_config (
            guild_id INTEGER,
            log_type TEXT,
            channel_id INTEGER,
            PRIMARY KEY (guild_id, log_type)
        )
    ''')
    
    # Table blacklist limits
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bl_limits (
            user_id INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0,
            last_reset TEXT
        )
    ''')
    
    # Table grade limits
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grade_limits (
            guild_id INTEGER,
            grade_type TEXT,
            limit_value INTEGER,
            PRIMARY KEY (guild_id, grade_type)
        )
    ''')
    
    conn.commit()
    return conn, cursor

# Initialiser la base de données
db_conn, db_cursor = init_database()
print("✅ Base de données SQLite initialisée")

# ============ FONCTIONS DATABASE ============
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

def set_grade_limit(guild_id, grade_type, limit_value):
    db_cursor.execute('''
        INSERT OR REPLACE INTO grade_limits (guild_id, grade_type, limit_value)
        VALUES (?, ?, ?)
    ''', (guild_id, grade_type, limit_value))
    db_conn.commit()

def get_grade_limit(guild_id, grade_type):
    db_cursor.execute('''
        SELECT limit_value FROM grade_limits 
        WHERE guild_id = ? AND grade_type = ?
    ''', (guild_id, grade_type))
    result = db_cursor.fetchone()
    return result[0] if result else None

# ============ PAGINATION SIMPLE ============
class SimplePaginator(discord.ui.View):
    def __init__(self, embeds, timeout=3600):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()
    
    def update_buttons(self):
        self.children[0].disabled = (self.current_page == 0)
        self.children[1].disabled = (self.current_page == len(self.embeds) - 1)
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

# ============ VÉRIFICATIONS DE PERMISSIONS ============
def has_required_grade():
    async def predicate(ctx):
        if ctx.author.id == ADMIN_USER_ID:
            return True
        
        if get_user_grade(ctx.author):
            return True
        
        embed = discord.Embed(
            description="Malheureusement tu n'as pas les permissions nécessaires",
            color=0x000000
        )
        await ctx.send(embed=embed)
        return False
    return commands.check(predicate)

def has_specific_grade(required_grade: str):
    async def predicate(ctx):
        if ctx.author.id == ADMIN_USER_ID:
            return True
        
        user_grade = get_user_grade(ctx.author)
        if not user_grade:
            embed = discord.Embed(
                description="Malheureusement tu n'as pas les permissions nécessaires",
                color=0x000000
            )
            await ctx.send(embed=embed)
            return False
        
        user_value = GRADES[user_grade]
        required_value = GRADES[required_grade]
        
        if user_value >= required_value:
            return True
        
        embed = discord.Embed(
            description="Malheureusement tu n'as pas les permissions nécessaires",
            color=0x000000
        )
        await ctx.send(embed=embed)
        return False
    return commands.check(predicate)

# ============ INITIALISATION ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ============ HIÉRARCHIE ============
GRADES = {
    "Créateur++": 5,
    "Créateur": 4,
    "Sys+": 3,
    "Sys": 2,
    "Owner": 1
}

ROLE_IDS_TO_GRADES = {
    CREATOR_PP_ROLE_ID: "Créateur++",
    CREATOR_ROLE_ID: "Créateur",
    SYS_PLUS_ROLE_ID: "Sys+",
    SYS_ROLE_ID: "Sys",
    OWNER_ROLE_ID: "Owner"
}

GRADE_TO_ROLE_ID = {
    "owner": OWNER_ROLE_ID,
    "sys": SYS_ROLE_ID,
    "sys+": SYS_PLUS_ROLE_ID,
    "crea": CREATOR_ROLE_ID,
    "crea++": CREATOR_PP_ROLE_ID
}

# ============ FONCTIONS UTILITAIRES ============
def get_user_grade(member: discord.Member) -> Optional[str]:
    if member.id == ADMIN_USER_ID:
        return "Créateur++"
    
    highest_grade = None
    highest_value = -1
    
    for role in member.roles:
        if role.id in ROLE_IDS_TO_GRADES:
            grade_name = ROLE_IDS_TO_GRADES[role.id]
            grade_value = GRADES[grade_name]
            
            if grade_value > highest_value:
                highest_value = grade_value
                highest_grade = grade_name
    
    return highest_grade

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
                        self.roles = []
                return MinimalMember(user), False
            except discord.NotFound:
                return None, False
    except:
        return None, False

def create_white_embed(description: str) -> discord.Embed:
    return discord.Embed(description=description, color=0xFFFFFF)

def create_green_embed(description: str) -> discord.Embed:
    return discord.Embed(description=description, color=0x00FF00)

def create_red_embed(description: str) -> discord.Embed:
    return discord.Embed(description=description, color=0xFF0000)

def create_black_embed(description: str) -> discord.Embed:
    return discord.Embed(description=description, color=0x000000)

def create_black_embed_with_title(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=0x000000)

def create_log_embed(title: str, fields: dict) -> discord.Embed:
    embed = discord.Embed(title=title, color=0x00FF00)
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    embed.set_thumbnail(url=LOG_THUMBNAIL)
    embed.set_footer(text=get_current_time_french())
    return embed

def get_current_time_french():
    tz = timezone(timedelta(hours=1))
    now = datetime.now(tz)
    return now.strftime("%d/%m/%Y - %H:%M:%S")

# ============ LIMITES BLACKLIST ============
BL_LIMITS = {
    "Owner": 3,
    "Sys": 6,
    "Sys+": 8,
    "Créateur": 15,
    "Créateur++": 9999
}

BL_COOLDOWN = 7200  # 2 heures

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
        return False, f"Limite atteinte ({limit}/2h). Réessayez dans {minutes_left} minutes"
    
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

# ============ LOGS ============
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

# ============ ÉVÉNEMENTS ============
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

# ============ COMMANDES HELP ============
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
            "`&rank @user grade` - Donner un grade\n"
            "  _(owner, sys, sys+, crea, crea++)_"
        ),
        inline=False
    )
    embed3.set_footer(text=f"Page 3/4 • {get_current_time_french()}")

    embed4 = discord.Embed(color=0xFFFFFF)
    embed4.description = "Page 4/4 - Créateur++ uniquement\n"
    embed4.add_field(
        name="Commandes réservées",
        value=(
            "`&wl @user` - Whitelist\n"
            "`&unwl @user` - Retirer WL\n"
            "`&clearwl` - Vider la whitelist\n"
            "`&unblall` - Tout unblacklist\n"
            "`&setlogs #salon` - Configurer logs\n"
            "`&setlogsbl #salon` - Logs BL\n"
            "`&setlogsunbl #salon` - Logs UNBL\n"
            "`&setlogsrank #salon` - Logs RANK\n"
            "`&setlogswl #salon` - Logs WL\n"
            "`&setlogsunwl #salon` - Logs UNWL\n"
            "`&help_logs` - Aide logs"
        ),
        inline=False
    )
    embed4.set_footer(text=f"Page 4/4 • {get_current_time_french()}")

    view = SimplePaginator([embed1, embed2, embed3, embed4])
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
        "&setlogswl #salon\n"
        "&setlogsunwl #salon\n\n"
        "&logs"
    )
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def perm(ctx):
    description = "──────────────\n"
    
    if ctx.author.id == ADMIN_USER_ID:
        description += "🔰 ADMIN SPÉCIAL\n"
        description += "──────────────\n"
        description += "• Accès complet à toutes les commandes\n"
        description += "• Pas de limites de blacklist\n"
        description += "• Pas besoin de whitelist\n"
        description += "• Toutes les permissions\n\n"
    
    description += "──────────────\n"
    description += "👑 Créateur++\n"
    description += "──────────────\n"
    description += "• Toutes les commandes\n"
    description += "• WL/UnWL/ClearWL\n"
    description += "• Unblall\n"
    description += "• Configuration logs\n"
    description += "• Changer limites BL\n\n"
    
    description += "──────────────\n"
    description += "⭐ Créateur\n"
    description += "──────────────\n"
    description += "• Blacklist/Unblacklist\n"
    description += "• Bllist/Blinfo\n"
    description += "• Grades (owner, sys, sys+, crea) avec WL\n"
    description += "• Wllist\n"
    description += "• Myrole/Grades\n\n"
    
    description += "──────────────\n"
    description += "🛠️ Sys+\n"
    description += "──────────────\n"
    description += "• Blacklist/Unblacklist\n"
    description += "• Bllist/Blinfo\n"
    description += "• Myrole/Grades\n\n"
    
    description += "──────────────\n"
    description += "🔧 Sys\n"
    description += "──────────────\n"
    description += "• Blacklist/Unblacklist\n"
    description += "• Bllist/Blinfo\n"
    description += "• Myrole/Grades\n\n"
    
    description += "──────────────\n"
    description += "👑 Owner\n"
    description += "──────────────\n"
    description += "• Blacklist/Unblacklist\n"
    description += "• Bllist/Blinfo\n"
    description += "• Myrole/Grades"
    
    embed = create_white_embed(description)
    await ctx.send(embed=embed)

# ============ COMMANDES GRADES ============
@bot.command()
@has_required_grade()
async def grades(ctx):
    lines = []
    
    if ctx.author.id == ADMIN_USER_ID:
        lines.append(f"──────────────")
        lines.append(f"🔰 ADMIN SPÉCIAL • Permission MAX")
    
    for grade, value in sorted(GRADES.items(), key=lambda x: x[1], reverse=True):
        emoji = {
            "Créateur++": "👑",
            "Créateur": "⭐",
            "Sys+": "🛠️",
            "Sys": "🔧",
            "Owner": "👑"
        }.get(grade, "•")
        
        lines.append(f"──────────────")
        lines.append(f"{emoji} {grade} • Permission {value}")
    
    lines.append(f"──────────────")
    embed = create_white_embed("HIÉRARCHIE DES GRADES\n\n" + "\n".join(lines))
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def myrole(ctx):
    if ctx.author.id == ADMIN_USER_ID:
        embed = create_white_embed(
            f"🔰 Tu es l'ADMIN SPÉCIAL\n\n"
            f"Tu as accès à toutes les commandes sans restrictions"
        )
    else:
        grade = get_user_grade(ctx.author)
        if grade:
            embed = create_white_embed(
                f"T'es gradé : {grade}\n\n"
                f"Fais `&perm` pour voir les commandes aux quels tu as accès"
            )
        else:
            embed = create_red_embed("Tu n'as aucun grade de la hiérarchie.")
    await ctx.send(embed=embed)

# ============ COMMANDES BLACKLIST ============
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
    
    if not identifier or not reason:
        embed = create_red_embed("**Usage Incorrecte**\nUsage : `&bl id/@ raison`")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    target_member, is_on_server = result
    
    existing = get_blacklist_user(target_member.id)
    if existing:
        embed = create_red_embed(f"Cet utilisateur est déjà dans la blacklist.")
        return await ctx.send(embed=embed)
    
    executor_grade = get_user_grade(ctx.author)
    
    if ctx.author.id == ADMIN_USER_ID:
        if target_member.id == ADMIN_USER_ID:
            embed = create_red_embed("Tu ne peux pas te blacklist toi-même.")
            return await ctx.send(embed=embed)
    else:
        if not executor_grade:
            embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
            return await ctx.send(embed=embed)
    
    if is_on_server:
        target_grade = get_user_grade(target_member)
        
        if target_grade == "Créateur++":
            embed = create_red_embed("Impossible de blacklist un **Créateur++**.")
            return await ctx.send(embed=embed)
        
        if not target_grade:
            target_grade = "Aucun grade"
            target_value = 0
        else:
            target_value = GRADES[target_grade]
        
        if ctx.author.id != ADMIN_USER_ID and GRADES[executor_grade] <= target_value:
            embed = create_red_embed("Eh Oh ? T'essaie de faire quoi ?")
            return await ctx.send(embed=embed)
    else:
        target_grade = "Inconnu (hors serveur)"
        target_value = 0
    
    if ctx.author.id != ADMIN_USER_ID and not is_in_whitelist(str(ctx.author.id)):
        can_bl, error_msg = check_bl_limit(str(ctx.author.id), executor_grade)
        if not can_bl:
            embed = create_red_embed(error_msg)
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
        target_grade,
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
    
    if is_on_server:
        embed = create_green_embed(f"{target_member.mention} a été blacklister par {ctx.author.mention}\nRaison : `{reason}`")
    else:
        embed = create_green_embed(f"L'utilisateur `{user_name}` a été blacklister par {ctx.author.mention}\nRaison : `{reason}`")
    
    await ctx.send(embed=embed)
    
    executor_display = "ADMIN SPÉCIAL" if ctx.author.id == ADMIN_USER_ID else f"{executor_grade}"
    
    if is_on_server:
        await send_log(ctx, "bl", {
            "Blacklist par": f"{ctx.author.mention} ({executor_display})",
            "Utilisateur BL": target_member.mention,
            "Raison": reason,
            "Statut": "Sur serveur"
        })
    else:
        await send_log(ctx, "bl", {
            "Blacklist par": f"{ctx.author.mention} ({executor_display})",
            "Utilisateur BL": f"{user_name} (ID: {target_member.id})",
            "Raison": reason,
            "Statut": "Hors serveur"
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
        embed = create_black_embed_with_title("MAUVAISE UTILISATION", "Usage : `&unbl id/@`")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    existing = get_blacklist_user(member.id)
    
    if not existing:
        embed = create_red_embed("Cet utilisateur n'est pas dans la blacklist.")
        return await ctx.send(embed=embed)
    
    if ctx.author.id != ADMIN_USER_ID:
        executor_grade = get_user_grade(ctx.author)
        if not executor_grade:
            embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
            return await ctx.send(embed=embed)
        
        stored_grade = existing[2]
        if stored_grade == "Créateur++" and executor_grade != "Créateur++":
            embed = create_red_embed(f"Vous n'avez pas les permissions nécessaires car cet utilisateur a été blacklister par un {stored_grade}.")
            return await ctx.send(embed=embed)
    
    unban_success = False
    if is_on_server:
        try:
            try:
                ban_entry = await ctx.guild.fetch_ban(discord.Object(id=member.id))
                await ctx.guild.unban(ban_entry.user, reason=f"Unblacklist par {ctx.author}")
                unban_success = True
                unban_msg = f"{member.mention} a bien été **retiré** de la blacklist et débanni."
            except discord.NotFound:
                unban_msg = f"{member.mention} a bien été **retiré** de la blacklist (n'était pas banni)."
        except discord.Forbidden:
            unban_msg = f"{member.mention} a bien été **retiré** de la blacklist (pas les permissions de unban)."
        except:
            unban_msg = f"{member.mention} a bien été **retiré** de la blacklist."
    else:
        unban_msg = f"L'utilisateur `{member.name}` a bien été **retiré** de la blacklist (hors serveur)."
    
    try:
        dm_message = (
            f"Vous avez été unbl de `Akusa` #🎐\n\n"
            f"Voici le lien du serveur : https://discord.gg/fH2ur9ffSa"
        )
        await member.send(dm_message)
    except:
        pass
    
    remove_from_blacklist(member.id)
    
    embed = create_green_embed(unban_msg)
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
@has_specific_grade("Créateur++")
async def unblall(ctx):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
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
    
    embed = create_green_embed(msg)
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
    
    items_per_page = 5
    pages = []
    
    for i in range(0, len(bl_data), items_per_page):
        description_lines = []
        items = bl_data[i:i+items_per_page]
        
        for item in items:
            user_id, user_name, grade, reason, added_by, added_by_name, banned, on_server, timestamp = item
            user_mention = f"<@{user_id}>"
            
            if grade == "None":
                grade = "Aucun grade"
            
            if not on_server:
                description_lines.append(f"{user_mention} — {grade} (hors serveur)")
            else:
                description_lines.append(f"{user_mention} — {grade}")
            
            description_lines.append(f"• Raison : {reason}")
            description_lines.append("")
        
        embed = create_white_embed("Liste des blacklist\n\n" + "\n".join(description_lines))
        embed.set_footer(text=f"Page {len(pages)+1}/{(len(bl_data)+items_per_page-1)//items_per_page} • {get_current_time_french()}")
        pages.append(embed)
    
    if len(pages) == 1:
        await ctx.send(embed=pages[0])
        return
    
    view = SimplePaginator(pages)
    await ctx.send(embed=pages[0], view=view)

@bot.command()
@has_required_grade()
async def blinfo(ctx, identifier: str):
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    existing = get_blacklist_user(member.id)
    
    if not existing:
        embed = create_red_embed("Cet utilisateur n'est pas dans la blacklist.")
        return await ctx.send(embed=embed)
    
    user_id, user_name, grade, reason, added_by, added_by_name, banned, on_server, timestamp = existing
    
    bl_by_grade = None
    try:
        if added_by:
            bl_by_member = await get_user_by_id_or_mention(ctx, str(added_by))
            if bl_by_member:
                bl_by_member_obj, _ = bl_by_member
                if isinstance(bl_by_member_obj, discord.Member):
                    bl_by_grade = get_user_grade(bl_by_member_obj)
    except:
        pass
    
    if not bl_by_grade and added_by == ADMIN_USER_ID:
        bl_by_grade = "Créateur++"
    
    hide_identity = False
    if bl_by_grade:
        if bl_by_grade in ["Créateur", "Créateur++"]:
            hide_identity = True
    
    if hide_identity:
        by_display = "**Masqué**"
        grade_display = "**Masqué**"
    else:
        by_display = f"<@{added_by}>" if added_by else "Inconnu"
        grade_display = grade if grade != "None" else "Aucun grade"
    
    status = "Hors serveur" if not on_server else "Sur serveur"
    
    embed = create_white_embed(
        f"BLACKLIST INFO\n\n"
        f"Blacklist : {member.mention}\n"
        f"Statut : {status}\n\n"
        f"Par : {by_display}\n"
        f"Grade : {grade_display}\n\n"
        f"Raison du BL :\n{reason}\n\n"
        f"Date : {timestamp}"
    )
    if hasattr(member, 'avatar') and member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

# ============ COMMANDE GRADE ============
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
            embed = create_red_embed("Utilisateur introuvable.")
            return await ctx.send(embed=embed)
        
        target_member, is_on_server = result
    
    if is_on_server and isinstance(target_member, discord.Member):
        grade = get_user_grade(target_member)
        
        if grade:
            embed = create_black_embed(f"{target_member.mention} a le grade **{grade}**")
        else:
            embed = create_black_embed(f"{target_member.mention} n'a aucun grade de la hiérarchie")
    else:
        embed = create_black_embed(f"{target_member.mention} n'est pas sur le serveur, impossible de vérifier son grade")
    
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def limits(ctx):
    lines = []
    
    for grade, limit in sorted(BL_LIMITS.items(), key=lambda x: GRADES.get(x[0], 0), reverse=True):
        emoji = {
            "Créateur++": "👑",
            "Créateur": "⭐",
            "Sys+": "🛠️",
            "Sys": "🔧",
            "Owner": "👑"
        }.get(grade, "•")
        
        if limit == 9999:
            limit_display = "Illimité"
        else:
            limit_display = str(limit)
        
        lines.append(f"{emoji} **{grade}** : {limit_display} BL/heure")
    
    lines.append(f"\n> La limite de bl par heure ce reset toute les **2 heures**")
    
    embed = create_white_embed("\n".join(lines))
    await ctx.send(embed=embed)

# ============ COMMANDES WHITELIST ============
@bot.command()
@has_specific_grade("Créateur++")
async def wl(ctx, identifier: str = None):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_member = replied_message.author
            identifier = str(target_member.id)
        except:
            pass
    
    if not identifier:
        embed = create_black_embed_with_title("MAUVAISE UTILISATION", "Usage : `&wl id/@`")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    if is_in_whitelist(member.id):
        if is_on_server:
            embed = create_red_embed(f"{member.mention} est déjà dans la whitelist.")
        else:
            embed = create_red_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) est déjà dans la whitelist.")
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
        embed = create_green_embed(f"{member.mention} ajouté à la whitelist.")
    else:
        embed = create_green_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) ajouté à la whitelist.")
    
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
@has_specific_grade("Créateur++")
async def unwl(ctx, identifier: str = None):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_member = replied_message.author
            identifier = str(target_member.id)
        except:
            pass
    
    if not identifier:
        embed = create_black_embed_with_title("MAUVAISE UTILISATION", "Usage : `&unwl id/@`")
        return await ctx.send(embed=embed)
    
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    removed = remove_from_whitelist(member.id)
    
    if removed:
        if is_on_server:
            embed = create_green_embed(f"{member.mention} retiré de la whitelist.")
        else:
            embed = create_green_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) retiré de la whitelist.")
        
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
            embed = create_red_embed(f"{member.mention} n'est pas dans la whitelist.")
        else:
            embed = create_red_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) n'est pas dans la whitelist.")
    
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def clearwl(ctx):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    count = clear_whitelist()
    
    if count == 0:
        embed = create_white_embed("La whitelist est déjà vide.")
    else:
        embed = create_green_embed(f"Whitelist vidée avec succès. {count} utilisateur(s) retiré(s).")
        
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

# ============ COMMANDES LOGS CONFIGURATION ============
@bot.command()
@has_specific_grade("Créateur++")
async def setlogs(ctx, channel: discord.TextChannel):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "general", channel.id)
    embed = create_green_embed(f"Salon de logs configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsbl(ctx, channel: discord.TextChannel):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "bl", channel.id)
    embed = create_green_embed(f"Salon de logs BL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsunbl(ctx, channel: discord.TextChannel):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "unbl", channel.id)
    embed = create_green_embed(f"Salon de logs UNBL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsrank(ctx, channel: discord.TextChannel):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "rank", channel.id)
    embed = create_green_embed(f"Salon de logs RANK configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogswl(ctx, channel: discord.TextChannel):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "wl", channel.id)
    embed = create_green_embed(f"Salon de logs WL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsunwl(ctx, channel: discord.TextChannel):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "unwl", channel.id)
    embed = create_green_embed(f"Salon de logs UNWL configuré : {channel.mention}")
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

# ============ COMMANDES ATTRIBUTION DE GRADES ============
def get_grade_name_from_key(grade_key: str) -> str:
    grade_map = {
        "owner": "Owner",
        "sys": "Sys",
        "sys+": "Sys+",
        "crea": "Créateur",
        "crea++": "Créateur++"
    }
    return grade_map.get(grade_key, grade_key)

@bot.command()
@has_required_grade()
async def rank(ctx, member: discord.Member = None, grade: str = None):
    if ctx.message.reference and ctx.message.reference.message_id and not member and not grade:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            member = replied_message.author
            content = ctx.message.content
            parts = content.split()
            if len(parts) >= 2:
                grade = parts[1]
        except:
            pass
    elif ctx.message.reference and ctx.message.reference.message_id and member and not grade:
        content = ctx.message.content
        parts = content.split()
        if len(parts) >= 3:
            grade = parts[2]
    
    if not member or not grade:
        embed = create_red_embed("**Usage Incorrecte**\nUsage : `&rank @user/id grade`\nGrades : owner, sys, sys+, crea, crea++")
        return await ctx.send(embed=embed)
    
    grade = grade.lower()
    valid_grades = ["owner", "sys", "sys+", "crea", "crea++"]
    
    if grade not in valid_grades:
        embed = create_red_embed("Grade invalide. Utilise : owner, sys, sys+, crea, crea++")
        return await ctx.send(embed=embed)
    
    if ctx.author.id == ADMIN_USER_ID:
        pass
    else:
        executor_grade = get_user_grade(ctx.author)
        
        if not executor_grade:
            embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
            return await ctx.send(embed=embed)
        
        if executor_grade == "Créateur++":
            pass
        elif executor_grade == "Créateur":
            if grade not in ["owner", "sys", "sys+", "crea"]:
                embed = create_red_embed("Vous n'avez pas les permissions nécessaires pour attribuer ce grade.")
                return await ctx.send(embed=embed)
            
            if not is_in_whitelist(str(ctx.author.id)):
                embed = create_red_embed("Vous n'êtes pas dans la whitelist.")
                return await ctx.send(embed=embed)
        else:
            embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
            return await ctx.send(embed=embed)
    
    if ctx.author.id != ADMIN_USER_ID:
        executor_grade_value = GRADES[executor_grade]
        target_grade_value = GRADES[get_grade_name_from_key(grade)]
        
        if target_grade_value >= executor_grade_value:
            embed = create_black_embed("Tu ne peux pas donner un grade égal ou supérieur au tien")
            return await ctx.send(embed=embed)
    
    role_id = GRADE_TO_ROLE_ID.get(grade)
    if not role_id:
        embed = create_red_embed(f"Rôle {grade} introuvable.")
        return await ctx.send(embed=embed)
    
    role = ctx.guild.get_role(role_id)
    if not role:
        embed = create_red_embed(f"Rôle {grade} introuvable.")
        return await ctx.send(embed=embed)
    
    try:
        await member.add_roles(role)
        
        for other_role_id in ROLE_IDS_TO_GRADES.keys():
            if other_role_id != role_id:
                other_role = ctx.guild.get_role(other_role_id)
                if other_role and other_role in member.roles:
                    await member.remove_roles(other_role)
        
        grade_display = get_grade_name_from_key(grade)
        embed = create_green_embed(f"{member.mention} a bien reçu le grade {grade_display}")
        await ctx.send(embed=embed)
        
        executor_display = "ADMIN SPÉCIAL" if ctx.author.id == ADMIN_USER_ID else f"{executor_grade}"
        await send_log(ctx, "rank", {
            "Donné par": f"{ctx.author.mention} ({executor_display})",
            "À": member.mention,
            "Grade donné": grade_display
        })
        
    except discord.Forbidden:
        embed = create_red_embed("Impossible d'ajouter le rôle. Permissions manquantes.")
        await ctx.send(embed=embed)
    except discord.HTTPException:
        embed = create_red_embed("Erreur technique. Impossible d'ajouter le rôle.")
        await ctx.send(embed=embed)

# ============ COMMANDE CHANGELIMIT ============
@bot.command()
@has_specific_grade("Créateur++")
async def changelimit(ctx, grade: str, limit: int):
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    grade = grade.lower()
    valid_grades = ["owner", "sys", "sys+", "crea", "crea++"]
    
    if grade not in valid_grades:
        embed = create_red_embed(f"Grade invalide. Grades : {', '.join(valid_grades)}")
        return await ctx.send(embed=embed)
    
    if limit < 0 or limit > 9999:
        embed = create_red_embed("Limite invalide. Utilise un nombre entre 0 et 9999.")
        return await ctx.send(embed=embed)
    
    grade_display = get_grade_name_from_key(grade)
    
    BL_LIMITS[grade_display] = limit
    
    embed = create_green_embed(f"Limite de BL par heure pour **{grade_display}** définie à **{limit}**.")
    await ctx.send(embed=embed)

# ============ COMMANDE PING ============
@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = create_white_embed(f"Pong! Latence : **{latency}ms**")
    await ctx.send(embed=embed)

# ============ LANCEMENT ============
if __name__ == "__main__":
    print("🚀 Démarrage du bot Akusa...")
    bot.run(TOKEN)