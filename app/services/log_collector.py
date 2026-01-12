import re
import json
from datetime import datetime

class LogCollector:
    """
    Pobiera i normalizuje logi z różnych systemów (Linux/Windows).
    """

    # --- KONFIGURACJA LINUX (REGEX) ---
    # Linux w journalctl zwraca treść błędu jako tekst w polu MESSAGE.
    # Musimy użyć Regex, aby wyciągnąć IP i Usera.
    LINUX_PATTERNS = {
        'failed_password': re.compile(r"Failed password for (?:invalid user )?([\w.-]+) from ([\d.]+)"),
        'invalid_user': re.compile(r"Invalid user ([\w.-]+) from ([\d.]+)"),
        'sudo': re.compile(r"sudo:\s+([a-zA-Z0-9._-]+)\s*:"),
    }

    # =========================================================================
    # METODA 1: LINUX (SSH + Journalctl + Regex)
    # =========================================================================
    @staticmethod
    def get_linux_logs(ssh_client, last_fetch_time=None):
        logs = []
        
        # Budowanie komendy: pobierz JSON z journalctl
        cmd = "sudo journalctl -u ssh -o json --no-pager"
        
        if last_fetch_time:
            since_str = last_fetch_time.strftime("%Y-%m-%d %H:%M:%S")
            cmd += f' --since "{since_str}"'
        else:
            cmd += ' --since "7 days ago"' # Domyślny zasięg na start

        print(f"DEBUG [Linux]: Executing {cmd}")
        
        try:
            stdout, stderr = ssh_client.run(cmd)
            
            if not stdout:
                return []

            for line in stdout.splitlines():
                if not line.strip(): continue
                try:
                    # Parsowanie JSON z journald
                    entry = json.loads(line)
                    message = entry.get('MESSAGE', '')
                    
                    # Konwersja czasu (mikrosekundy -> datetime)
                    ts_micro = int(entry.get('__REALTIME_TIMESTAMP', 0))
                    timestamp = datetime.fromtimestamp(ts_micro / 1_000_000)

                    # Analiza treści (Logika Regex)
                    parsed = LogCollector._parse_linux_message(message, timestamp)
                    if parsed:
                        logs.append(parsed)

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"Error collecting Linux logs: {e}")
            # Nie rzucamy wyjątku, żeby błąd jednego hosta nie zatrzymał procesu dla innych
            return []

        return logs

    @staticmethod
    def _parse_linux_message(message, timestamp):
        # Helper do sprawdzania Regexów
        
        # 1. Failed Password
        match = LogCollector.LINUX_PATTERNS['failed_password'].search(message)
        if match:
            return {
                'timestamp': timestamp,
                'alert_type': 'FAILED_LOGIN',
                'source_ip': match.group(2),
                'user': match.group(1),
                'message': message,
                'raw_log': message
            }
        
        # 2. Invalid User
        match = LogCollector.LINUX_PATTERNS['invalid_user'].search(message)
        if match:
            return {
                'timestamp': timestamp,
                'alert_type': 'INVALID_USER',
                'source_ip': match.group(2),
                'user': match.group(1),
                'message': message,
                'raw_log': message
            }

        # 3. Sudo
        match = LogCollector.LINUX_PATTERNS['sudo'].search(message)
        if match:
             return {
                'timestamp': timestamp,
                'alert_type': 'SUDO_USAGE',
                'source_ip': 'LOCAL',
                'user': match.group(1),
                'message': message,
                'raw_log': message
            }
        return None

    # =========================================================================
    # METODA 2: WINDOWS (PowerShell + XML Parsing)
    # =========================================================================
    @staticmethod
    def get_windows_logs(win_client, last_fetch_time=None):
        logs = []
        
        # Komenda PowerShell wzorowana na skrypcie 'collect_windows_logons_xml.ps1'.
        # 1. Get-WinEvent (ID 4625 = Failed Login)
        # 2. .ToXml() -> pozwala wyciągnąć IpAddress niezależnie od języka OS
        # 3. ConvertTo-Json -> zwraca gotowy obiekt do Pythona
        
        # TODO: Obsługa last_fetch_time w filtrze XML (dla studentów jako wyzwanie?)
        # Na potrzeby demo pobieramy MaxEvents=20 najnowszych, żeby nie zapchać łącza
        
        ps_cmd = (
            "Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625} -MaxEvents 20 -ErrorAction SilentlyContinue | "
            "ForEach-Object { "
            "   $xml = [xml]$_.ToXml(); "
            "   $data = @{}; "
            "   $xml.Event.EventData.Data | ForEach-Object { $data[$_.Name] = $_.'#text' }; "
            "   [PSCustomObject]@{ "
            "       Timestamp = $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'); "
            "       IpAddress = $data['IpAddress']; "
            "       TargetUserName = $data['TargetUserName']; "
            "       EventId = $_.Id "
            "   } "
            "} | ConvertTo-Json -Compress"
        )
        
        print(f"DEBUG [Windows]: Executing PS XML extraction...") 

        try:
            stdout = win_client.run_ps(ps_cmd)
            
            if not stdout:
                return [] # Brak logów lub błąd PS

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                print("WinLog Error: Invalid JSON output from PowerShell")
                return []

            # PowerShell zwraca dict (1 wynik) lub list (wiele wyników). Ujednolicamy.
            entries = [data] if isinstance(data, dict) else data

            for entry in entries:
                # Czyste dane ze struktury XML
                ip = entry.get('IpAddress', '-')
                user = entry.get('TargetUserName', 'UNKNOWN')
                ts_str = entry.get('Timestamp')
                
                # Konwersja daty
                try:
                    timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    timestamp = datetime.now()

                # Normalizacja IP ("-" oznacza logowanie lokalne)
                if not ip or ip == '-':
                    ip = 'LOCAL_CONSOLE'

                # Dodajemy do listy w formacie ujednoliconym z Linuxem
                logs.append({
                    'timestamp': timestamp,
                    'alert_type': 'WIN_FAILED_LOGIN',
                    'source_ip': ip,
                    'user': user,
                    'message': f"Windows Logon Failure for user: {user} (Event 4625)",
                    'raw_log': json.dumps(entry) # Zapisujemy strukturę JSON jako dowód
                })

        except Exception as e:
            print(f"Error collecting Windows logs: {e}")
            return []

        return logs