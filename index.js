const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
require('dotenv').config();

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
const channelId = 'ID_DU_CHANNEL'; // Remplace par l'ID du channel où compter

// Quand le bot est prêt
client.once('ready', () => {
    console.log(`✅ ${client.user.tag} est connecté !`);
    console.log(`📊 Bot compteur actif dans le channel : ${channelId}`);
});

// Commande !count
client.on('messageCreate', async message => {
    if (message.author.bot) return;

    // Incrémenter le compteur
    if (message.content.toLowerCase() === '!count') {
        count++;
        
        const embed = new EmbedBuilder()
            .setColor('#00ff00')
            .setTitle('📊 Compteur')
            .setDescription(`Le compteur est à : **${count}**`)
            .setFooter({ text: `Demandé par ${message.author.tag}` })
            .setTimestamp();

        await message.channel.send({ embeds: [embed] });
    }

    // Réinitialiser le compteur (admin uniquement)
    if (message.content.toLowerCase() === '!reset' && message.member.permissions.has('Administrator')) {
        count = 0;
        await message.channel.send('🔄 Compteur réinitialisé à **0** !');
    }

    // Afficher l'aide
    if (message.content.toLowerCase() === '!help') {
        const helpEmbed = new EmbedBuilder()
            .setColor('#0099ff')
            .setTitle('🤖 Commandes du Bot Compteur')
            .addFields(
                { name: '!count', value: 'Incrémente et affiche le compteur', inline: true },
                { name: '!reset', value: 'Réinitialise le compteur (Admin)', inline: true },
                { name: '!help', value: 'Affiche cette aide', inline: true }
            );
        await message.channel.send({ embeds: [helpEmbed] });
    }
});

// Connexion avec le token
const token = process.env.TOKEN || 'TON_TOKEN_ICI';
client.login(token);

// Gestion des erreurs
client.on('error', console.error);
process.on('unhandledRejection', console.error);