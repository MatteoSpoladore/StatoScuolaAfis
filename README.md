(# Analisi Costi — Istruzioni)

Questo repository contiene una semplice app Streamlit per analisi dei costi.

Installazione (uso di "uv add" come richiesto):

```bash
# Aggiungi la dipendenza usando il tuo tool 'uv'
uv add streamlit

# Se vuoi creare/attivare un virtualenv manualmente (opzionale):
# Linux / macOS (bash):
python -m venv .venv
source .venv/bin/activate

# Windows Git Bash (bash.exe) - la cartella è solitamente 'Scripts' con S maiuscola:
source .venv/Scripts/activate

# Comando per eseguire l'app Streamlit
streamlit run main.py
```

Nota: hai scritto `source .venv/scripts/activate`; su Windows la cartella è normalmente `Scripts`. Se stai usando un ambiente POSIX che crea `bin/`, usa il percorso `source .venv/bin/activate`.

File principali:

- `main.py` — app Streamlit minimale
- `pyproject.toml` — dipendenza `streamlit` aggiunta
- `requirements.txt` — file con `streamlit` per installazione alternativa
