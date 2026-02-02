import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

# ============ ADMIN USER ID ============
ADMIN_USER_ID = 1399234120214909010  # ID de l'utilisateur avec accès complet

# ============ PAGINATION SIMPLE ============
class SimplePaginator(discord.ui.View):
    def __init__(self, embeds, timeout=3600):  # 1 heure = 3600 secondes
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

# ============ VÉRIFICATIONS DE PERMISSIONS MODIFIÉES ============
def has_required_grade():
    async def predicate(ctx):
        # L'admin a toujours accès
        if ctx.author.id == ADMIN_USER_ID:
            return True
        
        if get_user_grade(ctx.author):
            return True
        
        # Message d'erreur noir pour les non-autorisés
        embed = discord.Embed(
            description="Malheureusement tu n'as pas les permissions nécessaires",
            color=0x000000
        )
        await ctx.send(embed=embed)
        return False
    return commands.check(predicate)

def has_specific_grade(required_grade: str):
    async def predicate(ctx):
        # L'admin a toujours accès
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

# ============ CONFIGURATION ============
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("❌ ERREUR : Le token Discord n'est pas défini !")
    print("Assure-toi d'avoir défini la variable d'environnement 'TOKEN' sur Railway.")
    exit(1)

PREFIX = "&"
THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/1467151867191496808/1467232922938638479/IMG_1620.jpg?ex=697fa2a4&is=697e5124&hm=a712241a364f6b68dc031cac0860e5e9b9af3f2df3e69c8f3b14e1817852ccde&"
SUPPORT_ID = 1399234120214909010
LOG_THUMBNAIL = THUMBNAIL_URL

# IDs des rôles
CREATOR_PP_ROLE_ID = 1466459905736183879  # @Compte Couronne
CREATOR_ROLE_ID = 1466514624718307562     # @<3
SYS_PLUS_ROLE_ID = 1466515541828309195    # @Akusa
SYS_ROLE_ID = 1466462217808642263         # @2026
OWNER_ROLE_ID = 1466773492388073482       # @⚫️ ╏ Perm Bl

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

# ============ FONCTIONS UTILITAIRES MODIFIÉES ============
def get_user_grade(member: discord.Member) -> Optional[str]:
    # L'admin est considéré comme Créateur++ pour la hiérarchie
    if member.id == ADMIN_USER_ID:
        return "Créateur++"
    
    highest_grade = None
    highest_value = -1
    
    for role in member.roles:
        if role.id in ROLE_IDS_TO_GRADES:
            grade_name = ROLE_IDS_TO_GRADES[role.id]
            grade_value = GRADES[grade_name]
            
            # Garder le grade le plus élevé
            if grade_value > highest_value:
                highest_value = grade_value
                highest_grade = grade_name
    
    return highest_grade

async def get_user_by_id_or_mention(ctx, identifier: str):
    """Récupère un utilisateur par ID ou mention, même hors serveur"""
    try:
        # Essayer de récupérer par mention
        if identifier.startswith('<@') and identifier.endswith('>'):
            # Enlever <@ et >
            user_id = identifier[2:-1]
            # Enlever le ! si c'est une mention de nickname
            if user_id.startswith('!'):
                user_id = user_id[1:]
            try:
                user_id = int(user_id)
            except ValueError:
                return None
        else:
            # Essayer de récupérer par ID direct
            user_id = int(identifier)
        
        # Essayer d'abord de récupérer depuis le serveur
        member = ctx.guild.get_member(user_id)
        if member:
            return member, True
        
        # Essayer de fetch le membre (pour ceux sur le serveur mais non cachés)
        try:
            member = await ctx.guild.fetch_member(user_id)
            return member, True
        except discord.NotFound:
            # Membre n'est pas sur le serveur, essayer de récupérer l'utilisateur
            try:
                user = await bot.fetch_user(user_id)
                # Créer un objet MinimalMember pour les utilisateurs hors serveur
                class MinimalMember:
                    def __init__(self, user):
                        self.id = user.id
                        self.name = user.name
                        self.mention = user.mention
                        self.display_name = user.name
                        self.avatar = user.avatar
                        self.bot = user.bot
                        self.roles = []  # Pas de rôles hors serveur
                
                return MinimalMember(user), False
            except discord.NotFound:
                return None, False
        except discord.HTTPException:
            return None, False
            
    except (ValueError, discord.NotFound, discord.HTTPException):
        return None, False

def create_white_embed(description: str) -> discord.Embed:
    embed = discord.Embed(description=description, color=0xFFFFFF)
    return embed

def create_green_embed(description: str) -> discord.Embed:
    embed = discord.Embed(description=description, color=0x00FF00)
    return embed

def create_red_embed(description: str) -> discord.Embed:
    embed = discord.Embed(description=description, color=0xFF0000)
    return embed

def create_black_embed(description: str) -> discord.Embed:
    embed = discord.Embed(description=description, color=0x000000)
    return embed

def create_black_embed_with_title(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=0x000000)
    return embed

def create_log_embed(title: str, fields: dict) -> discord.Embed:
    embed = discord.Embed(title=title, color=0x00FF00)
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    embed.set_thumbnail(url=LOG_THUMBNAIL)
    embed.set_footer(text=get_current_time_french())
    return embed

def get_current_time_french():
    # Heure française (UTC+1 ou UTC+2 selon l'heure d'été)
    tz = timezone(timedelta(hours=1))  # UTC+1 (pour l'heure d'hiver)
    now = datetime.now(tz)
    return now.strftime("%d/%m/%Y - %H:%M:%S")

# ============ LIMITES BLACKLIST MODIFIÉES ============
BL_LIMITS = {
    "Owner": 3,
    "Sys": 6,
    "Sys+": 8,
    "Créateur": 15,
    "Créateur++": 9999
}

BL_COOLDOWN = 7200  # 2 heures en secondes

def check_bl_limit(user_id: str, grade: str) -> tuple[bool, str]:
    # L'admin n'a pas de limites
    if int(user_id) == ADMIN_USER_ID:
        return True, ""
    
    # Vérifier si l'utilisateur est dans la whitelist
    if is_in_whitelist(str(user_id)):
        return True, ""
    
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
    # Ne pas incrémenter pour l'admin ou les whitelistés
    if int(user_id) == ADMIN_USER_ID or is_in_whitelist(str(user_id)):
        return
    
    data = load_json(BL_LIMITS_FILE)
    user_id = str(user_id)
    
    if user_id not in data:
        data[user_id] = {"count": 1, "last_reset": datetime.now().isoformat()}
    else:
        data[user_id]["count"] += 1
    
    save_json(BL_LIMITS_FILE, data)

# ============ LOGS ============
async def send_log(ctx, log_type: str, fields: dict):
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

# ============ WHITELIST MODIFIÉE ============
def is_in_whitelist(user_id: str) -> bool:
    # L'admin est toujours considéré comme dans la whitelist
    if int(user_id) == ADMIN_USER_ID:
        return True
    
    data = load_json(WHITELIST_FILE)
    # Whitelist unique pour tous les grades
    return user_id in data.get("all", [])

def add_to_whitelist(user_id: str):
    data = load_json(WHITELIST_FILE)
    if "all" not in data:
        data["all"] = []
    if user_id not in data["all"]:
        data["all"].append(user_id)
    save_json(WHITELIST_FILE, data)

def remove_from_whitelist(user_id: str):
    data = load_json(WHITELIST_FILE)
    if "all" in data and user_id in data["all"]:
        data["all"].remove(user_id)
        save_json(WHITELIST_FILE, data)
        return True
    return False

def clear_whitelist():
    data = load_json(WHITELIST_FILE)
    if "all" in data:
        count = len(data["all"])
        data["all"] = []
        save_json(WHITELIST_FILE, data)
        return count
    return 0

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
    # Page 1 - Modération
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

    # Page 2 - Information
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

    # Page 3 - Modification des grades
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

    # Page 4 - Créateur++ uniquement
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
    """Affiche l'aide pour les commandes de logs"""
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

# ============ COMMANDE PERM ============
@bot.command()
@has_required_grade()
async def perm(ctx):
    """Affiche les permissions par grade"""
    description = "──────────────\n"
    
    # Ajouter l'admin spécial
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
    """Affiche la hiérarchie des grades"""
    lines = []
    
    # Ajouter l'admin spécial en premier
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
    """Vérifie tes rôles"""
    # Vérifier si c'est l'admin
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
    """Blacklist un utilisateur avec raison (même hors serveur)"""
    # Vérifier si c'est une réponse à un message
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
    
    # Récupérer l'utilisateur par ID ou mention
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    target_member, is_on_server = result
    
    # Vérifier si l'utilisateur est déjà blacklisté
    bl_data = load_json(BLACKLIST_FILE)
    if str(target_member.id) in bl_data:
        embed = create_red_embed(f"Cet utilisateur est déjà dans la blacklist.")
        return await ctx.send(embed=embed)
    
    # Vérification des grades
    executor_grade = get_user_grade(ctx.author)
    
    # L'admin peut tout blacklist sauf lui-même
    if ctx.author.id == ADMIN_USER_ID:
        if target_member.id == ADMIN_USER_ID:
            embed = create_red_embed("Tu ne peux pas te blacklist toi-même.")
            return await ctx.send(embed=embed)
        # L'admin peut blacklist n'importe qui
        pass
    else:
        if not executor_grade:
            embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
            return await ctx.send(embed=embed)
    
    # Si l'utilisateur est sur le serveur, vérifier son grade
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
        
        # Vérification hiérarchique (sauf pour l'admin)
        if ctx.author.id != ADMIN_USER_ID and GRADES[executor_grade] <= target_value:
            embed = create_red_embed("Eh Oh ? T'essaie de faire quoi ?")
            return await ctx.send(embed=embed)
    else:
        # Pour les utilisateurs hors serveur, on ne connaît pas leur grade
        target_grade = "Inconnu (hors serveur)"
        target_value = 0
    
    # Vérifier la limite BL (sauf pour l'admin et les whitelistés)
    if ctx.author.id != ADMIN_USER_ID and not is_in_whitelist(str(ctx.author.id)):
        can_bl, error_msg = check_bl_limit(str(ctx.author.id), executor_grade)
        if not can_bl:
            embed = create_red_embed(error_msg)
            return await ctx.send(embed=embed)
    
    # Ban automatique si l'utilisateur est sur le serveur
    ban_success = False
    if is_on_server:
        try:
            await target_member.ban(reason=f"Blacklist par {ctx.author}: {reason}")
            ban_success = True
        except discord.Forbidden:
            ban_success = False
        except discord.HTTPException:
            ban_success = False
    else:
        ban_success = False  # Pas de ban possible hors serveur
    
    # Sauvegarde blacklist
    bl_data[str(target_member.id)] = {
        "grade": target_grade,
        "reason": reason,
        "by": ctx.author.id,
        "banned": ban_success,
        "on_server": is_on_server,
        "timestamp": get_current_time_french()
    }
    save_json(BLACKLIST_FILE, bl_data)
    
    # Incrémenter le compteur BL (sauf pour l'admin et les whitelistés)
    if ctx.author.id != ADMIN_USER_ID and not is_in_whitelist(str(ctx.author.id)):
        increment_bl_count(str(ctx.author.id))
    
    # Envoi DM à la personne blacklistée si possible
    try:
        dm_message = (
            f"Vous avez été blacklisté de `Akusa` #🎐 pour `{reason}`\n\n"
            f"Rejoignez le serveur prison d'Akusa pour vous faire unbl\n"
            f"lien : https://discord.gg/Cr8K2N48fe"
        )
        await target_member.send(dm_message)
    except:
        pass
    
    # Réponse publique
    if is_on_server:
        embed = create_green_embed(f"{target_member.mention} a été blacklister par {ctx.author.mention}\nRaison : `{reason}`")
    else:
        embed = create_green_embed(f"L'utilisateur `{target_member.name}` (ID: {target_member.id}) a été blacklister par {ctx.author.mention}\nRaison : `{reason}`")
    
    await ctx.send(embed=embed)
    
    # Log
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
            "Utilisateur BL": f"{target_member.name} (ID: {target_member.id})",
            "Raison": reason,
            "Statut": "Hors serveur"
        })

@bot.command()
@has_required_grade()
async def unbl(ctx, identifier: str = None):
    """Unblacklist un utilisateur par ID ou mention, même hors serveur"""
    # Vérifier si c'est une réponse à un message
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
    
    # Récupérer l'utilisateur par ID ou mention
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    bl_data = load_json(BLACKLIST_FILE)
    uid = str(member.id)
    
    if uid not in bl_data:
        embed = create_red_embed("Cet utilisateur n'est pas dans la blacklist.")
        return await ctx.send(embed=embed)
    
    # Vérification des permissions
    if ctx.author.id != ADMIN_USER_ID:
        executor_grade = get_user_grade(ctx.author)
        if not executor_grade:
            embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
            return await ctx.send(embed=embed)
        
        stored_grade = bl_data[uid]["grade"]
        if stored_grade == "Créateur++" and executor_grade != "Créateur++":
            embed = create_red_embed(f"Vous n'avez pas les permissions nécessaires car cet utilisateur a été blacklister par un {stored_grade}.")
            return await ctx.send(embed=embed)
    
    # Unban automatique si l'utilisateur est banni et sur le serveur
    unban_success = False
    if is_on_server:
        try:
            # Essayer de trouver si l'utilisateur est banni
            try:
                ban_entry = await ctx.guild.fetch_ban(discord.Object(id=int(uid)))
                await ctx.guild.unban(ban_entry.user, reason=f"Unblacklist par {ctx.author}")
                unban_success = True
                unban_msg = f"{member.mention} a bien été **retiré** de la blacklist et débanni."
            except discord.NotFound:
                # L'utilisateur n'est pas banni
                unban_msg = f"{member.mention} a bien été **retiré** de la blacklist (n'était pas banni)."
        except discord.Forbidden:
            unban_msg = f"{member.mention} a bien été **retiré** de la blacklist (pas les permissions de unban)."
        except:
            unban_msg = f"{member.mention} a bien été **retiré** de la blacklist."
    else:
        # Utilisateur hors serveur, pas de unban possible
        unban_msg = f"L'utilisateur `{member.name}` (ID: {member.id}) a bien été **retiré** de la blacklist (hors serveur)."
    
    # Envoi DM à la personne unblacklistée si possible
    try:
        dm_message = (
            f"Vous avez été unbl de `Akusa` #🎐\n\n"
            f"Voici le lien du serveur : https://discord.gg/fH2ur9ffSa"
        )
        await member.send(dm_message)
    except:
        pass
    
    # Suppression blacklist
    del bl_data[uid]
    save_json(BLACKLIST_FILE, bl_data)
    
    embed = create_green_embed(unban_msg)
    await ctx.send(embed=embed)
    
    # Log
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
    """Retirer tous les utilisateurs de la blacklist"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    bl_data = load_json(BLACKLIST_FILE)
    count = len(bl_data)
    
    # Unban tous les utilisateurs blacklistés qui sont sur le serveur
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
    
    embed = create_green_embed(msg)
    await ctx.send(embed=embed)
    
    # Log
    await send_log(ctx, "unbl", {
        "Unblacklist par": ctx.author.mention,
        "Action": "Tout unblacklist",
        "Nombre": str(count)
    })

@bot.command()
@has_required_grade()
async def bllist(ctx):
    """Liste des utilisateurs blacklistés"""
    bl_data = load_json(BLACKLIST_FILE)
    
    if not bl_data:
        embed = create_white_embed("Aucun utilisateur blacklist")
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
            on_server = data.get("on_server", True)
            
            if not on_server:
                description_lines.append(f"{user_mention} — {grade} (hors serveur)")
            else:
                description_lines.append(f"{user_mention} — {grade}")
            
            description_lines.append(f"• Raison : {reason}")
            description_lines.append("")
        
        embed = create_white_embed("Liste des blacklist\n\n" + "\n".join(description_lines))
        embed.set_footer(text=f"Page {len(pages)+1}/{(len(all_items)+items_per_page-1)//items_per_page} • {get_current_time_french()}")
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
async def blinfo(ctx, identifier: str):
    """Informations sur une blacklist"""
    # Récupérer l'utilisateur par ID ou mention
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    bl_data = load_json(BLACKLIST_FILE)
    uid = str(member.id)
    
    if uid not in bl_data:
        embed = create_red_embed("Cet utilisateur n'est pas dans la blacklist.")
        return await ctx.send(embed=embed)
    
    data = bl_data[uid]
    
    # Vérifier si la blacklist a été faite par un grade "Créateur" ou supérieur
    # ou par l'admin, et masquer l'identité si c'est le cas
    bl_by_grade = None
    bl_by_id = data.get('by')
    
    # Essayer de récupérer le grade de la personne qui a fait la BL
    try:
        if bl_by_id:
            bl_by_member = await get_user_by_id_or_mention(ctx, str(bl_by_id))
            if bl_by_member:
                bl_by_member_obj, _ = bl_by_member
                if isinstance(bl_by_member_obj, discord.Member):
                    bl_by_grade = get_user_grade(bl_by_member_obj)
    except:
        pass
    
    # Si pas de grade, vérifier si c'est l'admin
    if not bl_by_grade and bl_by_id == ADMIN_USER_ID:
        bl_by_grade = "Créateur++"  # Admin = Créateur++ pour la hiérarchie
    
    # Masquer l'identité si le grade est "Créateur" ou supérieur
    hide_identity = False
    if bl_by_grade:
        if bl_by_grade in ["Créateur", "Créateur++"]:
            hide_identity = True
    
    # Préparer l'affichage
    if hide_identity:
        by_display = "**Masqué**"
        grade_display = "**Masqué**"
    else:
        by_display = f"<@{bl_by_id}>" if bl_by_id else "Inconnu"
        grade_display = data.get('grade', 'Inconnu')
        if grade_display == "None":
            grade_display = "Aucun grade"
    
    # Statut serveur
    on_server = data.get('on_server', True)
    status = "Hors serveur" if not on_server else "Sur serveur"
    
    embed = create_white_embed(
        f"BLACKLIST INFO\n\n"
        f"Blacklist : {member.mention}\n"
        f"Statut : {status}\n\n"
        f"Par : {by_display}\n"
        f"Grade : {grade_display}\n\n"
        f"Raison du BL :\n{data['reason']}\n\n"
        f"Date : {data['timestamp']}"
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

# ============ NOUVELLE COMMANDE GRADE ============
@bot.command()
@has_required_grade()
async def grade(ctx, identifier: str = None):
    """Voir le grade d'un utilisateur"""
    # Vérifier si c'est une réponse à un message
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_member = replied_message.author
            identifier = str(target_member.id)
        except:
            pass
    
    if not identifier:
        # Voir son propre grade
        target_member = ctx.author
        is_on_server = True
    else:
        # Récupérer l'utilisateur par ID ou mention
        result = await get_user_by_id_or_mention(ctx, identifier)
        
        if not result:
            embed = create_red_embed("Utilisateur introuvable.")
            return await ctx.send(embed=embed)
        
        target_member, is_on_server = result
    
    # Vérifier le grade (seulement si sur le serveur)
    if is_on_server and isinstance(target_member, discord.Member):
        grade = get_user_grade(target_member)
        
        if grade:
            embed = create_black_embed(f"{target_member.mention} a le grade **{grade}**")
        else:
            embed = create_black_embed(f"{target_member.mention} n'a aucun grade de la hiérarchie")
    else:
        embed = create_black_embed(f"{target_member.mention} n'est pas sur le serveur, impossible de vérifier son grade")
    
    await ctx.send(embed=embed)

# ============ NOUVELLE COMMANDE LIMITS ============
@bot.command()
@has_required_grade()
async def limits(ctx):
    """Affiche les limites de blacklist par grade par heure"""
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
    """Ajouter un utilisateur à la whitelist (même hors serveur)"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    # Vérifier si c'est une réponse à un message
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
    
    # Récupérer l'utilisateur par ID ou mention
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    if is_in_whitelist(str(member.id)):
        if is_on_server:
            embed = create_red_embed(f"{member.mention} est déjà dans la whitelist.")
        else:
            embed = create_red_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) est déjà dans la whitelist.")
        return await ctx.send(embed=embed)
    
    add_to_whitelist(str(member.id))
    
    if is_on_server:
        embed = create_green_embed(f"{member.mention} ajouté à la whitelist.")
    else:
        embed = create_green_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) ajouté à la whitelist.")
    
    await ctx.send(embed=embed)
    
    # Log
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
    """Retirer un utilisateur de la whitelist (même hors serveur)"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    # Vérifier si c'est une réponse à un message
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
    
    # Récupérer l'utilisateur par ID ou mention
    result = await get_user_by_id_or_mention(ctx, identifier)
    
    if not result:
        embed = create_red_embed("Utilisateur introuvable.")
        return await ctx.send(embed=embed)
    
    member, is_on_server = result
    
    removed = remove_from_whitelist(str(member.id))
    
    if removed:
        if is_on_server:
            embed = create_green_embed(f"{member.mention} retiré de la whitelist.")
        else:
            embed = create_green_embed(f"L'utilisateur `{member.name}` (ID: {member.id}) retiré de la whitelist.")
        
        # Log
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
    """Vider complètement la whitelist"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    count = clear_whitelist()
    
    if count == 0:
        embed = create_white_embed("La whitelist est déjà vide.")
    else:
        embed = create_green_embed(f"Whitelist vidée avec succès. {count} utilisateur(s) retiré(s).")
        
        # Log
        await send_log(ctx, "clearwl", {
            "Vidée par": ctx.author.mention,
            "Nombre retiré": str(count)
        })
    
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def wllist(ctx):
    """Voir les utilisateurs dans la whitelist"""
    data = load_json(WHITELIST_FILE)
    
    description_lines = ["Whitelist\n"]
    members = data.get("all", [])
    
    if members:
        for uid in members:
            description_lines.append(f"• <@{uid}>")
    else:
        description_lines.append("Aucun utilisateur dans la whitelist")
    
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
    """Configurer le salon de logs général"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "general", channel.id)
    embed = create_green_embed(f"Salon de logs configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsbl(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs BL"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "bl", channel.id)
    embed = create_green_embed(f"Salon de logs BL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsunbl(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs UNBL"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "unbl", channel.id)
    embed = create_green_embed(f"Salon de logs UNBL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsrank(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs RANK"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "rank", channel.id)
    embed = create_green_embed(f"Salon de logs RANK configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogswl(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs WL"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "wl", channel.id)
    embed = create_green_embed(f"Salon de logs WL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_specific_grade("Créateur++")
async def setlogsunwl(ctx, channel: discord.TextChannel):
    """Configurer le salon de logs UNWL"""
    # L'admin peut aussi utiliser cette commande
    if ctx.author.id != ADMIN_USER_ID and get_user_grade(ctx.author) != "Créateur++":
        embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
        return await ctx.send(embed=embed)
    
    set_log_channel(ctx.guild.id, "unwl", channel.id)
    embed = create_green_embed(f"Salon de logs UNWL configuré : {channel.mention}")
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def logs(ctx):
    """Voir la configuration des salons de logs"""
    data = load_json(LOGS_FILE)
    guild_id = str(ctx.guild.id)
    
    if guild_id not in data:
        embed = create_white_embed("Aucun salon de logs configuré.")
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
    
    embed = create_white_embed("\n".join(lines))
    await ctx.send(embed=embed)

# ============ COMMANDES ATTRIBUTION DE GRADES ============
@bot.command()
@has_required_grade()
async def rank(ctx, member: discord.Member = None, grade: str = None):
    """Donner un grade à un utilisateur (peut répondre au message)"""
    # Vérifier si c'est une réponse à un message
    if ctx.message.reference and ctx.message.reference.message_id and not member and not grade:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            member = replied_message.author
            # Extraire le grade depuis le message
            content = ctx.message.content
            parts = content.split()
            if len(parts) >= 2:
                grade = parts[1]
        except:
            pass
    elif ctx.message.reference and ctx.message.reference.message_id and member and not grade:
        # Si le membre est mentionné mais pas le grade
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
    
    # Vérification des permissions
    if ctx.author.id == ADMIN_USER_ID:
        # L'admin peut tout donner sans restrictions
        pass
    else:
        executor_grade = get_user_grade(ctx.author)
        
        if not executor_grade:
            embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
            return await ctx.send(embed=embed)
        
        # Créateur++ peut tout donner sans whitelist
        if executor_grade == "Créateur++":
            pass  # Pas de vérification de whitelist
        # Créateur peut donner owner/sys/sys+/crea mais doit être dans la whitelist
        elif executor_grade == "Créateur":
            if grade not in ["owner", "sys", "sys+", "crea"]:
                embed = create_red_embed("Vous n'avez pas les permissions nécessaires pour attribuer ce grade.")
                return await ctx.send(embed=embed)
            
            if not is_in_whitelist(str(ctx.author.id)):
                embed = create_red_embed("Vous n'êtes pas dans la whitelist.")
                return await ctx.send(embed=embed)
        # Autres grades ne peuvent pas donner de grades
        else:
            embed = create_black_embed("Malheureusement tu n'as pas les permissions nécessaires")
            return await ctx.send(embed=embed)
    
    # Vérification qu'on ne donne pas un grade égal ou supérieur au sien
    if ctx.author.id != ADMIN_USER_ID:
        executor_grade_value = GRADES[executor_grade]
        target_grade_value = GRADES[get_grade_name_from_key(grade)]
        
        if target_grade_value >= executor_grade_value:
            embed = create_black_embed("Tu ne peux pas donner un grade égal ou supérieur au tien")
            return await ctx.send(embed=embed)
    
    # Récupérer le rôle
    role_id = GRADE_TO_ROLE_ID.get(grade)
    if not role_id:
        embed = create_red_embed(f"Rôle {grade} introuvable.")
        return await ctx.send(embed=embed)
    
    role = ctx.guild.get_role(role_id)
    if not role:
        embed = create_red_embed(f"Rôle {grade} introuvable.")
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
        
        grade_display = get_grade_name_from_key(grade)
        embed = create_green_embed(f"{member.mention} a bien reçu le grade {grade_display}")
        await ctx.send(embed=embed)
        
        # Log
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

def get_grade_name_from_key(grade_key: str) -> str:
    """Convertit une clé de grade en nom affichable"""
    grade_map = {
        "owner": "Owner",
        "sys": "Sys",
        "sys+": "Sys+",
        "crea": "Créateur",
        "crea++": "Créateur++"
    }
    return grade_map.get(grade_key, grade_key)

# ============ COMMANDE CHANGELIMIT ============
@bot.command()
@has_specific_grade("Créateur++")
async def changelimit(ctx, grade: str, limit: int):
    """Changer la limite de BL par heure pour un grade"""
    # L'admin peut aussi utiliser cette commande
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
    
    # Convertir le grade du format commande vers format affichage
    grade_display = get_grade_name_from_key(grade)
    
    # Mettre à jour la limite
    BL_LIMITS[grade_display] = limit
    
    embed = create_green_embed(f"Limite de BL par heure pour **{grade_display}** définie à **{limit}**.")
    await ctx.send(embed=embed)

# ============ COMMANDE PING ============
@bot.command()
async def ping(ctx):
    """Vérifie la latence du bot"""
    latency = round(bot.latency * 1000)
    embed = create_white_embed(f"Pong! Latence : **{latency}ms**")
    await ctx.send(embed=embed)

# ============ LANCEMENT ============
if __name__ == "__main__":
    bot.run(TOKEN)