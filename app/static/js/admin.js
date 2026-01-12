import { createEl, clearContainer } from './dom.js';
// Zauważ: Usuwamy importy fetchIPs itp., bo ich nie ma w api.js (student musi je dodać po napisaniu)
import { fetchHosts, createHost, updateHost, removeHost } from './api.js'; 
import { fetchIPs, createIP, updateIP, removeIP } from './api.js';

// --- SEKCJA HOSTÓW ---
const hostsContainer = document.getElementById('hostsListAdmin');
const hostForm = document.getElementById('hostForm');

// --- SEKCJA IP (Ukryta) ---
const ipContainer = document.getElementById('ipListAdmin');
const ipForm = document.getElementById('ipForm');
const refreshIPsBtn = document.getElementById('refreshIPsBtn');

// --- MODALE ---
let hostModal = null;
let ipModal = null;

export async function initAdmin() {
    // Inicjalizacja Bootstrap Modals
    const hostModalEl = document.getElementById('editHostModal');
    if (hostModalEl) hostModal = new bootstrap.Modal(hostModalEl);
    
    const ipModalEl = document.getElementById('editIPModal');
    if (ipModalEl) ipModal = new bootstrap.Modal(ipModalEl);

    // Event Listeners - Hosty
    if (hostForm) hostForm.addEventListener('submit', handleAddHost);
    if (document.getElementById('saveHostBtn')) {
        document.getElementById('saveHostBtn').addEventListener('click', handleSaveHost);
    }
    
    if (ipForm) ipForm.addEventListener('submit', handleAddIP); //przypisanie działania przycisku do zatwierdzenia formularza
    if (refreshIPsBtn) refreshIPsBtn.addEventListener('click', refreshIPs); //przypisanie działania do odświeżania
    if (document.getElementById('saveIPBtn')) {
        document.getElementById('saveIPBtn').addEventListener('click', handleSaveIP);
    }
    
    if (ipContainer) await refreshIPs();

    // Start Hosty
    if (hostsContainer) await refreshHosts();
}

// ======================= LOGIKA HOSTÓW (GOTOWA) =======================

async function refreshHosts() {
    clearContainer(hostsContainer);
    try {
        const hosts = await fetchHosts();
        hosts.forEach(renderHostRow);
    } catch(e) { console.error(e); }
}

function renderHostRow(host) {
    const item = createEl('div', ['list-group-item', 'd-flex', 'justify-content-between', 'align-items-center'], '', hostsContainer);
    
    const info = createEl('div', [], '', item);
    const icon = host.os_type === 'LINUX' ? '🐧' : '🪟';
    createEl('span', ['me-2'], icon, info);
    createEl('span', ['fw-bold', 'me-2'], host.hostname, info);
    createEl('small', ['text-muted'], host.ip_address, info);

    const btnGroup = createEl('div', ['btn-group', 'btn-group-sm'], '', item);
    
    const editBtn = createEl('button', ['btn', 'btn-outline-secondary'], '✏️', btnGroup);
    editBtn.addEventListener('click', () => openHostModal(host));

    const delBtn = createEl('button', ['btn', 'btn-outline-danger'], '🗑️', btnGroup);
    delBtn.addEventListener('click', async () => {
        if(confirm(`Usunąć hosta ${host.hostname}?`)) {
            await removeHost(host.id);
            await refreshHosts();
        }
    });
}

async function handleAddHost(e) {
    e.preventDefault();
    const data = {
        hostname: document.getElementById('hostName').value,
        ip_address: document.getElementById('hostIP').value,
        os_type: document.getElementById('hostOS').value
    };
    try {
        await createHost(data);
        e.target.reset();
        await refreshHosts();
    } catch(err) { alert(err.message); }
}

function openHostModal(host) {
    document.getElementById('editHostId').value = host.id;
    document.getElementById('editHostName').value = host.hostname;
    document.getElementById('editHostIP').value = host.ip_address;
    document.getElementById('editHostOS').value = host.os_type;
    hostModal.show();
}

async function handleSaveHost() {
    const id = document.getElementById('editHostId').value;
    const data = {
        hostname: document.getElementById('editHostName').value,
        ip_address: document.getElementById('editHostIP').value,
        os_type: document.getElementById('editHostOS').value
    };
    try {
        await updateHost(id, data);
        hostModal.hide();
        await refreshHosts();
    } catch(err) { alert(err.message); }
}


// ======================= LOGIKA IP REGISTRY (DO ODBLOKOWANIA) =======================

async function refreshIPs() { //do odświeżania listy IPs w HTML
    clearContainer(ipContainer); //wyczyszczenie starej listy w HTML
    try {
        const ips = await fetchIPs(); //pobieramy nowe dane z API, await żeby poczkać aż odpowie
        if(ips.length === 0) createEl('div', ['p-2', 'text-muted', 'small'], 'Pusto.', ipContainer);
        ips.forEach(renderIPRow); //dla każdego IP tworzymy nowy wiersz
    } catch(e) { console.error("Błąd IP:", e); }
}

function renderIPRow(ip) {
    const item = createEl('div', ['list-group-item', 'd-flex', 'justify-content-between', 'align-items-center'], '', ipContainer);
    //tworzymy kontener wiersz

    const info = createEl('div', [], '', item);
    let color = 'bg-secondary';
    if(ip.status === 'TRUSTED') color = 'bg-success';
    if(ip.status === 'BANNED') color = 'bg-danger'; //odpowiedni kolor w zależnosci od koloru
    createEl('span', ['badge', color, 'me-2'], ip.status[0], info); //mała ikonka z literą statusu
    
    createEl('span', ['fw-bold', 'font-monospace', 'me-2'], ip.ip_address, info);
    //fonta-monospace - czcionka o stałej szerokosci - ulatwia czytanie adresów IP

    let timeStr = '-';
    if (ip.last_seen && ip.last_seen !== '-') {
        const utcDate = new Date(ip.last_seen.replace(" ", "T") + "Z"); //konwersja do obiektu Date
        timeStr = utcDate.toLocaleString(); //do lokalnego czasu użytkownika
    }
    createEl('small', ['text-muted'], timeStr, info);

    const btnGroup = createEl('div', ['btn-group', 'btn-group-sm'], '', item);
    
    const editBtn = createEl('button', ['btn', 'btn-outline-secondary'], '✏️', btnGroup);
    editBtn.addEventListener('click', () => openIPModal(ip)); //przekazujemy IP żeby mógł otworzyć cały obiekt

    const delBtn = createEl('button', ['btn', 'btn-outline-danger'], '🗑️', btnGroup);
    delBtn.addEventListener('click', async () => {
        if(confirm(`Usunąć adres IP ${ip.ip_address} z rejestru?`)) { //pyta o potwierdzenie
            try {
                await removeIP(ip.id); //wywołuje funkcję wysyłającą zapytanie DELETE do serwera
                await refreshIPs(); //czeka aż się uda i odświeża
            } catch (err) { alert("Błąd usuwania: " + err.message); }
        }
    });
}

async function handleAddIP(e) { //funkcja do wysyłania głównego formularza dodawania IP z config.html
    e.preventDefault();
    const data = {
        ip_address: document.getElementById('regIP').value, //bierze wartości z pól tekstowych i ładuje do data
        status: document.getElementById('regStatus').value
    };
    try {
        await createIP(data); //wysyła żądanie POST
        e.target.reset(); //czyszczenie formularza w przypadku potwierdzenia sukcesu
        await refreshIPs();
    } catch(err) { alert(err.message); }
}

function openIPModal(ip) { //żeby formularz był wypełniony gdy chcemy edytować
    document.getElementById('editIPId').value = ip.id; //to ukryte żeby wiedzieć gdzie zapisać
    document.getElementById('editIPVal').value = ip.ip_address;
    document.getElementById('editIPStatus').value = ip.status;
    ipModal.show();
}

async function handleSaveIP() { //gdy zatwierdzimy zapisanie 
    const id = document.getElementById('editIPId').value; //gdy w oknie edycji klikniemy przycisk "Zapisz"
    const data = { 
        ip_address: document.getElementById('editIPVal').value, //zbiera wartości z pól
        status: document.getElementById('editIPStatus').value
    };
    try {
        await updateIP(id, data); //wywołuje żądanie PUT do serwera
        ipModal.hide(); //ukrycie okna edycji
        await refreshIPs(); //odświeżenie
    } catch(err) { alert(err.message); }
}