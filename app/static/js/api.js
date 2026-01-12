/**
 * Wrapper na Fetch API do komunikacji z backendem Flask
 */

// --- HOSTS (GOTOWE - WZÓR) ---
export async function fetchHosts() {
    const res = await fetch('/api/hosts/hosts');
    return await res.json();
}
export async function createHost(data) {
    const res = await fetch('/api/hosts/ips', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if(!res.ok) throw new Error((await res.json()).error);
    return await res.json();
}
export async function updateHost(id, data) {
    const res = await fetch(`/api/hosts/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if(!res.ok) throw new Error('Błąd edycji hosta');
    return await res.json();
}
export async function removeHost(id) {
    await fetch(`/api/hosts/${id}`, { method: 'DELETE' });
}

// --- MONITORING / LOGI (GOTOWE) ---
export async function checkHostStatus(id, osType) {
    const endpoint = (osType === 'LINUX') 
        ? `/api/hosts/${id}/ssh-info` 
        : `/api/hosts/${id}/windows-info`;
        
    const res = await fetch(endpoint);
    if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || `Błąd HTTP ${res.status}`);
    }
    return await res.json();
}

export async function triggerLogFetch(hostId) {
    const res = await fetch(`/api/hosts/${hostId}/logs`, {
        method: 'POST'
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Błąd pobierania logów');
    }
    return await res.json();
}

export async function fetchIPs() {
    const response = await fetch('/api/hosts/ips'); //prośba do serwera o uzyskanie ip
    if (!response.ok) throw new Error('Nie udało się pobrać bazy IP'); //sprawdzamy status i czy nie było błędu
    return await response.json();
}

export async function createIP(data) {
    const response = await fetch('/api/hosts/ips', { //pod ten sam adres, ale z parametrami
        method: 'POST', //typ metody
        headers: {
            'Content-Type': 'application/json' //jak wysyłamy mu dane
        },
        body: JSON.stringify(data) //na tekst bo nie możemy obiektów
    });

    if (!response.ok) throw new Error('Błąd podczas dodawania adresu IP')
    return await response.json()
}

export async function updateIP(id, data) {
    const response = await fetch('/api/hosts/ips/${id}', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });

    if (!response.ok) throw new Error('Błąd podczas aktualizacji IP');
    return await response.json();
}

export async function removeIP(id) {
    const response = await fetch('/api/hosts/ips/${id}', {
        method: 'DELETE'
    });

    if (!response.ok) throw new Error('Błąd podczas usuwania iP');
    return true;
}

export async function fetchAlerts() {
    const response = await fetch('/api/hosts/alerts'); //prośba do serwera o uzyskanie alertów

    if (!response.ok) throw new Error('Nie udało mi się pobrać alertów');
    return await response.json();
}