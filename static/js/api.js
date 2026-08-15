const API_BASE = 'http://127.0.0.1:8000/api';

async function api(chemin, options = {}) {
    const token = localStorage.getItem('access_token');
    const entetes = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) entetes['Authorization'] = `Bearer ${token}`;

    let reponse = await fetch(`${API_BASE}${chemin}`, { ...options, headers: entetes, cache: 'no-store' });

    if (reponse.status === 401) {
        const refresh = localStorage.getItem('refresh_token');
        if (refresh) {
            const rafraichi = await fetch(`${API_BASE}/auth/rafraichir/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh }),
                cache: 'no-store',
            });
            if (rafraichi.ok) {
                const data = await rafraichi.json();
                localStorage.setItem('access_token', data.access);
                entetes['Authorization'] = `Bearer ${data.access}`;
                reponse = await fetch(`${API_BASE}${chemin}`, { ...options, headers: entetes, cache: 'no-store' });
            } else {
                localStorage.clear();
                window.location.href = '/connexion.html';
                return null;
            }
        } else {
            window.location.href = '/connexion.html';
            return null;
        }
    }
    return reponse;
}

async function apiJSON(chemin, options = {}) {
    const reponse = await api(chemin, options);
    if (!reponse) return null;
    if (!reponse.ok) {
        const erreur = await reponse.json().catch(() => ({}));
        let message = erreur.detail;
        if (!message) {
            const morceaux = Object.entries(erreur).map(([champ, valeurs]) => {
                const texte = Array.isArray(valeurs) ? valeurs.join(' ') : valeurs;
                return champ === 'non_field_errors' ? texte : `${champ} : ${texte}`;
            });
            message = morceaux.length ? morceaux.join(' — ') : `Erreur ${reponse.status}`;
        }
        throw new Error(message);
    }
    return reponse.status === 204 ? null : reponse.json();
}
