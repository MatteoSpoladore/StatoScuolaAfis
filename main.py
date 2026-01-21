import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from math import ceil
import os, json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()  # carica tutte le variabili da .env


# CREDS_PATH = os.getenv("CREDS_PATH")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
SHEET_NAME = os.getenv("SHEET_NAME")
ROWS = (1, 13)  # zero-based: start inclusive, end exclusive (es. righe 2-13)
COLS = (7, 10)  # zero-based: colonne H-J (start inclusive, end exclusive)
COL_NAMES = ["Durata", "Corso", "Iscritti"]
# ----------------------------
# CONNESSIONE A FOGLI GOOGLE
# ----------------------------

# Connessione e lettura
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


# Provo a leggere il JSON dai secrets/cloud
creds_json = os.getenv("GOOGLE_CREDS_JSON")

if creds_json:
    # Se esiste, siamo in cloud
    creds_dict = json.loads(creds_json)
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    # Se non esiste, siamo in locale: carico dal file fisico
    CREDS_PATH = "credenziali.json"
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, scope)
# creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, scope)
# creds_dict = json.loads(creds_json)
# creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)
values = sheet.get_all_values()
df = pd.DataFrame(values)

# Estraggo la porzione indicata
chunk = df.iloc[ROWS[0] : ROWS[1], COLS[0] : COLS[1]].copy()
chunk.columns = COL_NAMES[: chunk.shape[1]]


def safe_int(x):
    try:
        if x is None:
            return None
        s = str(x).strip()
        if s == "":
            return None
        return int(float(s))
    except:
        return None


# Costruisco default_enrollments con chiavi tuple
default_enrollments = {}
for _, r in chunk.iterrows():
    d = safe_int(r.get("Durata"))
    c = (r.get("Corso") or "").strip()
    n = safe_int(r.get("Iscritti"))
    if d is not None and c != "" and n is not None:
        default_enrollments[(d, c)] = n


#################################SPECIALS#############################################
# ----------------------------
# COORDINATE per specials dal .env o fisse
# ----------------------------
SPECIAL_ROWS = (0, 5)  # righe 1-5 nel foglio → 0-based
SPECIAL_COLS = (11, 15)  # colonne L-O → 0-based

# Nomi colonne
SPECIAL_COL_NAMES = ["Corso", "Studenti", "Durata", "Prezzo"]

# Estraggo la porzione
special_chunk = df.iloc[
    SPECIAL_ROWS[0] : SPECIAL_ROWS[1], SPECIAL_COLS[0] : SPECIAL_COLS[1]
].copy()
special_chunk.columns = SPECIAL_COL_NAMES[: special_chunk.shape[1]]


# Funzione safe int già definita
def safe_float(x):
    try:
        s = str(x).strip()
        if s == "":
            return None
        return float(s)
    except:
        return None


# Costruisco defaults_specials
defaults_specials = {}
for _, r in special_chunk.iterrows():
    corso = (r.get("Corso") or "").strip()
    students = safe_int(r.get("Studenti"))
    duration = safe_int(r.get("Durata")) or 60  # default se vuoi
    price = safe_float(r.get("Prezzo")) or 100  # default se vuoi

    if corso != "" and students is not None:
        defaults_specials[corso] = {
            "students": students,
            "duration": duration,
            "price": price,
        }


# ----------------------------
# FINE CONNESSIONE
# ----------------------------

# st.code("default_enrollments = " + repr(defaults_specials), language="python")
# ----------------------------
# CONFIGURAZIONE PAGINA / COSTANTI
# ----------------------------
st.set_page_config(page_title="🎼 Piano Corsi", layout="wide")
st.title("🎵 Stato scuola di musica")
st.markdown(
    """
### 🧾 App per visualizzare la macro situazione del bilancio della scuola di musica  

Logica: inserire o modificare i valori degli iscritti per visualizzare un macro riassunto dei costi e ricavi della scuola e della saturazione delle ore disponibili.  

**Calcolo classi di solfeggio (durata 60 minuti):**  
La stima dei costi di solfeggio è calcolata raggruppando gli allievi con lo stesso minutaggio di strumento (classi di solfeggio per 30, 45 e 60 minuti).  
Si ipotizza che in una classe sia possibile inserire solo allievi con lo stesso minutaggio di strumento.  
Gli allievi che fanno *solo solfeggio* da 60 minuti vengono raggruppati con quelli che fanno 60 minuti di strumento.
"""
)

# --- CORSI PRINCIPALI ---
courses = [
    ("solo_fiato", "Solo strumento a fiato"),
    ("fiato_solf", "Strumento a fiato + solfeggio"),
    ("solo_arco", "Solo strumento ad arco"),
    ("arco_solf", "Strumento ad arco + solfeggio"),
]

PRICE_TABLE = {
    (30, "solo_fiato"): 90.0,
    (30, "fiato_solf"): 120.0,
    (30, "solo_arco"): 110.0,
    (30, "arco_solf"): 160.0,
    (45, "solo_fiato"): 135.0,
    (45, "fiato_solf"): 160.0,
    (45, "solo_arco"): 165.0,
    (45, "arco_solf"): 220.0,
    (60, "solo_fiato"): 180.0,
    (60, "fiato_solf"): 190.0,
    (60, "solo_arco"): 220.0,
    (60, "arco_solf"): 240.0,
}
DEFAULT_PRICES_BY_MIN = {30: 120.0, 45: 180.0, 60: 240.0}
LESSONS_PER_PACKAGE = 10

# default_enrollments = {
#     (30, "solo_fiato"): 1,
#     (30, "fiato_solf"): 12,
#     (30, "solo_arco"): 0,
#     (30, "arco_solf"): 13,
#     (45, "solo_fiato"): 9,
#     (45, "fiato_solf"): 16,
#     (45, "solo_arco"): 11,
#     (45, "arco_solf"): 11,
#     (60, "solo_fiato"): 8,
#     (60, "fiato_solf"): 4,
#     (60, "solo_arco"): 10,
#     (60, "arco_solf"): 2,
# }
# default_enrollments = {
#     (30, "solo_fiato"): 1,
#     (30, "fiato_solf"): 12,
#     (30, "solo_arco"): 0,
#     (30, "arco_solf"): 13,
#     (45, "solo_fiato"): 9,
#     (45, "fiato_solf"): 16,
#     (45, "solo_arco"): 11,
#     (45, "arco_solf"): 11,
#     (60, "solo_fiato"): 8,
#     (60, "fiato_solf"): 4,
#     (60, "solo_arco"): 10,
#     (60, "arco_solf"): 2,
# }

# defaults_specials = {
#     "prop": {"students": 0, "duration": 60, "price": 100},
#     "svil": {"students": 5, "duration": 45, "price": 80},
#     "fasce": {"students": 0, "duration": 30, "price": 80},
#     "solo_solfeggio": {"students": 12, "duration": 60, "price": 100},
# }

# defaults_specials = {
#     "prop": {"students": 0, "duration": 60, "price": 100},
#     "svil": {"students": 5, "duration": 45, "price": 80},
#     "fasce": {"students": 0, "duration": 30, "price": 80},
#     "solo_solfeggio": {"students": 12, "duration": 60, "price": 100},
# }


# ----------------------------
# FUNZIONI UTILI
# ----------------------------


def reset_session_keys(keys, defaults=None, rerun=True):
    """
    Resetta una lista di chiavi della sessione a 0 o al valore di default.
    keys: lista di chiavi session_state da resettare
    defaults: dizionario opzionale {key: default_value}
    rerun: se True, chiama st.experimental_rerun per aggiornare la UI
    """
    for k in keys:
        if defaults and k in defaults:
            st.session_state[k] = defaults[k]
        else:
            st.session_state[k] = 0

    if rerun:
        rerun_fn = getattr(st, "experimental_rerun", None)
        if callable(rerun_fn):
            try:
                rerun_fn()
            except Exception:
                pass


# ----------------------------
# RENDER: SIDEBAR e INPUT
# ----------------------------
def render_sidebar_settings():
    st.sidebar.header("⚙️ Impostazioni generali")
    st.sidebar.write(
        "Queste informazioni sono considerate costanti: la loro modifica cambia il bilancio."
    )
    min_students = st.sidebar.number_input(
        "👥 Numero minimo allievi per classe di solfeggio", 1, 15, 6
    )
    hourly_teacher_cost = st.sidebar.number_input(
        "💶 Costo docente per ora (€)", 0.0, 100.0, 24.0, step=0.5
    )
    total_available_hours = st.sidebar.number_input(
        "⏱️ Totale ore disponibili a settimana", 1, 500, 150, step=1
    )
    contributi = st.sidebar.number_input(
        "💰 Contributi accantonati (€)", 0, 20000, 0, step=500
    )
    costi_fissi = st.sidebar.number_input(
        "🏢 Altri costi fissi (€)", 0, 10000, 0, step=100
    )
    return (
        min_students,
        hourly_teacher_cost,
        total_available_hours,
        contributi,
        costi_fissi,
    )


def render_input_iscritti(defaults):
    with st.expander("📝 1) Inserisci iscritti per corso e durata", expanded=False):
        st.subheader("🧑‍🎓 Inserisci iscritti per corso e durata")
        enrollment_keys = {}
        for duration in [30, 45, 60]:
            st.markdown(f"**⏱ Durata {duration} min**")
            cols = st.columns(4)
            for i, (key, label) in enumerate(courses):
                session_key = f"iscr_{key}_{duration}"
                _val = cols[i].number_input(
                    f"{label}",
                    min_value=0,
                    value=defaults.get((duration, key), 0),
                    key=session_key,
                )
                enrollment_keys[(duration, key)] = session_key

        enrollment_keys_list = [v for v in enrollment_keys.values()]
        st.button(
            "🔄 Azzera iscritti principali",
            on_click=reset_session_keys,
            kwargs={"keys": enrollment_keys_list},
        )
        return enrollment_keys


def render_input_specials(defaults):
    with st.expander("🎯 2) Inserisci corsi di gruppo", expanded=False):
        st.subheader("👥 Inserisci altri corsi / attività")
        specials_data = {}
        cols = st.columns(4)
        # lista delle chiavi reali usate nei number_input
        special_input_keys = []
        for i, key in enumerate(["prop", "svil", "fasce", "solo_solfeggio"]):
            session_key = f"special_{key}_students"
            s = cols[i].number_input(
                f"{key} - numero iscritti",
                0,
                200,
                defaults[key]["students"],
                key=session_key,
            )
            special_input_keys.append(session_key)
            specials_data[key] = {
                "students": s,
                "duration": defaults[key]["duration"],
                "price": defaults[key]["price"],
            }

        # Pulsante che azzera *le stesse* chiavi dei number_input.
        # Se vuoi ripristinare ai default, passa defaults_map={"special_prop_students": defaults["prop"]["students"], ...}
        def _reset_specials_to_zero():
            reset_session_keys(special_input_keys, defaults=None, rerun=True)

        st.button(
            "🔄 Azzera specials",
            on_click=_reset_specials_to_zero,
        )

        return specials_data


def render_prices(defaults):
    with st.expander("🏷️ 3) Inserisci prezzi per singolo corso", expanded=False):
        st.subheader("💵 Prezzi per singolo corso (€/10 lezioni)")
        price_overrides = {}
        for duration in [30, 45, 60]:
            st.markdown(f"**⏱ Durata {duration} min**")
            cols = st.columns(4)
            for i, (key, label) in enumerate(courses):
                default_price = defaults.get(
                    (duration, key), DEFAULT_PRICES_BY_MIN[duration]
                )
                price_key = f"price_{key}_{duration}"
                price_overrides[(duration, key)] = cols[i].number_input(
                    label, 0.0, 500.0, float(default_price), key=price_key
                )
    return price_overrides


# ----------------------------
# READ / CALC
# ----------------------------
def read_enrollments(enrollment_keys, specials_data):
    enrolls = {
        (duration, key): int(st.session_state.get(session_key, 0))
        for (duration, key), session_key in enrollment_keys.items()
    }
    specials = {k: v["students"] for k, v in specials_data.items()}
    return enrolls, specials


def compute_totals(
    enrolls,
    specials,
    specials_data,
    price_overrides,
    min_students,
    hourly_teacher_cost,
    contributi,
    costi_fissi,
    num_lessons=LESSONS_PER_PACKAGE,
):
    """
    Restituisce i totali per un pacchetto di num_lessons:
    - ricavi, ore (pacchetto e settimanali), costi (docente + solfeggio), deviazione
    - solfeggio raggruppato per durata (30/45/60)
    """
    total_revenue = 0.0
    detail_rows = []

    # RICAVI corsi principali
    for (duration, key), n_students in enrolls.items():
        price = price_overrides.get((duration, key), DEFAULT_PRICES_BY_MIN[duration])
        revenue = n_students * price * (num_lessons / LESSONS_PER_PACKAGE)
        total_revenue += revenue
        detail_rows.append(
            {
                "course_label": key,
                "duration_min": duration,
                "n_students": n_students,
                "price_per_10_lezioni": price,
                "revenue_for_package": revenue,
            }
        )

    # RICAVI speciali (uso specials_data per price/duration)
    for k, n_students in specials.items():
        if n_students <= 0:
            continue
        meta = specials_data.get(k, {})
        price = meta.get("price", defaults_specials.get(k, {}).get("price", 0.0))
        duration = meta.get(
            "duration", defaults_specials.get(k, {}).get("duration", 60)
        )
        revenue = n_students * price * (num_lessons / LESSONS_PER_PACKAGE)
        total_revenue += revenue
        detail_rows.append(
            {
                "course_label": k,
                "duration_min": duration,
                "n_students": n_students,
                "price_per_10_lezioni": price,
                "revenue_for_package": revenue,
            }
        )

    # aggiungo contributi (se presenti) ai ricavi netti
    # total_revenue += float(contributi or 0.0)

    # Ore per pacchetto (moltiplicate per num_lessons)
    individual_hours = sum(
        int(n) * (duration / 60.0) * num_lessons
        for (duration, key), n in enrolls.items()
        if key in ("solo_fiato", "solo_arco", "fiato_solf", "arco_solf")
    )

    # Solfeggio: sommo studenti per durata (fiato_solf + arco_solf),
    # aggiungo i solo_solfeggio al gruppo 60 e poi calcolo classi (ceil once)
    solfeggio_class_count_by_duration = {}
    for d in (30, 45, 60):
        students = int(enrolls.get((d, "fiato_solf"), 0)) + int(
            enrolls.get((d, "arco_solf"), 0)
        )
        if d == 60:
            students += int(specials.get("solo_solfeggio", 0))
        class_count = ceil(students / min_students) if students > 0 else 0
        solfeggio_class_count_by_duration[d] = class_count

    # ogni classe di solfeggio dura 1 ora, moltiplichiamo per num_lessons
    solfeggio_class_hours = sum(
        count * 1.0 * num_lessons
        for count in solfeggio_class_count_by_duration.values()
    )

    # Altri corsi in classe: prop, svil, fasce (durata presa da specials_data)
    other_class_hours = 0.0
    for k in ("prop", "svil", "fasce"):
        n_students = int(specials.get(k, 0))
        if n_students > 0:
            duration = specials_data.get(k, {}).get(
                "duration", defaults_specials.get(k, {}).get("duration", 60)
            )
            other_class_hours += (
                ceil(n_students / min_students) * (duration / 60.0) * num_lessons
            )

    total_hours = individual_hours + solfeggio_class_hours + other_class_hours
    total_week_hours = (
        total_hours / LESSONS_PER_PACKAGE if LESSONS_PER_PACKAGE else total_hours
    )

    # COSTI
    individual_costs = hourly_teacher_cost * individual_hours
    special_costs = hourly_teacher_cost * other_class_hours
    teacher_cost = hourly_teacher_cost * (individual_hours + other_class_hours)
    solf_cost = hourly_teacher_cost * solfeggio_class_hours
    total_costs = teacher_cost + solf_cost# + other_fixed_costs
    deviation = total_revenue - total_costs

    saturation = (
        (total_week_hours / total_available_hours) * 100
        if total_available_hours > 0
        else 0.0
    )

    return {
        "total_revenue": total_revenue,
        "total_hours": total_hours,
        "total_week_hours": total_week_hours,
        "saturation": saturation,
        "individual_costs": individual_costs,
        "special_costs": special_costs,
        "solfeggio_cost": solf_cost,
        "total_costs": total_costs,
        "deviation": deviation,
        "detail_rows": detail_rows,
        "solfeggio_class_count_by_duration": solfeggio_class_count_by_duration,
    }


# ----------------------------
# RENDER: DASHBOARD e TABELLE
# ----------------------------
def render_dashboard(totals):
    st.subheader("💡 Riepilogo rapido (un trimestre)")
    cols = st.columns(5)
    cols[0].metric("💰 Ricavi totali", f"€ {totals['total_revenue']:,.0f}")
    cols[1].metric("🧾 Totale costi", f"€ {totals['total_costs']:,.0f}")
    cols[2].metric(
        "📉 Ricavi - Costi", f"€ {totals['total_revenue'] - totals['total_costs']:,.0f}"
    )
    cols[3].metric("⏱️ Ore totali (settimanali)", f"{totals['total_week_hours']:.2f} h")
    cols[4].metric("📊 Saturazione", f"{totals['saturation']:.2f} %")


def render_dashboard_anno(totals, contributi , costi_fissi):
    st.subheader("💡 Riepilogo rapido (anno scolastico senza variazioni)")

    ricavi_annui = 3 * totals["total_revenue"]
    costi_annui = 3 * totals["total_costs"]

    utile_annuo = ricavi_annui - costi_annui + contributi - costi_fissi
    utile_nocontr = ricavi_annui - costi_annui

    cols = st.columns(5)
    cols[0].metric("💰 Ricavi totali", f"€ {ricavi_annui:,.0f}")
    cols[1].metric("🧾 Totale costi", f"€ {costi_annui:,.0f}")
    cols[2].metric("📉 Ricavi - costi", f"€ {utile_nocontr:,.0f}")
    cols[3].metric("📉 Risultato netto \n (+- contributi e costi fissi)", f"€ {utile_annuo:,.0f}")
    cols[4].metric("💸 Contributi utilizzati", f"€ {contributi:,.0f}")
    cols = st.columns(5)
    cols[2].metric("📉 Risultato netto \n (+- contributi e costi fissi)", f"€ {utile_annuo:,.0f}")
    cols[3].metric("💸 Contributi utilizzati", f"€ {contributi:,.0f}")
    cols[4].metric("🧾 Costi fissi", f"€ {costi_fissi:,.0f}")
def render_detail_table(totals):
    st.subheader("📊 Tabella ricavi e costi per corsi individuali")
    with st.expander("🔎 dettagli ricavi, costi e saldo per corso", expanded=False):
        df = pd.DataFrame(totals["detail_rows"])

        if df.empty:
            st.write("Nessun corso con iscritti.")
            return

        # ------------------------------------------------
        # 0) Filtra/Nascondi i corsi che non vuoi mostrare
        # accetta sia le chiavi brevi (prop, svil, fasce, solo_solfeggio)
        # sia le label estese che potresti avere nei detail_rows
        # ------------------------------------------------
        exclude_keys = {"prop", "svil", "fasce", "solo_solfeggio"}
        exclude_labels = {
            "Propedeutica",
            "Propedeutica musicale",
            "Sviluppo musicalità",
            "Musica in fasce",
            "Solo Solfeggio",
            "Solo solfeggio",
        }

        # alcune versioni dei detail_rows potrebbero usare 'course_label' come chiave breve,
        # altre la label estesa; gestiamo entrambe
        def row_is_excluded(row):
            lab = str(row.get("course_label", "")).strip()
            # confronto diretto con chiavi brevi
            if lab in exclude_keys:
                return True
            # confronto con label estese (casefold per robustezza)
            if lab.casefold() in {x.casefold() for x in exclude_labels}:
                return True
            # alcune volte la chiave originale è in un campo diverso (es. 'course' o 'course_key')
            if "course" in row and str(row.get("course", "")).strip() in exclude_keys:
                return True
            if (
                "course_key" in row
                and str(row.get("course_key", "")).strip() in exclude_keys
            ):
                return True
            return False

        # Applichiamo il filtro
        df = df[~df.apply(row_is_excluded, axis=1)].reset_index(drop=True)

        if df.empty:
            st.write(
                "Dopo aver nascosto i corsi selezionati non ci sono righe da mostrare."
            )
            return

        # -----------------------------
        # Mappatura nomi più leggibili
        # -----------------------------
        rename_map = {
            "solo_fiato": "Fiati",
            "fiato_solf": "Fiati + Solfeggio",
            "solo_arco": "Archi",
            "arco_solf": "Archi + Solfeggio",
            "prop": "Propedeutica",
            "svil": "Sviluppo musicalità",
            "fasce": "Musica in fasce",
            "solo_solfeggio": "Solo Solfeggio",
        }

        # normalizza nomi/colonne se necessario
        if "course_label" not in df.columns and "course" in df.columns:
            df = df.rename(columns={"course": "course_label"})
        if "duration_min" not in df.columns and "duration" in df.columns:
            df = df.rename(columns={"duration": "duration_min"})
        if "n_students" not in df.columns and "iscritti" in df.columns:
            df = df.rename(columns={"iscritti": "n_students"})
        if "price_per_10_lezioni" not in df.columns and "price" in df.columns:
            df = df.rename(columns={"price": "price_per_10_lezioni"})
        if "revenue_for_package" not in df.columns and "ricavo" in df.columns:
            df = df.rename(columns={"ricavo": "revenue_for_package"})

        # applica la mappatura leggibile sulla label e aggiungi i minuti tra parentesi
        def pretty_label(row):
            base = row.get("course_label", "")
            pretty = rename_map.get(base, base)
            minutes = row.get("duration_min", None)
            if minutes is not None and str(minutes).strip() != "":
                try:
                    return f"{pretty} ({int(minutes)}')"
                except Exception:
                    return f"{pretty} ({minutes})"
            return pretty

        df["course_label"] = df.apply(pretty_label, axis=1)

        # -----------------------------
        # Calcolo costi per package
        # formula richiesta: numero_iscritti * 24 * (10/(60/30))
        # ora implementata usando hourly_teacher_cost (fallback 24) e LESSONS_PER_PACKAGE
        # -----------------------------
        hourly = globals().get("hourly_teacher_cost", 24.0)
        try:
            hourly = float(hourly)
        except Exception:
            hourly = 24.0

        denom = 60.0 / 30.0  # = 2.0
        lessons_pkg = globals().get("LESSONS_PER_PACKAGE", 10)
        try:
            lessons_pkg = float(lessons_pkg)
        except Exception:
            lessons_pkg = 10.0
        multiplier = lessons_pkg / denom  # es. 10 / 2 = 5

        # assicurati colonne esistenti e tipi
        if "revenue_for_package" not in df.columns:
            df["revenue_for_package"] = 0.0
        df["n_students"] = df.get("n_students", 0).fillna(0).astype(int)

        df["cost_per_package"] = df["n_students"] * hourly * multiplier
        df["saldo"] = df["revenue_for_package"].astype(float) - df[
            "cost_per_package"
        ].astype(float)

        # -----------------------------
        # Formattazione colonna e rinomina colonne per display
        # -----------------------------
        df_display = df.copy()
        for col in [
            "revenue_for_package",
            "price_per_10_lezioni",
            "cost_per_package",
            "saldo",
        ]:
            if col in df_display.columns:
                df_display[col] = df_display[col].map(lambda x: f"€ {x:,.2f}")

        # colonne da mostrare (ordinamento suggerito)
        display_cols = [
            "course_label",
            "duration_min",
            "n_students",
            "price_per_10_lezioni",
            "revenue_for_package",
            "cost_per_package",
            "saldo",
        ]
        display_cols = [c for c in display_cols if c in df_display.columns]

        pretty_headers = {
            "course_label": "Corso",
            "duration_min": "Minuti",
            "n_students": "Iscritti",
            "price_per_10_lezioni": "Prezzo (€/pacchetto)",
            "revenue_for_package": "Ricavo (€/pacchetto)",
            "cost_per_package": "Costo (€/pacchetto)",
            "saldo": "Saldo (€/pacchetto)",
        }
        df_display = df_display[display_cols].rename(columns=pretty_headers)

        st.dataframe(df_display)


# ----------------------------
# LOGICA STREAMLIT (esecuzione)
# ----------------------------
(
    min_students,
    hourly_teacher_cost,
    total_available_hours,
    contributi,
    costi_fissi,
) = render_sidebar_settings()
enrollment_keys = render_input_iscritti(default_enrollments)
specials_data = render_input_specials(defaults_specials)
price_overrides = render_prices(PRICE_TABLE)

enrolls, specials = read_enrollments(enrollment_keys, specials_data)

# calcoli per pacchetto 10 lezioni (tot_10)
tot_10 = compute_totals(
    enrolls=enrolls,
    specials=specials,
    specials_data=specials_data,
    price_overrides=price_overrides,
    min_students=min_students,
    hourly_teacher_cost=hourly_teacher_cost,
    contributi=contributi,
    costi_fissi=costi_fissi,
    num_lessons=LESSONS_PER_PACKAGE,
)

# ----------------------------
# GRAFICI: barre + semicerchio (pie rimodulato)
# ----------------------------
col_left, col_right = st.columns(2)
totals = tot_10

used_week_hours = totals.get("total_week_hours", 0.0)
available_hours = (
    float(total_available_hours) if "total_available_hours" in globals() else 1.0
)
used = min(used_week_hours, available_hours)
remaining = max(available_hours - used, 0.0)

# Semicerchio ottenuto con pie: colori nella metà superiore (rosso = usate, blu = rimanenti)
# costruiamo values in modo che la fetta trasparente occupi la metà inferiore
# per l'effetto semicerchio disponiamo i valori in ordine e ruotiamo di 180°
fig_semi = go.Figure(
    go.Pie(
        values=[remaining, used],
        hole=0.6,
        sort=False,
        direction="clockwise",
        marker=dict(
            colors=[
                "rgba(0,0,0,0)",  # filler (meta' inferiore invisibile)
                "#EF553B",  # rosso: ore usate
                # "#636EFA",  # blu: ore rimanenti
            ],
            line=dict(color="white", width=1),
        ),
        textinfo="none",
        hoverinfo="value",
        rotation=0,
    )
)

pct = (used / available_hours * 100) if available_hours > 0 else 0.0
fig_semi.update_layout(
    title="🕒 Utilizzo ore sede",
    title_x=0.35,
    showlegend=False,
    margin=dict(t=30, b=0, l=0, r=0),
    height=300,
    annotations=[
        dict(
            text=f"<b>{used:.1f} / {available_hours:.1f} h</b><br><span style='font-size:12px'>usate / disponibili</span>",
            x=0.5,
            y=0.52,
            showarrow=False,
        ),
        dict(
            text=f"{pct:.1f}%",
            x=0.5,
            y=0.36,
            showarrow=False,
            font=dict(size=16),
        ),
    ],
)

with col_right:
    st.plotly_chart(fig_semi, width="stretch")

# Grafico a barre: Ricavi vs Costi
ricavi = totals.get("total_revenue", 0.0)
costi = totals.get("total_costs", 0.0)
df_bar = pd.DataFrame(
    {"Categoria": ["Ricavi totali", "Costi totali"], "Valore": [ricavi, costi]}
)
fig_bar = px.bar(df_bar, x="Categoria", y="Valore", text="Valore", height=360)
fig_bar.update_traces(
    texttemplate="€ %{y:,.2f}",
    textposition="outside",
    marker_color=["#00CC96", "#636EFA"],
)
fig_bar.update_layout(
    title="💹 Confronto Ricavi e Costi",
    title_x=0.35,
    margin=dict(t=30, b=30, l=20, r=20),
    yaxis_title="€",
    xaxis_title="",
    showlegend=False,
)
max_val = max(ricavi, costi)
fig_bar.update_yaxes(tickformat=",", range=[0, max_val + 5000])
with col_left:
    st.plotly_chart(
        fig_bar, config={"staticPlot": True, "displayModeBar": True}, width="stretch"
    )


render_dashboard(tot_10)
render_dashboard_anno(tot_10, contributi,costi_fissi)

# -----------------------------
# RIEPILOGO CLASSI e DETTAGLIO
# -----------------------------
st.markdown("### 📚 Riepilogo Classi Formate")
with st.expander("🔢 riepilogo classi formate", expanded=False):
    # calcoli locali per classi di solfeggio raggrupate per minutaggio strumento
    solfeggio_class_count_by_duration = {}
    solfeggio_students_by_duration = {}
    for d in (30, 45, 60):
        students = int(enrolls.get((d, "fiato_solf"), 0)) + int(
            enrolls.get((d, "arco_solf"), 0)
        )
        if d == 60:
            students += int(
                specials_data.get("solo_solfeggio", {}).get(
                    "students", defaults_specials["solo_solfeggio"]["students"]
                )
            )
        solfeggio_students_by_duration[d] = students
        solfeggio_class_count_by_duration[d] = (
            ceil(students / min_students) if students > 0 else 0
        )

    prop_classes = (
        ceil(
            specials_data.get("prop", {}).get(
                "students", defaults_specials["prop"]["students"]
            )
            / min_students
        )
        if specials_data.get("prop", {}).get("students", 0) > 0
        else 0
    )
    fasce_classes = (
        ceil(
            specials_data.get("fasce", {}).get(
                "students", defaults_specials["fasce"]["students"]
            )
            / min_students
        )
        if specials_data.get("fasce", {}).get("students", 0) > 0
        else 0
    )

    classi_df = pd.DataFrame(
        {
            "Tipologia Classe": [
                "Solfeggio 30 min",
                "Solfeggio 45 min",
                "Solfeggio 60 min",
                "Propedeutica",
                "Musica in fasce",
            ],
            "Numero classi": [
                solfeggio_class_count_by_duration.get(30, 0),
                solfeggio_class_count_by_duration.get(45, 0),
                solfeggio_class_count_by_duration.get(60, 0),
                prop_classes,
                fasce_classes,
            ],
        }
    )
    st.markdown(
        classi_df.to_html(index=False, justify="center"), unsafe_allow_html=True
    )


# -----------------------------
# Dettaglio costi e ore (espandibile)
# -----------------------------
st.markdown("### 📊 Riepilogo Costi, Ricavi e Ore")
with st.expander("📈 Riepilogo costi, ricavi e ore (dettaglio)", expanded=False):
    col1, col2 = st.columns(2)
    # calcoli settimanali (senza moltiplicare per num_lessons)
    weekly_individual_hours = sum(
        int(n) * (duration / 60.0)
        for (duration, key), n in enrolls.items()
        if key in ("solo_fiato", "solo_arco", "fiato_solf", "arco_solf")
    )
    weekly_solfeggio_hours = sum(
        count * 1.0 for count in solfeggio_class_count_by_duration.values()
    )
    weekly_other_class_hours = 0.0
    for key in ("prop", "svil", "fasce"):
        students = int(
            specials_data.get(key, {}).get(
                "students", defaults_specials[key]["students"]
            )
        )
        duration = defaults_specials[key]["duration"]
        if students > 0:
            weekly_other_class_hours += ceil(students / min_students) * (
                duration / 60.0
            )

    weekly_total_hours = (
        weekly_individual_hours + weekly_solfeggio_hours + weekly_other_class_hours
    )
    saturation_pct = (
        (weekly_total_hours / total_available_hours) * 100
        if total_available_hours > 0
        else 0.0
    )

    with col1:
        st.write("**🔎 Dettaglio per pacchetto (10 lezioni)**:")
        st.write(f"🕒 Ore totali per pacchetto: {tot_10['total_hours']:.2f} h")
        st.write(
            f"👨‍🏫 Costo docente (lezioni individuali totali): € {tot_10['individual_costs']:,.2f}"
        )
        st.write(
            f"🎼 Costo solfeggio (classi) per pacchetto: € {tot_10['solfeggio_cost']:,.2f}"
        )
        st.write(
            f"🎼 Costo altri corsi (classi di Prop,SviMus,MusInFas): € {tot_10['special_costs']:,.2f}"
        )
        st.write(f"🏷️ Totale costi per pacchetto: € {tot_10['total_costs']:,.2f}")
        st.write(
            f"💵 Ricavi totali (1 pacchetto = {LESSONS_PER_PACKAGE} lezioni): € {tot_10['total_revenue']:,.2f}"
        )
        st.write(
            f"📉 Scostamento per pacchetto (ricavi - costi): € {tot_10['deviation']:,.2f}"
        )

    with col2:
        st.write(
            "**⏱️ Ore settimanali (effettive)** — max 1 lezione strumento/settimana e max 1 solfeggio a settimana"
        )
        st.write(
            f"🎻 Ore individuali (strumento) per settimana: {weekly_individual_hours:.2f} h"
        )
        st.write(
            f"📚 Ore solfeggio in classe per settimana: {weekly_solfeggio_hours:.2f} h"
        )
        st.write(
            f"🧸 Ore altri corsi in classe per settimana: {weekly_other_class_hours:.2f} h"
        )
        st.write(f"🔢 Ore totali richieste a settimana: {weekly_total_hours:.2f} h")
        st.write(f"📅 Ore disponibili a settimana: {total_available_hours:.2f} h")
        st.write(f"📈 Percentuale di saturazione settimanale: {saturation_pct:.2f} %")

render_detail_table(tot_10)
