import os,sys,sqlite3,asyncio
from datetime import datetime,timedelta,timezone
import discord
from discord.ext import commands

TOKEN=os.getenv("TOKEN")or os.getenv("DISCORD_TOKEN")
if not TOKEN:print("ERREUR: Token non défini!");sys.exit(1)

PREFIX="&"
THUMBNAIL_URL="https://cdn.discordapp.com/attachments/1467151867191496808/1467232922938638479/IMG_1620.jpg?ex=697fa2a4&is=697e5124&hm=a712241a364f6b68dc031cac0860e5e9b9af3f2df3e69c8f3b14e1817852ccde&"
LOG_THUMBNAIL=THUMBNAIL_URL
ADMIN_USER_ID= [1399234120214909010,1425947830463365120]

def init_database():
    conn=sqlite3.connect('akusa_bot.db',check_same_thread=False)
    c=conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS blacklist(user_id INTEGER PRIMARY KEY,user_name TEXT,grade TEXT,reason TEXT,added_by INTEGER,added_by_name TEXT,banned INTEGER DEFAULT 0,on_server INTEGER DEFAULT 1,timestamp TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS whitelist(user_id INTEGER PRIMARY KEY,user_name TEXT,added_by INTEGER,added_by_name TEXT,timestamp TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS logs_config(guild_id INTEGER,log_type TEXT,channel_id INTEGER,PRIMARY KEY(guild_id,log_type))')
    c.execute('CREATE TABLE IF NOT EXISTS bl_limits(user_id INTEGER PRIMARY KEY,count INTEGER DEFAULT 0,last_reset TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS user_grades(user_id INTEGER,guild_id INTEGER,grade TEXT,granted_by INTEGER,granted_by_name TEXT,timestamp TEXT,PRIMARY KEY(user_id,guild_id))')
    c.execute('CREATE TABLE IF NOT EXISTS blocked_words(word TEXT PRIMARY KEY,added_by INTEGER,added_by_name TEXT,timestamp TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS protect(user_id INTEGER PRIMARY KEY,user_name TEXT,added_by INTEGER,added_by_name TEXT,timestamp TEXT)')
    conn.commit()
    return conn,c
db_conn,db_cursor=init_database()
print("✅ DB initialisée")

def add_to_blacklist(uid,uname,grade,reason,added_by,added_by_name,banned,on_server,ts):
    db_cursor.execute('INSERT OR REPLACE INTO blacklist VALUES(?,?,?,?,?,?,?,?,?)',(uid,uname,grade,reason,added_by,added_by_name,banned,on_server,ts))
    db_conn.commit()
def remove_from_blacklist(uid):
    db_cursor.execute('DELETE FROM blacklist WHERE user_id=?',(uid,));db_conn.commit()
def get_blacklist():
    db_cursor.execute('SELECT*FROM blacklist ORDER BY timestamp DESC');return db_cursor.fetchall()
def get_blacklist_user(uid):
    db_cursor.execute('SELECT*FROM blacklist WHERE user_id=?',(uid,));return db_cursor.fetchone()
def clear_blacklist():
    db_cursor.execute('DELETE FROM blacklist');db_conn.commit();return db_cursor.rowcount

def add_to_whitelist(uid,uname,added_by,added_by_name,ts):
    db_cursor.execute('INSERT OR REPLACE INTO whitelist VALUES(?,?,?,?,?)',(uid,uname,added_by,added_by_name,ts))
    db_conn.commit()
def remove_from_whitelist(uid):
    db_cursor.execute('DELETE FROM whitelist WHERE user_id=?',(uid,));db_conn.commit();return db_cursor.rowcount>0
def is_in_whitelist(uid):
    db_cursor.execute('SELECT 1 FROM whitelist WHERE user_id=?',(uid,));return db_cursor.fetchone()is not None
def get_whitelist():
    db_cursor.execute('SELECT*FROM whitelist ORDER BY timestamp DESC');return db_cursor.fetchall()
def clear_whitelist():
    db_cursor.execute('DELETE FROM whitelist');db_conn.commit();return db_cursor.rowcount

def set_log_channel(gid,ltype,cid):
    db_cursor.execute('INSERT OR REPLACE INTO logs_config VALUES(?,?,?)',(gid,ltype,cid));db_conn.commit()
def get_log_channel(gid,ltype):
    db_cursor.execute('SELECT channel_id FROM logs_config WHERE guild_id=? AND log_type=?',(gid,ltype))
    r=db_cursor.fetchone();return r[0]if r else None
def get_all_logs(gid):
    db_cursor.execute('SELECT log_type,channel_id FROM logs_config WHERE guild_id=?',(gid,));return db_cursor.fetchall()

def update_bl_limit(uid,count,last_reset):
    db_cursor.execute('INSERT OR REPLACE INTO bl_limits VALUES(?,?,?)',(uid,count,last_reset));db_conn.commit()
def get_bl_limit(uid):
    db_cursor.execute('SELECT count,last_reset FROM bl_limits WHERE user_id=?',(uid,));return db_cursor.fetchone()

def set_user_grade(uid,gid,grade,granted_by,granted_by_name,ts):
    db_cursor.execute('INSERT OR REPLACE INTO user_grades VALUES(?,?,?,?,?,?)',(uid,gid,grade,granted_by,granted_by_name,ts))
    db_conn.commit()
def get_user_grade(uid,gid):
    if uid==ADMIN_USER_ID:return"Créateur++"
    db_cursor.execute('SELECT grade FROM user_grades WHERE user_id=? AND guild_id=?',(uid,gid))
    r=db_cursor.fetchone();return r[0]if r else None
def remove_user_grade(uid,gid):
    db_cursor.execute('DELETE FROM user_grades WHERE user_id=? AND guild_id=?',(uid,gid));db_conn.commit();return db_cursor.rowcount>0
def get_all_users_with_grade(gid,grade):
    db_cursor.execute('SELECT user_id FROM user_grades WHERE guild_id=? AND grade=?',(gid,grade));return db_cursor.fetchall()

def add_blocked_word(word,added_by,added_by_name,ts):
    db_cursor.execute('INSERT OR REPLACE INTO blocked_words VALUES(?,?,?,?)',(word.lower(),added_by,added_by_name,ts))
    db_conn.commit()
def remove_blocked_word(word):
    db_cursor.execute('DELETE FROM blocked_words WHERE word=?',(word.lower(),));db_conn.commit();return db_cursor.rowcount>0
def get_blocked_words():
    db_cursor.execute('SELECT word FROM blocked_words ORDER BY word ASC');return[r[0]for r in db_cursor.fetchall()]
def clear_blocked_words():
    db_cursor.execute('DELETE FROM blocked_words');db_conn.commit();return db_cursor.rowcount
def is_word_blocked(word):
    db_cursor.execute('SELECT 1 FROM blocked_words WHERE word=?',(word.lower(),));return db_cursor.fetchone()is not None

def add_protect(uid,uname,added_by,added_by_name,ts):
    db_cursor.execute('INSERT OR REPLACE INTO protect VALUES(?,?,?,?,?)',(uid,uname,added_by,added_by_name,ts))
    db_conn.commit()
def remove_protect(uid):
    db_cursor.execute('DELETE FROM protect WHERE user_id=?',(uid,));db_conn.commit();return db_cursor.rowcount>0
def is_protected(uid):
    db_cursor.execute('SELECT 1 FROM protect WHERE user_id=?',(uid,));return db_cursor.fetchone()is not None
def get_protect_list():
    db_cursor.execute('SELECT*FROM protect ORDER BY timestamp DESC');return db_cursor.fetchall()
def clear_protect():
    db_cursor.execute('DELETE FROM protect');db_conn.commit();return db_cursor.rowcount

class PaginatorWithCounter(discord.ui.View):
    def __init__(self,embeds,total_items,timeout=3600):
        super().__init__(timeout=timeout);self.embeds=embeds;self.total_items=total_items;self.current_page=0;self.update_buttons()
    def update_buttons(self):
        self.children[0].disabled=self.current_page==0
        self.children[2].disabled=self.current_page==len(self.embeds)-1
        self.children[1].label=f"{self.current_page+1}/{len(self.embeds)}"
    @discord.ui.button(emoji="◀️",style=discord.ButtonStyle.blurple)
    async def previous(self,i,b):
        if self.current_page>0:self.current_page=0
        self.update_buttons();await i.response.edit_message(embed=self.embeds[self.current_page],view=self)
    @discord.ui.button(label="1/1",style=discord.ButtonStyle.gray,disabled=True)
    async def page_counter(self,i,b):pass
    @discord.ui.button(emoji="▶️",style=discord.ButtonStyle.blurple)
    async def next(self,i,b):
        self.current_page+=1;self.update_buttons();await i.response.edit_message(embed=self.embeds[self.current_page],view=self)

def has_required_grade(min_grade=None):
    async def p(ctx):
        if ctx.command.name in["help","ping","test"]:return True
        if ctx.author.id==ADMIN_USER_ID:return True
        g=get_user_grade(ctx.author.id,ctx.guild.id)
        if not min_grade:
            if g:return True
        else:
            if g and GRADES.get(g,0)>=GRADES.get(min_grade,0):return True
        await ctx.send(embed=discord.Embed(description="Tu na pas la permission d'utiliser cette commande",color=0xFFFFFF));return False
    return commands.check(p)

intents=discord.Intents.all()
bot=commands.Bot(command_prefix=PREFIX,intents=intents,help_command=None)

GRADES={"Créateur++":5,"Créateur":4,"Sys+":3,"Sys":2,"Owner":1}
BL_LIMITS={"Owner":3,"Sys":6,"Sys+":8,"Créateur":15,"Créateur++":9999}
BL_COOLDOWN=7200

async def get_user_by_id_or_mention(ctx,identifier):
    if not identifier:return None,False
    try:
        if identifier.startswith('<@')and identifier.endswith('>'):
            uid=identifier[2:-1]
            if uid.startswith('!'):uid=uid[1:]
            uid=int(uid)
        else:uid=int(identifier)
        m=ctx.guild.get_member(uid)
        if m:return m,True
        try:m=await ctx.guild.fetch_member(uid);return m,True
        except discord.NotFound:
            try:
                u=await bot.fetch_user(uid)
                class M:
                    def __init__(s,u):s.id=u.id;s.name=u.name;s.mention=u.mention;s.display_name=u.name;s.avatar=u.avatar;s.bot=u.bot
                return M(u),False
            except:return None,False
    except:return None,False

def create_white_embed(desc):return discord.Embed(description=desc,color=0xFFFFFF)
def create_log_embed(title,fields):
    e=discord.Embed(title=title,color=0xFFFFFF)
    for n,v in fields.items():e.add_field(name=n,value=v,inline=False)
    e.set_thumbnail(url=LOG_THUMBNAIL);e.set_footer(text=get_current_time_french());return e
def get_current_time_french():
    tz=timezone(timedelta(hours=1));return datetime.now(tz).strftime("%d/%m/%Y - %H:%M:%S")
def time_ago(ts):
    try:
        tz=timezone(timedelta(hours=1))
        bl=datetime.strptime(ts,"%d/%m/%Y - %H:%M:%S").replace(tzinfo=tz)
        d=datetime.now(tz)-bl
        if d.days>0:return"Il y a 1 jour"if d.days==1 else f"Il y a {d.days} jours"
        if d.seconds>=3600:h=d.seconds//3600;return"Il y a 1 heure"if h==1 else f"Il y a {h} heures"
        if d.seconds>=60:m=d.seconds//60;return"Il y a 1 minute"if m==1 else f"Il y a {m} minutes"
        return"À l'instant"
    except:return"Date inconnue"

def check_bl_limit(uid,grade):
    if int(uid)==ADMIN_USER_ID or is_in_whitelist(str(uid)):return True,""
    r=get_bl_limit(str(uid))
    if not r:update_bl_limit(str(uid),0,datetime.now().isoformat());return True,""
    c,last=r;last=datetime.fromisoformat(last)
    if datetime.now()-last>timedelta(seconds=BL_COOLDOWN):update_bl_limit(str(uid),0,datetime.now().isoformat());return True,""
    limit=BL_LIMITS.get(grade,3)
    if c>=limit:
        t=last+timedelta(seconds=BL_COOLDOWN)-datetime.now()
        m,s=int(t.total_seconds()//60),int(t.total_seconds()%60)
        return False,f"Tu as atteint le limite de bl, attends `{m}min {s}s` avant de pouvoir bl"
    return True,""
def increment_bl_count(uid):
    if int(uid)==ADMIN_USER_ID or is_in_whitelist(str(uid)):return
    r=get_bl_limit(str(uid))
    if not r:update_bl_limit(str(uid),1,datetime.now().isoformat())
    else:c,last=r;update_bl_limit(str(uid),c+1,last)

async def send_log(ctx,ltype,fields):
    cid=get_log_channel(ctx.guild.id,ltype)or get_log_channel(ctx.guild.id,"general")
    if not cid:return
    ch=bot.get_channel(cid)
    if not ch:
        try:ch=await bot.fetch_channel(cid)
        except:return
    title={"bl":"BL","unbl":"UNBL","rank":"ATTRIBUTION DE GRADE","unrank":"RETRAIT DE GRADE","wl":"WL","unwl":"UNWL","clearwl":"CLEARWL","protect":"PROTECT"}.get(ltype,ltype.upper())
    try:await ch.send(embed=create_log_embed(title,fields))
    except:pass

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user}")
    if len(get_blacklist())==0 and len(get_whitelist())==0:
        print("⚠️ DB vide au démarrage")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

@bot.before_invoke
async def cooldown_global(ctx):
    grade=get_user_grade(ctx.author.id,ctx.guild.id)
    if grade!="Créateur++" and ctx.author.id!=ADMIN_USER_ID:
        await asyncio.sleep(5)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=create_white_embed(f"⏳ Trop rapide ! Attends 5 secondes entre chaque commande."))
    else:raise error

@bot.command()
@has_required_grade()
async def help(ctx):
    e1=discord.Embed(color=0xFFFFFF,description="Page 1/4 - Modération\n")
    e1.add_field(name="Modération",value="`&bl @user/id raison` - Blacklist\n`&unbl @user/id` - Unblacklist\n`&bllist` - Liste des blacklist\n`&blinfo @user/id` - Infos blacklist\n`&myrole` - Vérifier son grade\n`&ping` - Latence du bot",inline=False)
    e1.set_footer(text=f"Page 1/4 • {get_current_time_french()}");e1.description+="\n\n-# Effectue `&perm` pour voir ton grade et tes permissions"
    e2=discord.Embed(color=0xFFFFFF,description="Page 2/4 - Information\n")
    e2.add_field(name="Informations",value="`&grades` - Hiérarchie des grades\n`&perm` - Permissions par grade\n`&wllist` - Liste des whitelists\n`&logs` - Configuration des logs\n`&limits` - Limites BL par grade\n`&changelimit grade nombre` - Modifier limite BL (Créateur++)",inline=False)
    e2.set_footer(text=f"Page 2/4 • {get_current_time_french()}")
    e3=discord.Embed(color=0xFFFFFF,description="Page 3/4 - Gestion des grades\n")
    e3.add_field(name="Gestion des grades",value="`&owner @user/id` - Donner grade Owner\n`&sys @user/id` - Donner grade Sys\n`&sys+ @user/id` - Donner grade Sys+\n`&crea @user/id` - Donner grade Créateur\n`&crea++ @user/id` - Donner grade Créateur++\n`&ungrade @user/id` - Retirer un grade\n`&grade @user/id` - Voir le grade d'un utilisateur\n\n_(sans argument: liste des utilisateurs ayant le grade)_",inline=False)
    e3.set_footer(text=f"Page 3/4 • {get_current_time_french()}")
    e4=discord.Embed(color=0xFFFFFF,description="Page 4/4 - Créateur++ uniquement\n")
    e4.add_field(name="Commandes réservées",value="`&wl @user/id` - Ajouter à la whitelist\n`&unwl @user/id` - Retirer de la whitelist\n`&clearwl` - Vider la whitelist\n`&unblall` - Vider la blacklist\n`&unbanall` - Vider la liste des bannis\n`&protect @user/id` - Protéger un utilisateur\n`&protectlist` - Liste des protégés\n`&savedb` - Sauvegarder la DB sur ton tel\n`&setdb` - Restaurer la DB depuis un fichier\n`&setlogs #salon` - Logs généraux\n`&setlogsbl #salon` - Logs BL\n`&setlogsunbl #salon` - Logs UNBL\n`&setlogsrank #salon` - Logs RANK\n`&setlogsunrank #salon` - Logs UNRANK\n`&setlogswl #salon` - Logs WL\n`&setlogsunwl #salon` - Logs UNWL\n`&help_logs` - Aide configuration logs",inline=False)
    e4.set_footer(text=f"Page 4/4 • {get_current_time_french()}")
    v=PaginatorWithCounter([e1,e2,e3,e4],4)
    await ctx.send(embed=e1,view=v)

@bot.command()
@has_required_grade()
async def help_logs(ctx):
    await ctx.send(embed=create_white_embed("Logs\n\nPour définir un salon logs vous devez mettre obligatoirement le type et le salon\nexemple : &setlogsbl #salon\n\n&setlogs (les différents logs disponibles) #salon\n&setlogsbl #salon\n&setlogsunbl #salon\n&setlogsrank #salon\n&setlogsunrank #salon\n&setlogswl #salon\n&setlogsunwl #salon\n\n&logs"))

@bot.command()
@has_required_grade()
async def perm(ctx):
    d="──────────────\nCréateur++\n──────────────\nToutes les commandes\n\n──────────────\nCréateur\n──────────────\nBlacklist/Unblacklist\nBllist/Blinfo\nGrades (owner, sys, sys+, crea) avec WL\nWllist\nMyrole/Grades\n\n──────────────\nSys+\n──────────────\nBlacklist/Unblacklist (raison non obligatoire)\nBllist/Blinfo\nMyrole/Grades\n\n──────────────\nSys\n──────────────\nBlacklist/Unblacklist\nBllist/Blinfo\nMyrole/Grades\n\n──────────────\nOwner\n──────────────\nBlacklist/Unblacklist\nBllist/Blinfo\nMyrole/Grades"
    await ctx.send(embed=create_white_embed(d))

@bot.command()
@has_required_grade()
async def grades(ctx):
    l=[]
    for g,v in sorted(GRADES.items(),key=lambda x:x[1],reverse=True):l.append("──────────────");l.append(f"{g} • Permission {v}")
    l.append("──────────────")
    await ctx.send(embed=create_white_embed("HIÉRARCHIE DES GRADES\n\n"+"\n".join(l)))

@bot.command()
@has_required_grade()
async def myrole(ctx):
    g=get_user_grade(ctx.author.id,ctx.guild.id)
    await ctx.send(embed=create_white_embed(f"T'es gradé : {g}\n\nFais `&perm` pour voir les commandes aux quels tu as accès"if g else"Tu n'as aucun grade de la hiérarchie."))

async def handle_grade_command(ctx,mid,gname,gdisplay):
    if not mid:
        users=get_all_users_with_grade(ctx.guild.id,gname)
        if not users:return await ctx.send(embed=create_white_embed(f"**Liste des {gdisplay}**\n\nAucun utilisateur n'a le grade {gdisplay}."))
        ml=[]
        for uid in users:
            uid=uid[0]
            try:u=await bot.fetch_user(uid);ml.append(f"{u.mention}\n`{u.id}`")
            except:ml.append(f"<@{uid}>\n`{uid}`")
        return await ctx.send(embed=create_white_embed(f"**Liste des {gdisplay}** ({len(users)}):\n\n"+"\n\n".join(ml)))
    r=await get_user_by_id_or_mention(ctx,mid)
    if not r or not r[0]:
        return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable. Mentionne quelqu'un ou mets son ID."))
    m,ison=r
    eg=get_user_grade(ctx.author.id,ctx.guild.id)
    if ctx.author.id!=ADMIN_USER_ID:
        if not eg:return await ctx.send(embed=create_white_embed("Tu na pas la permission d'utiliser cette commande"))
        if gname=="Créateur++"and eg!="Créateur++":return await ctx.send(embed=create_white_embed("Tu na pas la permission d'utiliser cette commande"))
        if gname=="Créateur"and eg not in["Créateur++","Créateur"]:return await ctx.send(embed=create_white_embed("Tu na pas la permission d'utiliser cette commande"))
        if gname in["Sys+","Sys","Owner"]and eg=="Créateur"and not is_in_whitelist(str(ctx.author.id)):return await ctx.send(embed=create_white_embed("Tu na pas la permission d'utiliser cette commande"))
        if GRADES[gname]>=GRADES[eg]:return await ctx.send(embed=create_white_embed("Tu ne peux pas donner un grade égal ou supérieur au tien"))
    cg=get_user_grade(m.id,ctx.guild.id)
    try:
        if cg:remove_user_grade(m.id,ctx.guild.id)
        set_user_grade(m.id,ctx.guild.id,gname,ctx.author.id,ctx.author.name,get_current_time_french())
        await ctx.send(embed=create_white_embed(f"{m.mention} a bien reçu le grade (**{gdisplay}**)"))
        await send_log(ctx,"rank",{"Donné par":f"{ctx.author.mention} ({'Créateur++'if ctx.author.id==ADMIN_USER_ID else eg})","À":m.mention,"Grade donné":gdisplay})
    except Exception as e:
        print(f"Erreur grade: {e}")
        await ctx.send(embed=create_white_embed("Erreur technique. Impossible d'ajouter le grade."))

@bot.command()
@has_required_grade("Créateur")
async def owner(ctx,member=None):await handle_grade_command(ctx,member,"Owner","Owner")
@bot.command()
@has_required_grade("Créateur")
async def sys(ctx,member=None):await handle_grade_command(ctx,member,"Sys","Sys")
@bot.command()
@has_required_grade("Créateur")
async def sysplus(ctx,member=None):await handle_grade_command(ctx,member,"Sys+","Sys+")
@bot.command(name="sys+")
@has_required_grade("Créateur")
async def sys_plus(ctx,member=None):await handle_grade_command(ctx,member,"Sys+","Sys+")
@bot.command()
@has_required_grade("Créateur++")
async def crea(ctx,member=None):await handle_grade_command(ctx,member,"Créateur","Créateur")
@bot.command()
@has_required_grade("Créateur++")
async def creapp(ctx,member=None):await handle_grade_command(ctx,member,"Créateur++","Créateur++")
@bot.command(name="crea++")
@has_required_grade("Créateur++")
async def crea_pp(ctx,member=None):await handle_grade_command(ctx,member,"Créateur++","Créateur++")

@bot.command()
@has_required_grade()
async def ungrade(ctx,member=None):
    if not member:return await ctx.send(embed=create_white_embed("Usage : `&ungrade @user/id`"))
    r=await get_user_by_id_or_mention(ctx,member)
    if not r or not r[0]:return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable."))
    m,ison=r;cg=get_user_grade(m.id,ctx.guild.id)
    if not cg:return await ctx.send(embed=create_white_embed(f"{m.mention} n'a aucun grade."))
    eg=get_user_grade(ctx.author.id,ctx.guild.id)
    if ctx.author.id!=ADMIN_USER_ID:
        if not eg:return await ctx.send(embed=create_white_embed("Tu na pas la permission d'utiliser cette commande"))
        if cg=="Créateur++":return await ctx.send(embed=create_white_embed("Tu ne peux pas retirer le grade d'un Créateur++"))
        if GRADES[cg]>=GRADES[eg]:return await ctx.send(embed=create_white_embed("Tu ne peux pas retirer un grade égal ou supérieur au tien"))
    remove_user_grade(m.id,ctx.guild.id)
    await ctx.send(embed=create_white_embed(f"{m.mention} n'est plus (**{cg}**)"))
    await send_log(ctx,"unrank",{"Retiré par":f"{ctx.author.mention} ({'Créateur++'if ctx.author.id==ADMIN_USER_ID else eg})","De":m.mention,"Grade retiré":cg})

@bot.command()
@has_required_grade()
async def bl(ctx,identifier=None,*,reason=None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:identifier=str((await ctx.channel.fetch_message(ctx.message.reference.message_id)).author.id)
        except:pass
    if not identifier:return await ctx.send(embed=create_white_embed("**Usage Incorrecte**\nUsage : `&bl id/@ raison`"))
    r=await get_user_by_id_or_mention(ctx,identifier)
    if not r or not r[0]:return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable."))
    tm,ison=r
    if tm.id==ctx.author.id:return await ctx.send(embed=create_white_embed("Wsh ? T'es con ou quoi? Tu veux te suicider?"))
    
    if is_protected(tm.id):
        db_cursor.execute('SELECT added_by FROM protect WHERE user_id=?',(tm.id,));p=db_cursor.fetchone()
        pid=p[0]if p else None;eg=get_user_grade(ctx.author.id,ctx.guild.id)
        if eg=="Créateur++":
            u=await bot.fetch_user(pid)if pid else None
            m=f"Tu dois d'abord enlever la protection de {tm.mention}"+(f" mise par {u.mention}"if u else "")+"\n-# &protect id/@user pour enlever la protection"
            return await ctx.send(embed=create_white_embed(m))
        else:
            u=await bot.fetch_user(pid)if pid else None
            m=f"{tm.mention} ne peux pas etre blacklister car il est protect"+(f" par {u.mention}"if u else "")
            return await ctx.send(embed=create_white_embed(m))
    
    if get_blacklist_user(tm.id):return await ctx.send(embed=create_white_embed("Cet utilisateur est déjà dans la blacklist."))
    eg=get_user_grade(ctx.author.id,ctx.guild.id)
    if ctx.author.id!=ADMIN_USER_ID and not eg:return await ctx.send(embed=create_white_embed("Tu na pas la permission d'utiliser cette commande"))
    if ison and isinstance(tm,discord.Member)and tm.top_role>=ctx.author.top_role and ctx.author.id!=ADMIN_USER_ID:
        return await ctx.send(embed=create_white_embed(f"Tu ne peux pas blacklist {tm.mention} car il est égal ou supérieur a toi"))
    if reason and ctx.author.id!=ADMIN_USER_ID:
        eg2=get_user_grade(ctx.author.id,ctx.guild.id)
        if eg2 not in["Créateur","Créateur++"]:
            for w in get_blocked_words():
                if w in reason.lower():return await ctx.send(embed=create_white_embed("Merci de mettre une raison valable"))
    if not reason and eg in["Owner","Sys"]and not is_in_whitelist(str(ctx.author.id)):
        return await ctx.send(embed=create_white_embed("**Usage Incorrecte**\nUsage : `&bl id/@ raison`\n\nRaison obligatoire pour blacklister un utilisateur."))
    reason=reason or"Aucune raison fournie"
    td="Inconnu (hors serveur)"
    if ison and isinstance(tm,discord.Member):
        tg=get_user_grade(tm.id,ctx.guild.id)
        if tg=="Créateur++":return await ctx.send(embed=create_white_embed("Impossible de blacklist un Créateur++."))
        if ctx.author.id!=ADMIN_USER_ID and tg and GRADES[eg]<=GRADES[tg]:
            return await ctx.send(embed=create_white_embed(f"Tu ne peux pas blacklist {tm.mention} car il est égal ou supérieur a toi"))
        td=tg or"Aucun grade"
    if ctx.author.id!=ADMIN_USER_ID and not is_in_whitelist(str(ctx.author.id)):
        c,msg=check_bl_limit(str(ctx.author.id),eg)
        if not c:return await ctx.send(embed=create_white_embed(msg))
    ban=False
    if ison:
        try:await tm.ban(reason=f"Blacklist par {ctx.author}: {reason}");ban=True
        except:ban=False
    add_to_blacklist(tm.id,tm.name if hasattr(tm,'name')else str(tm.id),td,reason,ctx.author.id,ctx.author.name,1 if ban else 0,1 if ison else 0,get_current_time_french())
    if ctx.author.id!=ADMIN_USER_ID and not is_in_whitelist(str(ctx.author.id)):increment_bl_count(str(ctx.author.id))
    try:await tm.send(f"Vous avez été blacklisté de `Akusa` #🎐 pour `{reason}`\n\nRejoignez le serveur prison d'Akusa pour vous faire unbl\nlien : https://discord.gg/Cr8K2N48fe")
    except:pass
    await ctx.send(embed=create_white_embed(f"{tm.mention} à bien etait blacklister\n`{reason}`"))
    ed="Créateur++"if ctx.author.id==ADMIN_USER_ID else eg
    await send_log(ctx,"bl",{"Blacklist par":f"{ctx.author.mention} ({ed})","Utilisateur BL":tm.mention if ison else f"{tm.name} (ID: {tm.id})","Raison":reason})

@bot.command()
@has_required_grade()
async def unbl(ctx,identifier=None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:identifier=str((await ctx.channel.fetch_message(ctx.message.reference.message_id)).author.id)
        except:pass
    if not identifier:return await ctx.send(embed=create_white_embed("MAUVAISE UTILISATION\nUsage : `&unbl id/@`"))
    r=await get_user_by_id_or_mention(ctx,identifier)
    if not r or not r[0]:return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable."))
    m,ison=r;ex=get_blacklist_user(m.id)
    if not ex:return await ctx.send(embed=create_white_embed("Cet utilisateur n'est pas dans la blacklist."))
    uid,uname,grade,reason,added_by,added_by_name,banned,on_server,ts=ex
    eg=get_user_grade(ctx.author.id,ctx.guild.id)
    if ctx.author.id!=ADMIN_USER_ID and not eg:return await ctx.send(embed=create_white_embed("Tu na pas la permission d'utiliser cette commande"))
    if added_by!=ctx.author.id and ctx.author.id!=ADMIN_USER_ID:
        try:
            bg=get_user_grade(added_by,ctx.guild.id)
            if bg and GRADES[bg]>GRADES[eg]:return await ctx.send(embed=create_white_embed(f"Tu ne peux pas unbl cette utilisateur car il a etait bl par un **({bg})**"))
        except:pass
    if added_by==ADMIN_USER_ID and ctx.author.id!=ADMIN_USER_ID:
        try:return await ctx.send(embed=create_white_embed(f"Cette utilisateur a etait Bl par <@{added_by}>"))
        except:return await ctx.send(embed=create_white_embed(f"Cette utilisateur a etait Bl par @akusa"))
    if ison:
        try:
            try:await ctx.guild.unban((await ctx.guild.fetch_ban(discord.Object(id=m.id))).user,reason=f"Unblacklist par {ctx.author}")
            except:pass
        except:pass
    try:await m.send(f"Vous avez été unbl de `Akusa` #🎐\n\nVoici le lien du serveur : https://discord.gg/fH2ur9ffSa")
    except:pass
    remove_from_blacklist(m.id)
    await ctx.send(embed=create_white_embed(f"{m.mention} à bien etait unbl"))
    await send_log(ctx,"unbl",{"Unblacklist par":ctx.author.mention,"Utilisateur unBL":m.mention if ison else f"{m.name} (ID: {m.id})","Statut":"Sur serveur"if ison else"Hors serveur"})

@bot.command()
@has_required_grade("Créateur++")
async def unblall(ctx):
    c=clear_blacklist()
    await ctx.send(embed=create_white_embed(f"{c} utilisateur(s) ont été retiré(s) de la blacklist"))
    await send_log(ctx,"unbl",{"Unblacklist par":ctx.author.mention,"Action":"Vider la blacklist","Nombre":str(c)})

@bot.command()
@has_required_grade("Créateur++")
async def unbanall(ctx):
    if ctx.author.id!=ADMIN_USER_ID and get_user_grade(ctx.author.id,ctx.guild.id)!="Créateur++":
        return await ctx.send(embed=create_white_embed("Tu na pas les permissions d'exécuter cette commande"))
    c=0
    try:
        async for b in ctx.guild.bans():
            try:await ctx.guild.unban(b.user,reason=f"Unbanall par {ctx.author}");c+=1
            except:pass
    except:pass
    await ctx.send(embed=create_white_embed(f"{c} utilisateur{' ont bien été'if c>1 else' a bien été'} unban avec succès"if c!=0 else"0 utilisateur a été unban avec succès"))
    await send_log(ctx,"unbl",{"Action":"Vider la liste des bannis","Par":ctx.author.mention,"Nombre":str(c)})

@bot.command()
@has_required_grade()
async def bllist(ctx):
    data=get_blacklist()
    if not data:return await ctx.send(embed=create_white_embed("Aucun utilisateur blacklist"))
    p=[]
    for i in range(0,len(data),10):
        l=["**Liste des utilisateurs blacklister**\n"]
        for it in data[i:i+10]:
            uid,un,g,r,ab,abn,b,os,ts=it
            l.append(f"<@{uid}>\n`{r}`");l.append("─"*30)
        e=create_white_embed("\n".join(l));e.set_footer(text=f"blacklist : {len(data)}");p.append(e)
    if len(p)==1:await ctx.send(embed=p[0])
    else:await ctx.send(embed=p[0],view=PaginatorWithCounter(p,len(data)))

@bot.command()
@has_required_grade()
async def blinfo(ctx,identifier):
    r=await get_user_by_id_or_mention(ctx,identifier)
    if not r or not r[0]:return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable."))
    m,ison=r;ex=get_blacklist_user(m.id)
    if not ex:return await ctx.send(embed=create_white_embed("Cet utilisateur n'est pas dans la blacklist."))
    uid,un,g,r,ab,abn,b,os,ts=ex
    l=[f"Blacklist : {m.mention}",f"`{uid}`",""]
    if ab:l.append(f"Blacklister par : <@{ab}>");l.append(f"`{ab}`")
    else:l.append("Blacklister par : Inconnu")
    l.append("");l.append(f"raison: `{r}`");l.append("");l.append(f"Il y'a {time_ago(ts).replace('Il y a ','')}")
    e=create_white_embed("\n".join(l))
    if hasattr(m,'avatar')and m.avatar:e.set_thumbnail(url=m.avatar.url)
    await ctx.send(embed=e)

@bot.command()
@has_required_grade()
async def grade(ctx,identifier=None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:identifier=str((await ctx.channel.fetch_message(ctx.message.reference.message_id)).author.id)
        except:pass
    if not identifier:tm,ison=ctx.author,True
    else:
        r=await get_user_by_id_or_mention(ctx,identifier)
        if not r or not r[0]:return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable."))
        tm,ison=r
    if ison and isinstance(tm,discord.Member):
        g=get_user_grade(tm.id,ctx.guild.id)
        await ctx.send(embed=create_white_embed(f"{tm.mention} a le grade **{g}**"if g else f"{tm.mention} n'a aucun grade de la hiérarchie"))
    else:await ctx.send(embed=create_white_embed(f"{tm.mention} n'est pas sur le serveur, impossible de vérifier son grade"))

@bot.command()
@has_required_grade()
async def limits(ctx):
    l=[]
    for g,lim in sorted(BL_LIMITS.items(),key=lambda x:GRADES.get(x[0],0),reverse=True):
        l.append(f"**{g}** : {lim if lim!=9999 else 'Illimité'} BL/2h")
    l.append("\n> La limite de bl par heure ce reset toute les **2 heures**")
    await ctx.send(embed=create_white_embed("\n".join(l)))

@bot.command()
@has_required_grade("Créateur++")
async def wl(ctx,identifier=None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:identifier=str((await ctx.channel.fetch_message(ctx.message.reference.message_id)).author.id)
        except:pass
    if not identifier:return await ctx.send(embed=create_white_embed("MAUVAISE UTILISATION\nUsage : `&wl id/@`"))
    r=await get_user_by_id_or_mention(ctx,identifier)
    if not r or not r[0]:return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable."))
    m,ison=r
    if is_in_whitelist(m.id):
        await ctx.send(embed=create_white_embed(f"{m.mention} est déjà dans la whitelist."if ison else f"L'utilisateur `{m.name}` (ID: {m.id}) est déjà dans la whitelist."))
        return
    add_to_whitelist(m.id,m.name if hasattr(m,'name')else str(m.id),ctx.author.id,ctx.author.name,get_current_time_french())
    await ctx.send(embed=create_white_embed(f"{m.mention} ajouté à la whitelist."if ison else f"L'utilisateur `{m.name}` (ID: {m.id}) ajouté à la whitelist."))
    await send_log(ctx,"wl",{"Ajouté par":ctx.author.mention,"À":m.mention if ison else f"{m.name} (ID: {m.id})"})

@bot.command()
@has_required_grade("Créateur++")
async def unwl(ctx,identifier=None):
    if ctx.message.reference and ctx.message.reference.message_id and not identifier:
        try:identifier=str((await ctx.channel.fetch_message(ctx.message.reference.message_id)).author.id)
        except:pass
    if not identifier:return await ctx.send(embed=create_white_embed("MAUVAISE UTILISATION\nUsage : `&unwl id/@`"))
    r=await get_user_by_id_or_mention(ctx,identifier)
    if not r or not r[0]:return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable."))
    m,ison=r
    if remove_from_whitelist(m.id):
        await ctx.send(embed=create_white_embed(f"{m.mention} retiré de la whitelist."if ison else f"L'utilisateur `{m.name}` (ID: {m.id}) retiré de la whitelist."))
        await send_log(ctx,"unwl",{"Retiré par":ctx.author.mention,"De":m.mention if ison else f"{m.name} (ID: {m.id})"})
    else:await ctx.send(embed=create_white_embed(f"{m.mention} n'est pas dans la whitelist."if ison else f"L'utilisateur `{m.name}` (ID: {m.id}) n'est pas dans la whitelist."))

@bot.command()
@has_required_grade("Créateur++")
async def clearwl(ctx):
    c=clear_whitelist()
    await ctx.send(embed=create_white_embed("La whitelist est déjà vide."if c==0 else f"Whitelist vidée avec succès. {c} utilisateur retiré."))
    if c>0:await send_log(ctx,"clearwl",{"Vidée par":ctx.author.mention,"Nombre retiré":str(c)})

@bot.command()
@has_required_grade()
async def wllist(ctx):
    data=get_whitelist()
    l=["Whitelist\n"]
    if data:
        for it in data:l.append(f"• <@{it[0]}>")
    else:l.append("Aucun utilisateur dans la whitelist")
    await ctx.send(embed=create_white_embed("\n".join(l)))

@bot.command()
@has_required_grade("Créateur++")
async def setlogs(ctx,channel:discord.TextChannel):
    set_log_channel(ctx.guild.id,"general",channel.id)
    await ctx.send(embed=create_white_embed(f"Salon de logs configuré : {channel.mention}"))
@bot.command()
@has_required_grade("Créateur++")
async def setlogsbl(ctx,channel:discord.TextChannel):
    set_log_channel(ctx.guild.id,"bl",channel.id)
    await ctx.send(embed=create_white_embed(f"Salon de logs BL configuré : {channel.mention}"))
@bot.command()
@has_required_grade("Créateur++")
async def setlogsunbl(ctx,channel:discord.TextChannel):
    set_log_channel(ctx.guild.id,"unbl",channel.id)
    await ctx.send(embed=create_white_embed(f"Salon de logs UNBL configuré : {channel.mention}"))
@bot.command()
@has_required_grade("Créateur++")
async def setlogsrank(ctx,channel:discord.TextChannel):
    set_log_channel(ctx.guild.id,"rank",channel.id)
    await ctx.send(embed=create_white_embed(f"Salon de logs RANK configuré : {channel.mention}"))
@bot.command()
@has_required_grade("Créateur++")
async def setlogsunrank(ctx,channel:discord.TextChannel):
    set_log_channel(ctx.guild.id,"unrank",channel.id)
    await ctx.send(embed=create_white_embed(f"Salon de logs UNRANK configuré : {channel.mention}"))
@bot.command()
@has_required_grade("Créateur++")
async def setlogswl(ctx,channel:discord.TextChannel):
    set_log_channel(ctx.guild.id,"wl",channel.id)
    await ctx.send(embed=create_white_embed(f"Salon de logs WL configuré : {channel.mention}"))
@bot.command()
@has_required_grade("Créateur++")
async def setlogsunwl(ctx,channel:discord.TextChannel):
    set_log_channel(ctx.guild.id,"unwl",channel.id)
    await ctx.send(embed=create_white_embed(f"Salon de logs UNWL configuré : {channel.mention}"))

@bot.command()
@has_required_grade()
async def logs(ctx):
    data=get_all_logs(ctx.guild.id)
    if not data:return await ctx.send(embed=create_white_embed("Aucun salon de logs configuré."))
    l=["Logs\n"]
    types={"general":"General","bl":"Bl","unbl":"Unbl","rank":"Rank","unrank":"Unrank","wl":"Wl","unwl":"Unwl"}
    for k,n in types.items():
        c=None
        for t,cid in data:
            if t==k:c=cid;break
        l.append(f"{n} : <#{c}>"if c else f"{n} : Non configuré")
    await ctx.send(embed=create_white_embed("\n".join(l)))

@bot.command()
@has_required_grade("Créateur++")
async def changelimit(ctx,grade:str,limit:int):
    grade=grade.lower()
    if grade not in["owner","sys","sys+","crea","crea++"]:
        return await ctx.send(embed=create_white_embed(f"Grade invalide. Grades : owner, sys, sys+, crea, crea++"))
    if limit<0 or limit>9999:return await ctx.send(embed=create_white_embed("Limite invalide. Utilise un nombre entre 0 et 9999."))
    m={"owner":"Owner","sys":"Sys","sys+":"Sys+","crea":"Créateur","crea++":"Créateur++"}
    BL_LIMITS[m[grade]]=limit
    await ctx.send(embed=create_white_embed(f"Limite de BL par heure pour **{m[grade]}** définie à **{limit}**."))

@bot.command()
async def ping(ctx):
    await ctx.send(embed=create_white_embed(f"Pong! Latence : **{round(bot.latency*1000)}ms**"))
@bot.command()
async def test(ctx):
    await ctx.send("Le bot répond !")

@bot.command()
@commands.check(lambda ctx:ctx.author.id==ADMIN_USER_ID)
async def savedb(ctx):
    try:
        await ctx.author.send(file=discord.File('akusa_bot.db'))
        await ctx.send(embed=create_white_embed("📩 DB envoyée en DM"))
    except:await ctx.send(embed=create_white_embed("❌ Erreur envoi DM"))

@bot.command()
@commands.check(lambda ctx:ctx.author.id==ADMIN_USER_ID)
async def setdb(ctx):
    if not ctx.message.attachments:
        return await ctx.send(embed=create_white_embed("❌ Attache le fichier .db"))
    try:
        await ctx.message.attachments[0].save('akusa_bot.db')
        global db_conn,db_cursor
        db_conn,db_cursor=init_database()
        await ctx.send(embed=create_white_embed("✅ DB restaurée"))
    except:await ctx.send(embed=create_white_embed("❌ Erreur restauration"))

@bot.command(name="block")
@commands.check(lambda ctx:ctx.author.id==ADMIN_USER_ID)
async def block(ctx,action=None,*,word=None):
    if not action:return await ctx.send(embed=create_white_embed("Usage : `&block add/remove/list/clear [mot]`"))
    a=action.lower()
    if a=="add":
        if not word:return await ctx.send(embed=create_white_embed("Usage : `&block add mot`"))
        if is_word_blocked(word):return await ctx.send(embed=create_white_embed(f"Le mot `{word}` est déjà bloqué."))
        add_blocked_word(word,ctx.author.id,ctx.author.name,get_current_time_french())
        await ctx.send(embed=create_white_embed(f"Le mot `{word}` a été ajouté à la liste des mots bloqués."))
    elif a=="remove":
        if not word:return await ctx.send(embed=create_white_embed("Usage : `&block remove mot`"))
        await ctx.send(embed=create_white_embed(f"Le mot `{word}` a été retiré de la liste des mots bloqués."if remove_blocked_word(word)else f"Le mot `{word}` n'est pas dans la liste."))
    elif a=="list":
        w=get_blocked_words()
        if not w:await ctx.send(embed=create_white_embed("Aucun mot bloqué."))
        else:await ctx.send(embed=create_white_embed("**Liste des mots bloqués :**\n"+"\n".join(f"• `{x}`"for x in w)))
    elif a=="clear":
        c=clear_blocked_words()
        await ctx.send(embed=create_white_embed(f"{c} mot(s) ont été supprimés de la liste."))
    else:await ctx.send(embed=create_white_embed("Action invalide. Utilise `add`, `remove`, `list` ou `clear`."))

@bot.command()
@has_required_grade("Créateur++")
async def protect(ctx,*,id=None):
    if not id:return await ctx.send(embed=create_white_embed("Usage : `&protect @user/id`"))
    r=await get_user_by_id_or_mention(ctx,id)
    if not r or not r[0]:return await ctx.send(embed=create_white_embed("❌ Utilisateur introuvable."))
    m,ison=r
    if is_protected(m.id):
        remove_protect(m.id)
        embed=create_white_embed(f" {m.mention} n'est plus protégé.")
        await send_log(ctx,"protect",{"Retiré par":ctx.author.mention,"Utilisateur":m.mention})
    else:
        add_protect(m.id,m.name,ctx.author.id,ctx.author.name,get_current_time_french())
        embed=create_white_embed(f" {m.mention} est désormais protégé.")
        await send_log(ctx,"protect",{"Ajouté par":ctx.author.mention,"Utilisateur":m.mention})
    await ctx.send(embed=embed)

@bot.command()
@has_required_grade()
async def protectlist(ctx):
    d=get_protect_list()
    if not d:return await ctx.send(embed=create_white_embed("Aucun utilisateur protégé."))
    await ctx.send(embed=create_white_embed("** Liste des protégés :**\n"+'\n'.join(f"• <@{i[0]}>"for i in d)))

@bot.command()
@commands.check(lambda ctx:ctx.author.id==ADMIN_USER_ID)
async def pclear(ctx):
    c=clear_protect()
    await ctx.send(embed=create_white_embed(f" Protection de {c} utilisateur retiré ."))
    await send_log(ctx,"protect",{"Action":"Vider protect","Par":ctx.author.mention,"Nombre":str(c)})

if __name__=="__main__":
    print("Démarrage du bot Akusa...")
    bot.run(TOKEN)