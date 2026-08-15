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

    const estConsultation = utilisateur.role === 'consultation';
    const peutVoirAgents = ['administrateur', 'gestionnaire', 'directeur', 'chef_service'].includes(utilisateur.role);
    const peutVoirDemandes = ['administrateur', 'gestionnaire'].includes(utilisateur.role);

    let liens;
    if (estConsultation) {
        liens = [
            { href: '/mon-planning.html', texte: 'Mon planning', cle: 'mon-planning' },
            { href: '/profil.html', texte: 'Mon profil', cle: 'profil' },
        ];
    } else {
        liens = [
            { href: '/index.html', texte: 'Mes décomptes', cle: 'accueil' },
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
        if (['administrateur', 'directeur', 'gestionnaire', 'chef_service'].includes(utilisateur.role)) {
            liens.push({ href: '/tableau-bord.html', texte: 'Tableau de bord', cle: 'tableau-bord' });
        }
        if (['administrateur', 'directeur'].includes(utilisateur.role)) {
            liens.push({ href: '/journal-audit.html', texte: "Journal d'audit", cle: 'journal-audit' });
        }
        liens.push({ href: '/profil.html', texte: 'Mon profil', cle: 'profil' });
    }

    const navHtml = liens.map(l => `<a href="${l.href}" class="${l.cle === pageActive ? 'actif' : ''}">${l.texte}</a>`).join('');
    const accueilHref = estConsultation ? '/mon-planning.html' : '/index.html';

    document.getElementById('sidebar-container').innerHTML = `
        <nav class="sidebar">
            <a class="sidebar-brand" href="${accueilHref}">CHR de Fès<small>Heures supplémentaires</small></a>
            <div class="sidebar-nav">${navHtml}</div>
            <div class="sidebar-footer">
                <div class="nom">${utilisateur.nom_complet}</div>
                <div class="role">${LIBELLES_ROLES[utilisateur.role] || utilisateur.role}</div>
                <button class="btn-deconnexion" onclick="localStorage.clear(); window.location.href='/connexion.html';">Déconnexion</button>
            </div>
        </nav>
    `;

    if (['administrateur', 'gestionnaire', 'directeur', 'chef_service'].includes(utilisateur.role)) {
        verifierNotifications();
        setInterval(verifierNotifications, 30000);
    }

    return utilisateur;
}

async function verifierNotifications() {
    let notifications;
    try {
        notifications = await apiJSON('/comptes/notifications/');
    } catch {
        return;
    }
    if (!notifications || !notifications.length) return;

    const existant = document.getElementById('popupNotifications');
    if (existant) existant.remove();

    const popup = document.createElement('div');
    popup.id = 'popupNotifications';
    popup.className = 'popup-notifications-overlay';
    popup.innerHTML = `
        <div class="popup-notifications-carte">
            <h5>Indisponibilité déclarée</h5>
            <ul>${notifications.map(n => `<li>${n.message}</li>`).join('')}</ul>
            <button class="btn btn-primary" id="boutonFermerNotifications">OK</button>
        </div>
    `;
    document.body.appendChild(popup);
    document.getElementById('boutonFermerNotifications').addEventListener('click', async () => {
        popup.remove();
        try { await apiJSON('/comptes/notifications/lues/', { method: 'POST' }); } catch {}
    });
}
