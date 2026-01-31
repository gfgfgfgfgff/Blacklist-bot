import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional

# ============ PAGINATION SIMPLE ============
class SimplePaginator(discord.ui.View):
    def __init__(self, embeds, timeout=60):
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
        if get_user_grade(ctx.author):
            return True
        return False
    return commands.check(predicate)

def has_specific_grade(required_grade: str):
    async def predicate(ctx):
        user_grade = get_user_grade(ctx.author)
        if not user_grade:
            return False
        
        user_value = GRADES[user_grade]
        required_value = GRADES[required_grade]
        
        if user_value >= required_value:
            return True
        return False
    return commands.check(predicate)

# ============ CONFIGURATION ============
TOKEN = os.getenv("TOKEN")
PREFIX = "&"
THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/1467065928024985815/1467071653023453308/IMG_9048.jpg"
SUPPORT_ID = 1399234120214909010
LOG_THUMBNAIL = "https://cdn.discordapp.com/attachments/1466619652288417901/1467113570969063534/IMG_1620.jpg"

# IDs des rôles
CREATOR_PP_ROLE_ID = 1466459905736183879
CREATOR_ROLE_ID = 1466460761764265984
SYS_PLUS_ROLE_ID = 1466515541828309195
SYS_ROLE_ID = 1466462217808642263
OWNER_ROLE_ID = 1466773492388073482

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

# ============ FICHIERS ============
BLACKLIST_FILE = "blacklist.json"
LOGS_FILE = "logs_config.json"
WHITELIST_FILE = "whitelist.json"
BL_LIMITS_FILE = "bl_limits.json"
GRADE_LIMITS_FILE = "grade_limits.json"

def load_json(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump({}, f)
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# ============ FONCTIONS UTILITAIRES ============
def get_user_grade(member: discord.Member) -> Optional[str]:
    for role in member.roles:
        if role.id in ROLE_IDS_TO_GRADES:
            return ROLE_IDS_TO_GRADES[role.id]
    return None

def create_black_embed(description: str) -> discord.Embed:
    embed = discord.Embed(description=description, color=0x000000)
    embed.set_footer(text=get_current_time())
    return embed

def create_white_embed(description: str) -> discord.Embed:
    embed = discord.Embed(description=description, color=0xFFFFFF)
    embed.set_footer(text=get_current_time())
    return embed

def create_red_embed(title: str = None, description: str = None) -> discord.Embed:
    embed = discord.Embed(color=0xFF0000)
    if title:
        embed.title = title
    if description:
        embed.description = description
    embed.set_thumbnail(url=THUMBNAIL_URL)
    return embed

def create_green_log_embed(title: str, fields: dict, thumbnail_url: str = None) -> discord.Embed:
    embed = discord.Embed(title=title, color=0x00FF00)
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    embed.set_footer(text=get_current_time())
    return embed

def get_current_time():
    return datetime.now().strftime("%d/%m/%Y - %H:%M:%S")

# ============ LIMITES BLACKLIST ============
BL_LIMITS = {
    "Owner": 3,
    "Sys": 6,
    "Sys+": 8,
    "Créateur": 15,
    "Créateur++": 9999
}

BL_COOLDOWN = 7200  # 2 heures en secondes

def check_bl_limit(user_id: str, grade: str) -> tuple[bool, str]:
    data = load_json(BL_LIMITS_FILE)
    user_id = str(user_id)
    
    if user_id not in data:
        data[user_id] = {"count": 0, "last_reset": datetime.now().isoformat()}
        save_json(BL_LIMITS_FILE, data)
        return True, ""
    
    user_data = data[user_id]
    last_reset = datetime.fromisoformat(user_data["last_reset"])
    
    # Reset si 2 heures écoulées
    if datetime.now() - last_reset > timedelta(seconds=BL_COOLDOWN):
        user_data["count"] = 0
        user_data["last_reset"] = datetime.now().isoformat()
        save_json(BL_LIMITS_FILE, data)
        return True, ""
    
    limit = BL_LIMITS.get(grade, 3)
    if user_data["count"] >= limit:
        time_left = last_reset + timedelta(seconds=BL_COOLDOWN) - datetime.now()
        minutes_left = int(time_left.total_seconds() // 60)
        return False, f"Vous avez atteint le max de bl par heure, ressayez dans {minutes_left} minutes"
    
    return True, ""

def increment_bl_count(user_id: str):
    data = load_json(BL_LIMITS_FILE)
    user_id = str(user_id)
    
    if user_id not in data:
        data[user_id] = {"count": 1, "last_reset": datetime.now().isoformat()}
    else:
        data[user_id]["count"] += 1
    
    save_json(BL_LIMITS_FILE, data)

# ============ LOGS ============
async def send_log(ctx, log_type: str, fields: dict, thumbnail_url: str = None):
    logs_data = load_json(LOGS_FILE)
    guild_id = str(ctx.guild.id)
    
    # Cherche d'abord le salon spécifique
    specific_key = f"{log_type}_channel"
    if specific_key in logs_data.get(guild_id, {}):
        channel_id = logs_data[guild_id][specific_key]
    # Sinon cherche le salon général
    elif "general_channel" in logs_data.get(guild_id, {}):
        channel_id = logs_data[guild_id]["general_channel"]
    else:
        return
    
    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except:
            return
    
    title_map = {
        "bl": "**__BL__**",
        "unbl": "**__UNBL__**",
        "rank": "ATTRIBUTION DE GRADE",
        "wl": "**__WL__**",
        "unwl": "**__UNWL__**"
    }
    
    title = title_map.get(log_type, log_type.upper())
    embed = create_green_log_embed(title, fields, thumbnail_url)
    
    try:
        await channel.send(embed=embed)
    except:
        pass

# ============ WHITELIST ============
def is_in_whitelist(user_id: str, wl_type: str) -> bool:
    data = load_json(WHITELIST_FILE)
    return user_id in data.get(wl_type, [])

def add_to_whitelist(user_id: str, wl_type: str):
    data = load_json(WHITELIST_FILE)
    if wl_type not in data:
        data[wl_type] = []
    if user_id not in data[wl_type]:
        data[wl_type].append(user_id)
    save_json(WHITELIST_FILE, data)

def remove_from_whitelist(user_id: str, wl_type: str = None):
    data = load_json(WHITELIST_FILE)
    removed = False
    
    if wl_type:
        if wl_type in data and user_id in data[wl_type]:
            data[wl_type].remove(user_id)
            removed = True
    else:
        for wl_type_key in data:
            if user_id in data[wl_type_key]:
                data[wl_type_key].remove(user_id)
                removed = True
    
    if removed:
        save_json(WHITELIST_FILE, data)
    return removed

# ============ LIMITES DE GRADE ============
def check_grade_limit(guild_id: str, grade_type: str) -> tuple[bool, str]:
    data = load_json(GRADE_LIMITS_FILE)
    guild_id = str(guild_id)
    
    if guild_id not in data or grade_type not in data[guild_id]:
        return True, ""
    
    limit = data[guild_id][grade_type]
    role_id = GRADE_TO_ROLE_ID.get(grade_type)
    
    if not role_id:
        return True, ""
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return True, ""
    
    role = guild.get_role(role_id)
    if not role:
        return True, ""
    
    members_with_role = len([m for m in guild.members if role in m.roles])
    
    if members_with_role >= limit:
        return False, f"Limite de {grade_type} atteinte (max: {limit})"
    
    return True, ""

# ============ ÉVÉNEMENTS ============
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

# ============ COMMANDES HELP ============
@bot.command()
@has_required_grade()
async def help(ctx):
    # Page 1
    embed1 = create_red_embed()
    embed1.title = "🤖 BOT BLACKLIST"
    embed1.description = "📍 **Page 1/2 - MODÉRATION**\n"
    embed1.add_field(
        name="🔨 **Commandes de Modération**",
        value=(
            "• `&bl @user raison` - Blacklist\n"
            "• `&unbl @user` - Unblacklist\n"
            "• `&bllist` - Liste des blacklist\n"
            "• `&blinfo @user` - Infos blacklist"
        ),
        inline=False
    )
    
    # Page 2
    embed2 = create_red_embed()
    embed2.title = "🤖 BOT BLACKLIST"
    embed2.description = "📍 **Page 2/2 - INFORMATION**\n"
    embed2.add_field(
        name="📊 **Commandes d'information**",
        value=(
            "• `&grades` - Hiérarchie des grades\n"
            "• `&myrole` - Vérifier ses rôles\n"
            "• `&wllist` - Voir les whitelists"
        ),
        inline=False
    )
    embed2.add_field(
        name="👑 **Créateur++ uniquement**",
        value=(
            "• `&setlogs #salon` - Configurer logs\n"
            "• `&wl @user type` - Whitelist\n"
            "• `&unwl @user` - Retirer WL"
        ),
        inline=False
    )
    embed2.add_field(
        name="🎖️ **Attribution de grades**",
        value=(
            "• `&rank @user grade` - Donner un grade\n"
            "  _(owner, sys, sys+)_"
        ),
        inline=False
    )
    
    view = SimplePaginator([embed1, embed2])
    await ctx.send(embed=embed1, view=view)

@bot.command()
@has_required_grade()
async def help_logs(ctx):
    """Affiche l'aide pour les commandes de logs"""
    embed = create_black_embed(
        "Logs\n\n"
        "> Pour définir un salon logs vous devez mettre obligatoirement le type et le salon\n"
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

# ============ COMMANDES GRADES ============
@bot.command()
@has_required_grade()
async def grades(ctx):
    """Affiche la hiérarchie des grades"""
    lines = []
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
    embed = create_white_embed("📊 HIÉRARCHIE DES GRADES\n\n" + "\n".join(lines))
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def myrole(ctx):
    """Vérifie tes rôles"""
    grade = get_user_grade(ctx.author)
    if grade:
        embed = create_white_embed(
            f"T'es gradé : {grade}\n\n"
            f"Fais `&myrole` pour voir les commandes aux quel ta acces"
        )
    else:
        embed = create_black_embed("Tu n'as aucun grade de la hiérarchie.")
    await ctx.send(embed=embed)

# ============ COMMANDES BLACKLIST ============
@bot.command()
@has_required_grade()
async def bl(ctx, member: Optional[discord.Member] = None, *, reason: str = None):
    """Blacklist un utilisateur avec raison (peut répondre à un message)"""
    # Vérifier si c'est une réponse à un message
    if ctx.message.reference and ctx.message.reference.message_id:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            member = replied_message.author
        except:
            pass
    
    # Vérifications
    if not member:
        embed = create_black_embed("Vous devez mentionner un utilisateur ou répondre à son message.")
        return await ctx.send(embed=embed)
    
    if not reason:
        embed = create_black_embed("Vous devez préciser une raison.")
        return await ctx.send(embed=embed)
    
    # Vérification des grades
    executor_grade = get_user_grade(ctx.author)
    target_grade = get_user_grade(member)
    
    if not executor_grade:
        embed = create_black_embed("Vous n'avez pas les permissions nécessaires.")
        return await ctx.send(embed=embed)
    
    if target_grade == "Créateur++":
        embed = create_black_embed("Impossible de blacklist un **Créateur++**.")
        return await ctx.send(embed=embed)
    
    # Vérifier la limite BL
    can_bl, error_msg = check_bl_limit(ctx.author.id, executor_grade)
    if not can_bl:
        embed = create_black_embed(error_msg)
        return await ctx.send(embed=embed)
    
    if not target_grade:
        target_grade = "Aucun grade"
        target_value = 0
    else:
        target_value = GRADES[target_grade]
    
    if GRADES[executor_grade] <= target_value:
        embed = create_black_embed("Eh Oh ? T'essaie de faire quoi ?")
        return await ctx.send(embed=embed)
    
    # Ban automatique
    try:
        await member.ban(reason=f"Blacklist par {ctx.author}: {reason}")
        ban_success = True
    except discord.Forbidden:
        ban_success = False
    except discord.HTTPException:
        ban_success = False
    
    # Sauvegarde blacklist
    bl_data = load_json(BLACKLIST_FILE)
    bl_data[str(member.id)] = {
        "grade": target_grade if target_grade != "Aucun grade" else "None",
        "reason": reason,
        "by": ctx.author.id,
        "banned": ban_success,
        "timestamp": get_current_time()
    }
    save_json(BLACKLIST_FILE, bl_data)
    
    # Incrémenter le compteur BL
    increment_bl_count(ctx.author.id)
    
    # Envoi DM à la personne blacklistée
    try:
        dm_message = (
            f"Vous avez été blacklisté de `Akusa #🎐` pour `{reason}`\n\n"
            f"Rejoignez le serveur prison d'Akusa pour vous faire unbl\n"
            f"lien : https://discord.gg/Cr8K2N48fe"
        )
        await member.send(dm_message)
    except:
        pass
    
    # Réponse publique
    embed = create_white_embed(f"{member.mention} a etait blacklister par {ctx.author.mention}\nRaison : `{reason}`")
    await ctx.send(embed=embed)
    
    # Log
    await send_log(ctx, "bl", {
        "Blacklist par": f"{ctx.author.mention} ({executor_grade})",
        "Utilisateur BL": member.mention,
        "Raison": reason
    }, LOG_THUMBNAIL)

@bot.command()
@has_required_grade()
async def unbl(ctx, member: discord.Member):
    """Unblacklist un utilisateur"""
    bl_data = load_json(BLACKLIST_FILE)
    uid = str(member.id)
    
    if uid not in bl_data:
        embed = create_black_embed("Cet utilisateur n'est pas blacklist.")
        return await ctx.send(embed=embed)
    
    # Vérification des grades
    executor_grade = get_user_grade(ctx.author)
    if not executor_grade:
        embed = create_black_embed("Vous n'avez pas les permissions nécessaires.")
        return await ctx.send(embed=embed)
    
    stored_grade = bl_data[uid]["grade"]
    if stored_grade == "Créateur++" and executor_grade != "Créateur++":
        embed = create_black_embed("Seul un **Créateur++** peut unbl un autre Créateur++.")
        return await ctx.send(embed=embed)
    
    # Unban automatique
    try:
        async for ban_entry in ctx.guild.bans():
            if ban_entry.user.id == member.id:
                await ctx.guild.unban(ban_entry.user, reason=f"Unblacklist par {ctx.author}")
                unban_msg = f"{member.mention} a été retiré de la blacklist et **UNBANNI**."
                break
        else:
            unban_msg = f"{member.mention} a été retiré de la blacklist (n'était pas banni)."
    except discord.Forbidden:
        unban_msg = f"{member.mention} a été retiré de la blacklist (pas les permissions de unban)."
    except:
        unban_msg = f"{member.mention} a été retiré de la blacklist."
    
    # Envoi DM à la personne unblacklistée
    try:
        dm_message = (
            f"Vous avez été unblacklisté de `Akusa #🎐`\n\n"
            f"Vous pouvez désormais revenir sur le serveur.\n"
            f"Lien d'invitation : https://discord.gg/TfSDNp3V2x"
        )
        await member.send(dm_message)
    except:
        pass
    
    # Suppression blacklist
    del bl_data[uid]
    save_json(BLACKLIST_FILE, bl_data)
    
    embed = create_white_embed(unban_msg)
    await ctx.send(embed=embed)
    
    # Log
    await send_log(ctx, "unbl", {
        "Unblacklist par": ctx.author.mention,
        "Utilisateur unBL": member.mention
    }, LOG_THUMBNAIL)

@bot.command()
@has_specific_grade("Créateur++")
async def unblall(ctx):
    """Retirer tous les utilisateurs de la blacklist (Créateur++ uniquement)"""
    bl_data = load_json(BLACKLIST_FILE)
    count = len(bl_data)
    
    # Unban tous les utilisateurs blacklistés
    unbanned_count = 0
    try:
        async for ban_entry in ctx.guild.bans():
            if str(ban_entry.user.id) in bl_data:
                await ctx.guild.unban(ban_entry.user, reason=f"Unblacklist all par {ctx.author}")
                unbanned_count += 1
    except:
        pass
    
    # Vider la blacklist
    bl_data.clear()
    save_json(BLACKLIST_FILE, bl_data)
    
    # Message de confirmation
    if count == 0:
        msg = "0 utilisateur a été unblacklist avec succès"
    elif count == 1:
        msg = "1 utilisateur a été unblacklist avec succès"
    else:
        msg = f"{count} utilisateurs ont été unblacklist avec succès"
    
    embed = create_white_embed(msg)
    await ctx.send(embed=embed)
    
    # Log
    await send_log(ctx, "unbl", {
        "Unblacklist par": ctx.author.mention,
        "Action": "Tout unblacklist",
        "Nombre": str(count)
    }, LOG_THUMBNAIL)

@bot.command()
@has_required_grade()
async def bllist(ctx):
    """Liste des utilisateurs blacklistés"""
    bl_data = load_json(BLACKLIST_FILE)
    
    if not bl_data:
        embed = create_black_embed("Aucun utilisateur blacklist")
        return await ctx.send(embed=embed)
    
    # Crée les pages
    items_per_page = 5
    all_items = list(bl_data.items())
    pages = []
    
    for i in range(0, len(all_items), items_per_page):
        description_lines = []
        items = all_items[i:i+items_per_page]
        
        for uid, data in items:
            user_mention = f"<@{uid}>"
            grade = data.get("grade", "Inconnu")
            if grade == "None":
                grade = "Aucun grade"
            reason = data.get("reason", "Non spécifiée")
            
            description_lines.append(f"{user_mention} — {grade}")
            description_lines.append(f"• Raison : {reason}")
            description_lines.append("")
        
        embed = create_white_embed("📋 Liste des blacklist\n\n" + "\n".join(description_lines))
        embed.set_footer(text=f"Page {len(pages)+1}/{(len(all_items)+items_per_page-1)//items_per_page} • {get_current_time()}")
        pages.append(embed)
    
    # Si une seule page, envoie simple
    if len(pages) == 1:
        await ctx.send(embed=pages[0])
        return
    
    # Sinon pagination
    view = SimplePaginator(pages)
    await ctx.send(embed=pages[0], view=view)

@bot.command()
@has_required_grade()
async def blinfo(ctx, member: discord.Member):
    """Informations sur une blacklist"""
    bl_data = load_json(BLACKLIST_FILE)
    uid = str(member.id)
    
    if uid not in bl_data:
        embed = create_black_embed("Cet utilisateur n'est pas blacklist.")
        return await ctx.send(embed=embed)
    
    data = bl_data[uid]
    grade = get_user_grade(member)
    
    embed = create_white_embed(
        f"📄 BLACKLIST INFO\n\n"
        f"Blacklist : {member.mention}\n\n"
        f"Par : <@{data['by']}> ({data['grade']})\n\n"
        f"Raison du BL :\n{data['reason']}"
    )
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

# ============ COMMANDES WHITELIST ============
@bot.command()
@has_specific_grade("Créateur++")
async def wl(ctx, member: discord.Member, wl_type: str):
    """Ajouter un utilisateur à la whitelist (Créateur++ uniquement)"""
    wl_type = wl_type.lower()
    valid_types = ["owner", "sys", "sys+", "crea"]
    
    if wl_type not in valid_types:
        embed = create_black_embed(f"Type invalide. Utilise : {', '.join(valid_types)}")
        return await ctx.send(embed=embed)
    
    if is_in_whitelist(str(member.id), wl_type):
        embed = create_black_embed(f"{member.mention} est déjà dans la whitelist {wl_type}.")
        return await ctx.send(embed=embed)
    
    add_to_whitelist(str(member.id), wl_type)
    embed = create_white_embed(f"{member.mention} ajouté à la whitelist {wl_type}.")
    await ctx.send(embed=embed)
    
    # Log
    await send_log(ctx, "wl", {
        "Ajouté par": ctx.author.mention,
        "À": member.mention,
        "Type": wl_type
    }, LOG_THUMBNAIL)

@bot.command()
@has_specific_grade("Créateur++")
async def unwl(ctx, member: discord.Member):
    """Retirer un utilisateur de la whitelist (Créateur++ uniquement)"""
    removed = remove_from_whitelist(str(member.id))
    
    if removed:
        embed = create_white_embed(f"{member.mention} retiré de la whitelist.")
        
        # Log
        await send_log(ctx, "unwl", {
            "Retiré par": ctx.author.mention,
            "De": member.mention
        }, LOG_THUMBNAIL)
    else:
        embed = create_black_embed(f"{member.mention} n'est dans aucune whitelist.")
    
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def wllist(ctx):
    """Voir les whitelists"""
    data = load_json(WHITELIST_FILE)
    
    description_lines = ["📋 Whitelists\n"]
    grade_order = ["crea++", "crea", "sys+", "sys", "owner"]
    grade_names = {
        "crea++": "👑 Créateur++",
        "crea": "⭐ Créateur",
        "sys+": "🛠️ Sys+",
        "sys": "🔧 Sys",
        "owner": "👑 Owner"
    }
    
    for grade_type in grade_order:
        grade_name = grade_names.get(grade_type, grade_type)
        members = data.get(grade_type, [])
        
        description_lines.append(f"\n{grade_name}")
        if members:
            for uid in members:
                description_lines.append(f"• <@{uid}>")
        else:
            description_lines.append("Aucun")
    
    embed = create_white_embed("\n".join(description_lines))
    await ctx.send(embed=embed)

# ============ COMMANDES LOGS CONFIGURATION ============
def set_log_channel(guild_id: str, log_type: str, channel_id: int):
    data = load_json(LOGS_FILE)
    guild_id = str(guild_id)
    
    if guild_id not in data:
        data[guild_id] = {}
    
    if log_type == "general":
        data[guild_id]["general_channel"] = channel_id
    else:
        data[guild_id][f"{log_type}_channel"] = channel_id
    
    save_json(LOGS_FILE, data)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogs(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs général (Créateur++ uniquement)"""
    set_log_channel(ctx.guild.id, "general", channel.id)
    embed = create_white_embed(f"Salon de logs configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsbl(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs BL (Créateur++ uniquement)"""
    set_log_channel(ctx.guild.id, "bl", channel.id)
    embed = create_white_embed(f"Salon de logs BL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsunbl(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs UNBL (Créateur++ uniquement)"""
    set_log_channel(ctx.guild.id, "unbl", channel.id)
    embed = create_white_embed(f"Salon de logs UNBL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsrank(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs RANK (Créateur++ uniquement)"""
    set_log_channel(ctx.guild.id, "rank", channel.id)
    embed = create_white_embed(f"Salon de logs RANK configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogswl(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs WL (Créateur++ uniquement)"""
    set_log_channel(ctx.guild.id, "wl", channel.id)
    embed = create_white_embed(f"Salon de logs WL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsunwl(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs UNWL (Créateur++ uniquement)"""
    set_log_channel(ctx.guild.id, "unwl", channel.id)
    embed = create_white_embed(f"Salon de logs UNWL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def logs(ctx):
    """Voir la configuration des salons de logs"""
    data = load_json(LOGS_FILE)
    guild_id = str(ctx.guild.id)
    
    if guild_id not in data:
        embed = create_black_embed("Aucun salon de logs configuré.")
        return await ctx.send(embed=embed)
    
    guild_data = data[guild_id]
    
    lines = ["Logs\n"]
    log_types = {
        "general_channel": "General",
        "bl_channel": "Bl",
        "unbl_channel": "Unbl",
        "rank_channel": "Rank",
        "wl_channel": "Wl",
        "unwl_channel": "Unwl"
    }
    
    for key, name in log_types.items():
        channel_id = guild_data.get(key)
        if channel_id:
            lines.append(f"{name} : <#{channel_id}>")
        else:
            lines.append(f"{name} : Non configuré")
    
    embed = create_black_embed("\n".join(lines))
    await ctx.send(embed=embed)

# ============ COMMANDES ATTRIBUTION DE GRADES ============
@bot.command()
@has_required_grade()
async def rank(ctx, member: discord.Member, grade: str):
    """Donner un grade à un utilisateur"""
    grade = grade.lower()
    valid_grades = ["owner", "sys", "sys+", "crea", "crea++"]
    
    if grade not in valid_grades:
        embed = create_black_embed("Grade invalide. Utilise : owner, sys, sys+")
        return await ctx.send(embed=embed)
    
    # Vérification des permissions
    executor_grade = get_user_grade(ctx.author)
    
    if not executor_grade:
        embed = create_black_embed("Vous n'avez pas les permissions nécessaires pour attribuer un grade.")
        return await ctx.send(embed=embed)
    
    # Créateur++ peut tout donner sans whitelist
    if executor_grade == "Créateur++":
        pass  # Pas de vérification de whitelist
    # Créateur peut donner owner/sys/sys+ mais doit être dans la whitelist
    elif executor_grade == "Créateur":
        if grade not in ["owner", "sys", "sys+"]:
            embed = create_black_embed("Vous n'avez pas les permissions nécessaires pour attribuer ce grade.")
            return await ctx.send(embed=embed)
        
        if not is_in_whitelist(str(ctx.author.id), grade):
            embed = create_black_embed(f"Vous n'êtes pas dans la whitelist {grade}.")
            return await ctx.send(embed=embed)
    # Autres grades ne peuvent pas donner de grades
    else:
        embed = create_black_embed("Vous n'avez pas les permissions nécessaires pour attribuer un grade.")
        return await ctx.send(embed=embed)
    
    # Vérifier la limite de grade
    can_give, error_msg = check_grade_limit(ctx.guild.id, grade)
    if not can_give:
        embed = create_black_embed(error_msg)
        return await ctx.send(embed=embed)
    
    # Récupérer le rôle
    role_id = GRADE_TO_ROLE_ID.get(grade)
    if not role_id:
        embed = create_black_embed(f"Rôle {grade} introuvable.")
        return await ctx.send(embed=embed)
    
    role = ctx.guild.get_role(role_id)
    if not role:
        embed = create_black_embed(f"Rôle {grade} introuvable.")
        return await ctx.send(embed=embed)
    
    # Donner le rôle
    try:
        await member.add_roles(role)
        
        # Retirer les anciens grades si nécessaire (optionnel)
        for other_role_id in ROLE_IDS_TO_GRADES.keys():
            if other_role_id != role_id:
                other_role = ctx.guild.get_role(other_role_id)
                if other_role and other_role in member.roles:
                    await member.remove_roles(other_role)
        
        grade_name_map = {
            "owner": "Owner",
            "sys": "Sys",
            "sys+": "Sys+",
            "crea": "Créateur",
            "crea++": "Créateur++"
        }
        
        grade_display = grade_name_map.get(grade, grade)
        embed = create_white_embed(f"{member.mention} a bien recu le grade {grade_display}")
        await ctx.send(embed=embed)
        
        # Log
        await send_log(ctx, "rank", {
            "Donné par": f"{ctx.author.mention} ({executor_grade})",
            "À": member.mention,
            "Grade donné": grade_display
        })
        
    except discord.Forbidden:
        embed = create_black_embed("Impossible d'ajouter le rôle. Permissions manquantes.")
        await ctx.send(embed=embed)
    except discord.HTTPException:
        embed = create_black_embed("Erreur technique. Impossible d'ajouter le rôle.")
        await ctx.send(embed=embed)

# ============ COMMANDE CHANGELIMIT ============
@bot.command()
@has_specific_grade("Créateur++")
async def changelimit(ctx, grade: str, limit: int):
    """Changer la limite de membres pour un grade (Créateur++ uniquement)"""
    grade = grade.lower()
    valid_grades = ["owner", "sys", "sys+", "crea"]
    
    if grade not in valid_grades:
        embed = create_black_embed(f"Grade invalide. Grades : {', '.join(valid_grades)}")
        return await ctx.send(embed=embed)
    
    if limit < 1 or limit > 100:
        embed = create_black_embed("Nombre invalide. Utilise un nombre entre 1 et 100.")
        return await ctx.send(embed=embed)
    
    data = load_json(GRADE_LIMITS_FILE)
    guild_id = str(ctx.guild.id)
    
    if guild_id not in data:
        data[guild_id] = {}
    
    data[guild_id][grade] = limit
    save_json(GRADE_LIMITS_FILE, data)
    
    grade_name_map = {
        "owner": "Owner",
        "sys": "Sys",
        "sys+": "Sys+",
        "crea": "Créateur"
    }
    
    grade_display = grade_name_map.get(grade, grade)
    embed = create_white_embed(f"Limite {grade_display} définie à {limit} membres.")
    await ctx.send(embed=embed)

# ============ COMMANDE PING ============
@bot.command()
async def ping(ctx):
    """Vérifie la latence du bot"""
    latency = round(bot.latency * 1000)
    embed = create_white_embed(f"🏓 Pong! Latence : **{latency}ms**")
    await ctx.send(embed=embed)

# ============ LANCEMENT ============
if __name__ == "__main__":
    bot.run(TOKEN)
