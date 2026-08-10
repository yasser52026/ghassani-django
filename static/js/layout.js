const LIBELLES_ROLES = {
    administrateur: 'Administrateur', gestionnaire: 'Gestionnaire RH / Paie',
    chef_service: 'Chef de service', directeur: 'Directeur', consultation: 'Consultation seule',
};

async function chargerLayout(pageActive) {
    if (!localStorage.getItem('access_token')) {
        window.location.href = '/connexion.html';
        return null;
    }
    let utilisateur;
    try {
        utilisateur = await apiJSON('/comptes/moi/');
    } catch {
        window.location.href = '/connexion.html';
        return null;
    }

    const peutVoirAgents = ['administrateur', 'gestionnaire', 'directeur', 'chef_service'].includes(utilisateur.role);
    const peutVoirDemandes = ['administrateur', 'gestionnaire'].includes(utilisateur.role);

    const liens = [
        { href: '/index.html', texte: 'Tableau de bord', cle: 'accueil' },
        { href: '/services.html', texte: 'Services', cle: 'services' },
        { href: '/calendrier.html', texte: 'Calendrier', cle: 'calendrier' },
        { href: '/plannings.html', texte: 'Plannings', cle: 'plannings' },
        { href: '/decomptes.html', texte: 'Décomptes', cle: 'decomptes' },
    ];
    if (peutVoirAgents) {
        liens.push({ href: '/absences.html', texte: 'Absences', cle: 'absences' });
        liens.push({ href: '/agents.html', texte: 'Agents', cle: 'agents' });
    }
    if (peutVoirDemandes) liens.push({ href: '/demandes.html', texte: 'Demandes', cle: 'demandes' });
    liens.push({ href: '/profil.html', texte: 'Mon profil', cle: 'profil' });

    const navHtml = liens.map(l => `<a href="${l.href}" class="${l.cle === pageActive ? 'actif' : ''}">${l.texte}</a>`).join('');

    document.getElementById('sidebar-container').innerHTML = `
        <nav class="sidebar">
            <a class="sidebar-brand" href="/index.html">CHR de Fès<small>Heures supplémentaires</small></a>
            <div class="sidebar-nav">${navHtml}</div>
            <div class="sidebar-footer">
                <div class="nom">${utilisateur.nom_complet}</div>
                <div class="role">${LIBELLES_ROLES[utilisateur.role] || utilisateur.role}</div>
                <button class="btn-deconnexion" onclick="localStorage.clear(); window.location.href='/connexion.html';">Déconnexion</button>
            </div>
        </nav>
    `;
    return utilisateur;
}