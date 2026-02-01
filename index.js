const { Client, GatewayIntentBits, EmbedBuilder, PermissionsBitField, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

// Création du client Discord
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers
    ]
});

// Variables pour le compteur
let count = 0;

// Quand le bot est prêt
client.once('ready', () => {
    console.log(`✅ ${client.user.tag} est connecté !`);
    console.log(`📊 Bot compteur actif`);
    
    // Optionnel : mettre un statut
    client.user.setActivity('/panel pour admin', { type: 3 });
});

// Commande /panel (admin seulement)
client.on('messageCreate', async (message) => {
    if (message.author.bot) return;
    
    // Vérifier si c'est la commande /panel
    if (message.content.toLowerCase() === '/panel') {
        
        // Vérifier les permissions administrateur
        if (!message.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
            const embed = new EmbedBuilder()
                .setColor('#ff0000')
                .setTitle('❌ Accès refusé')
                .setDescription('Seuls les administrateurs peuvent utiliser cette commande.')
                .setTimestamp();
            
            return message.channel.send({ embeds: [embed] }).then(msg => {
                setTimeout(() => msg.delete(), 5000);
            });
        }
        
        // Créer le panel admin
        const panelEmbed = new EmbedBuilder()
            .setColor('#5865F2')
            .setTitle('🛠️ PANEL ADMIN - BOT COMPTEUR')
            .setDescription('Gestion du bot compteur')
            .addFields(
                { name: '📊 Compteur actuel', value: `**${count}**`, inline: true },
                { name: '🔄 Commandes', value: '!count - !reset - !help', inline: true },
                { name: '👥 Utilisation', value: `${message.guild.memberCount} membres`, inline: true }
            )
            .setFooter({ text: `Panel demandé par ${message.author.username}` })
            .setTimestamp();
        
        // Créer les boutons
        const row = new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder()
                    .setCustomId('reset_count')
                    .setLabel('🔄 Réinitialiser')
                    .setStyle(ButtonStyle.Danger),
                new ButtonBuilder()
                    .setCustomId('show_stats')
                    .setLabel('📈 Statistiques')
                    .setStyle(ButtonStyle.Primary),
                new ButtonBuilder()
                    .setCustomId('close_panel')
                    .setLabel('❌ Fermer')
                    .setStyle(ButtonStyle.Secondary)
            );
        
        // Envoyer le panel
        const panelMessage = await message.channel.send({
            embeds: [panelEmbed],
            components: [row]
        });
        
        // Collecteur d'interactions pour les boutons
        const collector = panelMessage.createMessageComponentCollector({
            time: 60000 // 1 minute
        });
        
        collector.on('collect', async (interaction) => {
            // Vérifier à nouveau les permissions admin
            if (!interaction.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
                return interaction.reply({
                    content: '❌ Permission refusée.',
                    ephemeral: true
                });
            }
            
            if (interaction.customId === 'reset_count') {
                count = 0;
                await interaction.reply({
                    content: '✅ Compteur réinitialisé à **0** !',
                    ephemeral: true
                });
                
                // Mettre à jour l'embed
                panelEmbed.spliceFields(0, 1, { name: '📊 Compteur actuel', value: `**${count}**`, inline: true });
                await interaction.message.edit({ embeds: [panelEmbed] });
                
            } else if (interaction.customId === 'show_stats') {
                const statsEmbed = new EmbedBuilder()
                    .setColor('#00ff00')
                    .setTitle('📈 Statistiques')
                    .addFields(
                        { name: 'Compteur', value: `${count}` },
                        { name: 'Serveur', value: `${message.guild.name}` },
                        { name: 'Membres', value: `${message.guild.memberCount}` }
                    )
                    .setTimestamp();
                
                await interaction.reply({
                    embeds: [statsEmbed],
                    ephemeral: true
                });
                
            } else if (interaction.customId === 'close_panel') {
                await interaction.message.delete();
                await interaction.reply({
                    content: '✅ Panel fermé.',
                    ephemeral: true
                });
            }
        });
        
        collector.on('end', collected => {
            console.log(`Collecteur terminé. ${collected.size} interactions`);
        });
        
        return;
    }
    
    // Commandes normales (garder les anciennes)
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

    if (message.content.toLowerCase() === '!reset') {
        if (!message.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
            return message.channel.send('❌ Tu n\'as pas la permission de réinitialiser le compteur !');
        }
        
        count = 0;
        await message.channel.send('🔄 Compteur réinitialisé à **0** !');
    }

    if (message.content.toLowerCase() === '!help') {
        const helpEmbed = new EmbedBuilder()
            .setColor('#0099ff')
            .setTitle('🤖 Commandes du Bot Compteur')
            .addFields(
                { name: '!count', value: 'Incrémente et affiche le compteur', inline: true },
                { name: '!reset', value: 'Réinitialise le compteur (Admin)', inline: true },
                { name: '/panel', value: 'Panel de contrôle admin', inline: true },
                { name: '!help', value: 'Affiche cette aide', inline: true }
            );

        await message.channel.send({ embeds: [helpEmbed] });
    }
});

// Récupérer le token depuis Railway
const token = process.env.TOKEN || process.env.DISCORD_TOKEN;

if (!token) {
    console.error('❌ Token Discord non trouvé !');
    console.log('ℹ️ Sur Railway : Variables > Ajouter TOKEN');
    process.exit(1);
}

client.login(token)
    .then(() => {
        console.log('🔗 Connexion au Discord API...');
    })
    .catch((error) => {
        console.error('❌ Erreur de connexion :', error.message);
        process.exit(1);
    });

// Gestion des erreurs
client.on('error', console.error);
process.on('unhandledRejection', console.error);