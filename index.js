const { Client, GatewayIntentBits, EmbedBuilder, PermissionsBitField } = require('discord.js');

// Création du client Discord
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

// Variables pour le compteur
let count = 0;
const channelId = 'ID_DU_CHANNEL'; // À REMPLACER par l'ID réel du channel

// Quand le bot est prêt
client.once('ready', () => {
    console.log(`✅ ${client.user.tag} est connecté !`);
    console.log(`📊 Bot compteur actif`);
    
    // Optionnel : mettre un statut
    client.user.setActivity('!help pour les commandes', { type: 3 }); // type: 3 = WATCHING
});

// Commande !count
client.on('messageCreate', async (message) => {
    // Éviter les boucles avec les autres bots
    if (message.author.bot) return;

    // Incrémenter le compteur
    if (message.content.toLowerCase() === '!count') {
        count++;
        
        const embed = new EmbedBuilder()
            .setColor('#00ff00')
            .setTitle('📊 Compteur')
            .setDescription(`Le compteur est à : **${count}**`)
            .setFooter({ text: `Demandé par ${message.author.username}` })
            .setTimestamp();

        await message.channel.send({ embeds: [embed] });
    }

    // Réinitialiser le compteur (admin uniquement)
    if (message.content.toLowerCase() === '!reset') {
        // Vérifier les permissions
        if (!message.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
            return message.channel.send('❌ Tu n\'as pas la permission de réinitialiser le compteur !');
        }
        
        count = 0;
        await message.channel.send('🔄 Compteur réinitialisé à **0** !');
    }

    // Afficher l'aide
    if (message.content.toLowerCase() === '!help' || message.content.toLowerCase() === '!commands') {
        const helpEmbed = new EmbedBuilder()
            .setColor('#0099ff')
            .setTitle('🤖 Commandes du Bot Compteur')
            .addFields(
                { name: '!count', value: 'Incrémente et affiche le compteur', inline: true },
                { name: '!reset', value: 'Réinitialise le compteur (Admin uniquement)', inline: true },
                { name: '!help', value: 'Affiche cette aide', inline: true }
            )
            .setFooter({ text: 'Bot développé avec Discord.js v14' })
            .setTimestamp();

        await message.channel.send({ embeds: [helpEmbed] });
    }
});

// Récupérer le token depuis les variables d'environnement
const token = process.env.TOKEN || process.env.DISCORD_TOKEN;

if (!token) {
    console.error('❌ ERREUR : Token Discord non trouvé !');
    console.log('ℹ️ Configure une variable d\'environnement TOKEN ou DISCORD_TOKEN');
    console.log('ℹ️ Sur Railway : Variables > Ajouter TOKEN');
    process.exit(1);
}

// Connexion
client.login(token)
    .then(() => {
        console.log('🔗 Connexion au Discord API...');
    })
    .catch((error) => {
        console.error('❌ Erreur de connexion :', error.message);
        if (error.message.includes('token')) {
            console.log('⚠️ Vérifie que ton token Discord est correct');
        }
        process.exit(1);
    });

// Gestion des erreurs
client.on('error', (error) => {
    console.error('❌ Erreur Discord.js :', error);
});

process.on('unhandledRejection', (error) => {
    console.error('❌ Erreur non gérée :', error);
});

// Gestion propre de l'arrêt
process.on('SIGINT', () => {
    console.log('🛑 Arrêt du bot...');
    client.destroy();
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('🛑 Arrêt du bot (SIGTERM)...');
    client.destroy();
    process.exit(0);
});