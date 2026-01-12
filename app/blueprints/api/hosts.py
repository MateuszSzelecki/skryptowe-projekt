import time
from flask import Blueprint, jsonify, request, current_app
from datetime import timezone, datetime
import os

from flask_login import login_required

from app.models import Host, LogSource, LogArchive, Alert, IPRegistry
from app.services.remote_client import RemoteClient
from app.services.win_client import WinClient
from app.services.log_collector import LogCollector
from app.services.data_manager import DataManager
from app.services.log_analyzer import LogAnalyzer
from app.extensions import db

api_bp = Blueprint("api_hosts", __name__)

# --- CRUD HOSTS (GOTOWE - ABY UI DZIAŁAŁO) ---

@api_bp.route("/hosts", methods=["GET"])
@login_required
def get_hosts():
    hosts = Host.query.all()
    return jsonify([h.to_dict() for h in hosts])

@api_bp.route("/hosts", methods=["POST"])
@login_required
def add_host():
    data = request.get_json()
    if not data: return jsonify({"error": "Brak danych"}), 400
    if Host.query.filter_by(ip_address=data.get("ip_address")).first():
        return jsonify({"error": "IP musi być unikalne"}), 409
    new_host = Host(hostname=data.get("hostname"), ip_address=data.get("ip_address"), os_type=data.get("os_type"))
    db.session.add(new_host)
    db.session.commit()
    return jsonify(new_host.to_dict()), 201

@api_bp.route("/hosts/<int:host_id>", methods=["DELETE"])
@login_required
def delete_host(host_id):
    host = Host.query.get_or_404(host_id)
    db.session.delete(host)
    db.session.commit()
    return jsonify({"message": "Usunięto hosta"}), 200

@api_bp.route("/hosts/<int:host_id>", methods=["PUT"])
@login_required
def update_host(host_id):
    host = Host.query.get_or_404(host_id)
    data = request.get_json()
    if 'hostname' in data: host.hostname = data['hostname']
    if 'ip_address' in data: host.ip_address = data['ip_address']
    if 'os_type' in data: host.os_type = data['os_type']
    db.session.commit()
    return jsonify(host.to_dict()), 200

# --- MONITORING LIVE (GOTOWE) ---

@api_bp.route("/hosts/<int:host_id>/ssh-info", methods=["GET"])
@login_required
def get_ssh_info(host_id):
    host = Host.query.get_or_404(host_id)
    ssh_user = current_app.config.get("SSH_DEFAULT_USER", "vagrant")
    ssh_port = current_app.config.get("SSH_DEFAULT_PORT", 2222)
    ssh_key = current_app.config.get("SSH_KEY_FILE")
    try:
        with RemoteClient(host=host.ip_address, user=ssh_user, port=ssh_port, key_file=ssh_key) as remote:
            ram_out, _ = remote.run("free -m | grep Mem | awk '{print $7}'")
            disk_percentage, _ = remote.run("df -h | grep '/$' | awk '{print $5}'")
            if not disk_percentage: disk_percentage, _ = remote.run("df -h | grep '/dev/sda1' | awk '{print $5}'")
            disk_total, _ = remote.run("df -h | grep '/dev/sda1' | awk '{print $2}'")
            cpu_load, _ = remote.run("uptime | awk -F'load average:' '{ print $2 }' | cut -d',' -f1")
            uptime_seconds_str, _ = remote.run("cat /proc/uptime | awk '{print $1}'")
            uptime_formatted = "N/A"
            try:
                total_seconds = float(uptime_seconds_str)
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                uptime_formatted = f"{hours}h {minutes}m"
            except: pass

            return jsonify({
                "free_ram_mb": ram_out.strip(), "disk_info": disk_percentage.strip(),
                "disk_total": disk_total.strip(), "cpu_load": cpu_load.strip(), "uptime_hours": uptime_formatted
            }), 200
    except Exception as e:
        return jsonify({"error": f"Błąd połączenia: {str(e)}"}), 500

@api_bp.route("/hosts/<int:host_id>/windows-info", methods=["GET"])
@login_required
def get_windows_info(host_id):
    import psutil
    host = Host.query.get_or_404(host_id)
    if host.os_type != "WINDOWS": return jsonify({"error": "Wrong OS"}), 400
    try:
        mem = psutil.virtual_memory()
        free_ram_mb = str(round(mem.available / (1024 * 1024)))
        cpu_load = f"{psutil.cpu_percent(interval=0.1)}%"
        try:
            usage = psutil.disk_usage("C:\\")
            disk_percentage = f"{usage.percent}%"
            disk_total = f"{round(usage.total / (1024**3), 1)}GB"
        except:
            disk_percentage, disk_total = "N/A", "?"
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.now() - boot_time).total_seconds()
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return jsonify({
            "free_ram_mb": free_ram_mb, "disk_info": disk_percentage,
            "disk_total": disk_total, "cpu_load": cpu_load, "uptime_hours": f"{hours}h {minutes}m"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===================================================================
# MIEJSCE NA TWOJĄ IMPLEMENTACJĘ (ZADANIE 2 i 3)
# ===================================================================

@api_bp.route("/hosts/<int:host_id>/logs", methods=["POST"])
@login_required
def fetch_logs(host_id):
    host = Host.query.get_or_404(host_id) #pobieramy obiekt hosta z bazy
    
    #szukamy w bazie informacji kiedy ostatnio pobieraliśmy logi z tego konkretnego hosta
    log_source = LogSource.query.filter_by(host_id=host.id).first() 
    if not log_source: #jeśli jeszcze nie pobieraliśmy
        log_source = LogSource(host_id=host.id, log_type='security', last_fetch=None)
        #last_fetch=None - pobierz logi od początku historii
        db.session.add(log_source)
        db.session.commit()

    logs = []

    try:
        if host.os_type == 'LINUX':
            ssh_user = current_app.config.get("SSH_DEFAULT_USER")
            ssh_port = current_app.config.get("SSH_DEFAULT_PORT")
            ssh_key = current_app.config.get("SSH_KEY_FILE")

            with RemoteClient(host=host.ip_address, user=ssh_user, port=ssh_port, key_file=ssh_key) as client:
                raw_data = LogCollector.get_linux_logs(client, since=log_source.last_fetch)
                logs = raw_data

        elif host.os_type == 'WINDOWS':
            client = WinClient()
            raw_data = LogCollector.get_windows_logs(client, since=log_source.last_fetch)
            logs = raw_data

        if not logs: #jeśli brak nowych logów na serwerze to nie marnujemy zasobów na zapis pliku
            return jsonify({"message": "Brak nowych logów do pobrania", "alerts": 0}), 200
        
        filename = DataManager.save_logs_to_parquet(logs, host.id) #zapisanie logów do pliku Parquet
        #format Parquet jest wydajny, kolumnowy, odporny na manipulacje

        new_archive = LogArchive(host_id=host.id, filename=filename)
        db.session.add(new_archive) #rejestrujemy w bazie fakt stworzenia nowego pliku z logami z konkretnego hosta

        log_source.last_fetch = datetime.now(timezone.utc) #przesuwamy wskaźnik czasu na teraz

        db.session.commit() #zatwierdzamy new_archive i last_fetch

        alerts_found = LogAnalyzer.analyze_parquet(filename, host.id)
        #analizator otwiera plik Parquet i analizuje pod kątem wykrycia oznaczonych IP, np.: banned 

        return jsonify({ "message": f"Pobrano {len(logs)} logów.", "alerts": alerts_found, "archive": filename }), 200
    
    except Exception as ex:
        db.session.rollback() #w razie błędu cofamy niedokończone zmiany w bazie danych, aby nie zostawiać śmieci
        return jsonify({ "error": f"Błąd podczas procesu ETL: {str(ex)}"}), 500

@api_bp.route("/ips", methods=["GET"])
@login_required
def get_ips():
    ips = IPRegistry.query.order_by(IPRegistry.last_seen.desc()).all()
    # pobieramy wszystkie adresy IP z rejestru sortując od widzianego najbardziej niedawno
    return jsonify([ip.to_dict() for ip in ips]) #zmieniamy na słowniki żeby zwrócić w JSONie

@api_bp.route("/ips", methods=["POST"])
@login_required
def add_ip():
    data = request.get_json() #pobieramy dane w JSON z frontendu

    if not data or 'ip_address' not in data: #czy są dane i czy zawierają klucz 'ip_address'
        return jsonify({"error": "Brak adresu IP"}), 400
    
    existing = IPRegistry.query.filter_by(ip_address=data['ip_address']).first()
    #sprawdzamy czy takie IP już istnieje aby uniknąć błędów powielenia adresu ip
    if existing:
        return jsonify({"error": "Ten adres IP jest już w bazie"}), 409
    
    new_ip = IPRegistry(
        ip_address=data['ip_address'],
        status = data.get('status', 'UNKNOWN'),
        last_seen = datetime.now(timezone.utc)
    )

    db.session.add(new_ip)
    db.session.commit()

    return jsonify(new_ip.to_dict(), 201) # zwracamy utworzony obiekt, aby frontent mogł go od razu wyświetlić

@api_bp.route("/ips/<int:ip_id>", methods=["PUT"])
@login_required
def update_ip(ip_id):
    ip_entry = IPRegistry.query.get_or_404(ip_id)
    data = request.get_json()

    if 'status' in data: #aktualizujemy stan jeśli został przyjęty w żądaniu
        ip_entry.status = data['status']

    db.session.commit()
    return jsonify(ip_entry.to_dict()), 200

@api_bp.route("/ips/<int:ip_id>", methods=["DELETE"])
@login_required
def delete_ip(ip_id):
    ip_entry = IPRegistry.query.get_or_404(ip_id)

    db.session.delete(ip_entry)
    db.session.commit()
    return jsonify({"message": "Usunięto IP z rejestru"}), 200

@api_bp.route("/alerts", methods=["GET"])
@login_required
def get_recent_alerts(): #główny endpoint dashboardu, pobieranie najnowszych alertów
    alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(20).all() #20 najświeższych alertów, sortując od najmłodszego

    result = []
    for a in alerts:
        alert_data = a.to_dict() #zamieniamy alert na słownik
        
        host = Host.query.get(a.host_id) #pobieramy obiekt hosta którego dotyczy alert, używając powiązania host_id
        alert_data['hostname'] = host.hostname if host else "Nieznany host"
        #nowa kolumna 'hostname' dodana do JSONa - zobaczymy konkretną nazwę hosta a nie tylko jego ID

        result.append(alert_data)

    return jsonify(result)