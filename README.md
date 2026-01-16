# System Analizy Logów i Informatyki Śledczej (SIEM)

Projekt z przedmiotu Języki Skryptowe. Aplikacja webowa służąca do zbierania, analizy i wizualizacji logów systemowych, z naciskiem na aspekty informatyki śledczej (Forensics) i bezpieczeństwa (Security).

## 📋 Główne Funkcjonalności

### 1. Zbieranie Logów (Log Collection)
*   Agregacja logów ze zdalnych serwerów Linux poprzez **SSH** (przy użyciu biblioteki `paramiko`).
*   Pobieranie logów z lokalnego systemu **Windows** (Event Log).
*   Scentralizowane zarządzanie hostami.

### 2. Informatyka Śledcza (Forensics)
*   **Trwały zapis dowodów**: Wszystkie zebrane logi są zapisywane do plików w formacie **Parquet** (`pyarrow`) w katalogu `storage/`. Zapewnia to wydajność i integralność danych do dalszej analizy.
*   Dane nie są analizowane wyłącznie w pamięci RAM, co spełnia wymogi dotyczące zachowania materiału dowodowego.

### 3. Analiza Zagrożeń (Threat Intelligence)
*   **Log Analyzer**: Moduł analizujący logi pod kątem podejrzanych aktywności.
*   **Threat Intel**: Korelacja adresów IP z logów z bazami zagrożeń (wykrywanie potencjalnych ataków).

### 4. Bezpieczeństwo Aplikacji (Security First)
*   **Uwierzytelnianie**: Bezpieczne logowanie użytkowników, haszowanie haseł (zgodnie z `werkzeug.security`).
*   **Ochrona API**: Zabezpieczenie endpointów.
*   **Architektura**: 'Defense in Depth'.

## 🛠️ Technologie

Projekt został zrealizowany w języku **Python** z wykorzystaniem frameworka **Flask**.

*   **Backend**: Flask, Flask-Login, Flask-Migrate
*   **Baza Danych**: SQLite (SQLAlchemy ORM)
*   **Przetwarzanie Danych**: pandas, pyarrow (Parquet)
*   **Komunikacja Sieciowa**: paramiko (klient SSH)
*   **Formularze**: Flask-WTF

## 🚀 Instalacja i Uruchomienie

### Wymagania
*   Python 3.8 lub nowszy
*   Rekomendowany system: Windows (dla pełnej funkcjonalności modułu `win_client`) lub Linux (z ograniczeniem do SSH).

### Krok 1: Klonowanie repozytorium
```bash
git clone <url_do_repozytorium>
cd skryptowe-projekt
```

### Krok 2: Przygotowanie środowiska wirtualnego
```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### Krok 3: Instalacja zależności
```bash
pip install -r requirements.txt
```

### Krok 4: Konfiguracja
Aplikacja posiada domyślną konfigurację w `config.py`. Możesz nadpisać ustawienia tworząc plik `.env` w głównym katalogu:

```ini
SECRET_KEY=twoj-super-tajny-klucz
SQLALCHEMY_DATABASE_URI=sqlite:///../instance/lab7.db
# Konfiguracja domyślna SSH (np. dla Vagrant)
SSH_DEFAULT_USER=vagrant
SSH_DEFAULT_PORT=2222
```

### Krok 5: Uruchomienie
```bash
flask run
```
Aplikacja będzie dostępna pod adresem: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 📂 Struktura Katalogów

*   `app/` - Główny kod źródłowy aplikacji
    *   `blueprints/` - Moduły aplikacji (Interfejs, API, Autoryzacja)
    *   `services/` - Logika biznesowa (`LogCollector`, `LogAnalyzer`, `DataManager`)
    *   `models.py` - Modele bazy danych
*   `storage/` - Miejsce zapisu plików Parquet (baza dowodowa)
*   `instance/` - Plik bazy danych SQLite

## 📝 Autor

Mateusz Szelecki.
