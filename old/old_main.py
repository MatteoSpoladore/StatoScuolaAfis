import streamlit as st
import pandas as pd
from math import ceil

# from funzioni import compute_totals_from_state, read_enrollments_from_state

# --- CONFIG PAGINA ---
st.set_page_config(page_title="Piano ricavi/costi - Corsi Musicali", layout="wide")
st.title("Piano ricavi / costi - Corsi musicali")
st.markdown(
    "App per calcolare ricavi, costi, ore e saturazione settimanale a partire dagli iscritti per corso e minutaggio. "
    "Logica: **strumento** = lezione individuale; **solfeggio** = lezioni in classe (aggregazione in base a min_students); "
    "gli altri corsi sono in classe. I costi di solfeggio sono calcolati automaticamente come costo orario docente sulle ore delle classi di solfeggio."
)

# --- SIDEBAR: impostazioni generali ---
st.sidebar.header("Impostazioni generali")
min_students = st.sidebar.number_input(
    "Numero minimo allievi per classe (gruppo)",
    min_value=1,
    value=6,
    step=1,
    key="min_students",
)
hourly_teacher_cost = st.sidebar.number_input(
    "Costo docente per ora (€)",
    min_value=0.0,
    value=24.0,
    step=0.5,
    key="hourly_teacher_cost",
)
total_available_hours = st.sidebar.number_input(
    "Totale ore disponibili a settimana",
    min_value=1.0,
    value=150.0,
    step=1.0,
    key="total_available_hours",
)
other_fixed_costs = st.sidebar.number_input(
    "Altri costi fissi (€/pacchetto o fisso) (€)",
    min_value=0.0,
    value=0.0,
    step=10.0,
    key="other_fixed_costs",
)

st.sidebar.caption(
    "I prezzi impostati qui sotto si intendono come prezzo per pacchetto da 10 lezioni. "
    "Il costo delle classi di solfeggio è calcolato automaticamente."
)

# --- Prezzi di riferimento (valori di default per minutaggio e corso) ---
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

# --- definizione dei corsi principali ---
courses = [
    ("solo_fiato", "Solo strumento a fiato"),
    ("fiato_solf", "Strumento a fiato + solfeggio"),
    ("solo_arco", "Solo strumento ad arco"),
    ("arco_solf", "Strumento ad arco + solfeggio"),
]

# --- DEFAULT ISCRITTI (usati come valore iniziale nei number_input) ---
default_enrollments = {
    (30, "solo_fiato"): 1,
    (30, "fiato_solf"): 12,
    (30, "solo_arco"): 0,
    (30, "arco_solf"): 13,
    (45, "solo_fiato"): 9,
    (45, "fiato_solf"): 16,
    (45, "solo_arco"): 11,
    (45, "arco_solf"): 11,
    (60, "solo_fiato"): 8,
    (60, "fiato_solf"): 4,
    (60, "solo_arco"): 10,
    (60, "arco_solf"): 2,
}

# --- Parametro pacchetto (unità base) ---
LESSONS_PER_PACKAGE = 10

# ----------------------------
# SEZIONE 1) INSERISCI ISCRIZIONI (in expander)
# ----------------------------
with st.expander("1) Inserisci iscrizioni per corso e durata", expanded=False):
    st.write("Inserisci il numero di iscritti per ogni corso e durata.")

    # Bottone per azzerare tutte le iscrizioni (versione robusta: non usa experimental_rerun se non presente)
    def reset_iscritti():
        keys_to_reset = [k for k in st.session_state.keys() if k.startswith("iscr_")]
        if not keys_to_reset:
            st.info("Non ci sono campi iscritti da azzerare.")
            return
        for k in keys_to_reset:
            st.session_state[k] = 0
        # provo a chiamare experimental_rerun se disponibile
        rerun_fn = getattr(st, "experimental_rerun", None)
        if callable(rerun_fn):
            try:
                rerun_fn()
                return
            except Exception:
                pass
        st.success(
            "Tutti gli iscritti sono stati azzerati. (Se non vedi i cambiamenti, aggiorna la pagina.)"
        )

    st.button("🔄 Azzera iscritti", on_click=reset_iscritti)

    # grid input: ogni number_input usa una key che inizia con "iscr_"
    def input_grid_with_keys(defaults):
        data_keys = {}
        for duration in [30, 45, 60]:
            st.subheader(f"Durata: {duration} min")
            cols = st.columns(4)
            for i, (key, label) in enumerate(courses):
                session_key = f"iscr_{key}_{duration}"
                default_val = defaults.get((duration, key), 0)
                val = cols[i].number_input(
                    f"{label}",
                    min_value=0,
                    value=int(default_val),
                    key=session_key,
                )
                data_keys[(duration, key)] = session_key
        return data_keys

    # costruisce le mappature tra (duration, key) e nome session state
    enrollment_keys = input_grid_with_keys(default_enrollments)

# ----------------------------
# SEZIONE 2) PREZZI PER CORSO (in expander)
# ----------------------------
with st.expander(
    "2) Inserisci Prezzi per singolo corso (per pacchetto da 10 lezioni)",
    expanded=False,
):
    st.write("Imposta il prezzo per pacchetto (10 lezioni) per ogni corso/durata.")
    price_overrides = {}
    for duration in [30, 45, 60]:
        st.subheader(f"Prezzi per durata {duration} min (€/10 lezioni)")
        cols = st.columns(4)
        for i, (key, label) in enumerate(courses):
            default_price = PRICE_TABLE.get(
                (duration, key), DEFAULT_PRICES_BY_MIN[duration]
            )
            price_key = f"price_{key}_{duration}"
            p = cols[i].number_input(
                f"{label}",
                min_value=0.0,
                value=float(default_price),
                key=price_key,
            )
            price_overrides[(duration, key)] = float(p)

# ----------------------------
# SEZIONE 3) Altri corsi / attività (visibile di default)
# ----------------------------
# ----------------------
# Valori di default
# ----------------------
default_prices = {
    "prop": 100,
    "svil": 80,
    "fasce": 80,
    "solo_solfeggio": 100,
}

default_durations = {
    "prop": 60,
    "svil": 45,
    "fasce": 30,
    "solo_solfeggio": 60,
}

with st.expander(
    "3) Inserisci Altri corsi / attività (iscritti e parametri)", expanded=False
):
    # Bottone che azzera SOLO gli iscritti della sezione 3
    def reset_iscritti_sezione_3():
        keys = ["iscr_prop", "iscr_sviluppo", "iscr_fasce", "iscr_solo_solfeggio"]
        any_reset = False
        for k in keys:
            if k in st.session_state and st.session_state.get(k, 0) != 0:
                st.session_state[k] = 0
                any_reset = True

        rerun_fn = getattr(st, "experimental_rerun", None)
        if callable(rerun_fn):
            try:
                rerun_fn()
                return
            except Exception:
                pass

        if any_reset:
            st.success("Iscritti della sezione 3 azzerati.")
        else:
            st.info("I campi erano già a zero.")

    st.button("🔄 Azzera iscritti - Sezione 3", on_click=reset_iscritti_sezione_3)

    # --- NUMERO ISCRITTI (int) ---
    col1, col2, col3, col4 = st.columns(4)
    prop_num = col1.number_input(
        "Propedeutica - numero iscritti",
        min_value=0,
        value=st.session_state.get("iscr_prop", 0),
        key="iscr_prop",
    )
    sviluppo_num = col2.number_input(
        "Sviluppo musicalità - numero iscritti",
        min_value=0,
        value=5,
        # value=st.session_state.get("iscr_sviluppo", 0),
        key="iscr_sviluppo",
    )
    musica_in_fasce_num = col3.number_input(
        "Musica in fasce - numero iscritti",
        min_value=0,
        value=st.session_state.get("iscr_fasce", 0),
        key="iscr_fasce",
    )
    solo_solfeggio_num = col4.number_input(
        "Solo solfeggio - numero iscritti",
        min_value=0,
        value=12,
        # value=st.session_state.get("iscr_solo_solfeggio", 0),
        key="iscr_solo_solfeggio",
    )

    # --- DURATA (int) ---
    col_a, col_b, col_c, col_d = st.columns(4)
    prop_duration = col_a.selectbox(
        "Propedeutica durata (min)",
        options=[30, 45, 60],
        index=2,
        key="prop_duration",  # default 60
    )
    svil_duration = col_b.selectbox(
        "Sviluppo musicalità durata (min)",
        options=[30, 45, 60],
        index=1,
        key="svil_duration",  # default 45
    )
    fasce_duration = col_c.selectbox(
        "Musica in fasce durata (min)",
        options=[30, 45, 60],
        index=0,
        key="fasce_duration",  # default 30
    )
    solo_solf_duration = col_d.selectbox(
        "Solo solfeggio durata (min)",
        options=[30, 45, 60],
        index=2,
        key="solo_solf_duration",  # default 60
    )

    # --- PREZZI (float) ---
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    svil_price = col_p1.number_input(
        "Prezzo sviluppo musicalità (€/10 lezioni)",
        min_value=0.0,
        value=float(st.session_state.get("svil_price", 80.0)),
        step=1.0,
        key="svil_price",
    )
    solo_solf_price = col_p2.number_input(
        "Prezzo solo solfeggio (€/10 lezioni)",
        min_value=0.0,
        value=float(st.session_state.get("solo_solf_price", 100.0)),
        step=1.0,
        key="solo_solf_price",
    )
    prop_price = col_p3.number_input(
        "Prezzo propedeutica (€/10 lezioni)",
        min_value=0.0,
        value=float(st.session_state.get("prop_price", 100.0)),
        step=1.0,
        key="prop_price",
    )
    fasce_price = col_p4.number_input(
        "Prezzo musica in fasce (€/10 lezioni)",
        min_value=0.0,
        value=float(st.session_state.get("fasce_price", 80.0)),
        step=1.0,
        key="fasce_price",
    )


# ----------------------------
# Utility: costruisce dizionario enrollments leggendo lo stato della sessione
# ----------------------------
def read_enrollments_from_state(enrollment_key_map):
    enrolls = {}
    for (duration, key), session_key in enrollment_key_map.items():
        enrolls[(duration, key)] = int(st.session_state.get(session_key, 0))
    enrolls_special = {
        "prop_num": int(st.session_state.get("iscr_prop", 0)),
        "sviluppo_num": int(st.session_state.get("iscr_sviluppo", 0)),
        "musica_in_fasce_num": int(st.session_state.get("iscr_fasce", 0)),
        "solo_solfeggio_num": int(st.session_state.get("iscr_solo_solfeggio", 0)),
    }
    return enrolls, enrolls_special


# ----------------------------
# Funzione di calcolo aggiornata (classi di solfeggio per durata)
# ----------------------------
def compute_totals_from_state(num_lessons=None):
    """
    Calcola ricavi, ore e costi a partire dallo stato Streamlit.
    Dipendenze globali richieste (devono essere definite nel modulo):
      - enrollment_keys, read_enrollments_from_state
      - courses (list of (key,label))
      - price_overrides, DEFAULT_PRICES_BY_MIN
      - LESSONS_PER_PACKAGE
      - prop_price, svil_price, fasce_price, solo_solf_price
      - prop_duration, svil_duration, fasce_duration
      - min_students, hourly_teacher_cost, other_fixed_costs, total_available_hours

    Restituisce un dizionario con le grandezze calcolate.
    """
    # fallback/validazione num_lessons
    if num_lessons is None:
        try:
            num_lessons = LESSONS_PER_PACKAGE
        except NameError:
            num_lessons = 1
    else:
        # ensure numeric and positive
        try:
            num_lessons = float(num_lessons)
            if num_lessons <= 0:
                num_lessons = (
                    LESSONS_PER_PACKAGE if "LESSONS_PER_PACKAGE" in globals() else 1
                )
        except Exception:
            num_lessons = (
                LESSONS_PER_PACKAGE if "LESSONS_PER_PACKAGE" in globals() else 1
            )

    lessons_base = (
        LESSONS_PER_PACKAGE
        if ("LESSONS_PER_PACKAGE" in globals() and LESSONS_PER_PACKAGE > 0)
        else 1
    )

    # leggi iscritti dallo stato
    enrolls, specials = read_enrollments_from_state(enrollment_keys)

    # -----------------------
    # RICAVI
    total_revenue = 0.0
    detail_rows = []

    for duration in (30, 45, 60):
        for key, label in courses:
            n = int(enrolls.get((duration, key), 0))
            price_per_package = float(
                price_overrides.get(
                    (duration, key), DEFAULT_PRICES_BY_MIN.get(duration, 0.0)
                )
            )
            revenue = price_per_package * n * (num_lessons / lessons_base)
            total_revenue += revenue
            detail_rows.append(
                {
                    "course_label": label,
                    "duration_min": duration,
                    "n_students": n,
                    "price_per_10_lezioni": price_per_package,
                    "revenue_for_package": revenue,
                }
            )

    # speciali (compatto)
    specials_meta = {
        "prop_num": {
            "label": "Propedeutica musicale",
            "duration_min": prop_duration,
            "price": float(prop_price),
        },
        "sviluppo_num": {
            "label": "Sviluppo musicalità",
            "duration_min": svil_duration,
            "price": float(svil_price),
        },
        "musica_in_fasce_num": {
            "label": "Musica in fasce",
            "duration_min": fasce_duration,
            "price": float(fasce_price),
        },
        "solo_solfeggio_num": {
            "label": "Solo solfeggio",
            "duration_min": 60,
            "price": float(solo_solf_price),
        },
    }

    for key, meta in specials_meta.items():
        n_students = int(specials.get(key, 0))
        if n_students <= 0:
            continue
        rev = n_students * meta["price"] * (num_lessons / lessons_base)
        total_revenue += rev
        detail_rows.append(
            {
                "course_label": meta["label"],
                "duration_min": meta["duration_min"],
                "n_students": n_students,
                "price_per_10_lezioni": meta["price"],
                "revenue_for_package": rev,
            }
        )

    # -----------------------
    # ORE PER PACCHETTO
    # 1) Individuali (strumento e anche chi ha +solfeggio mantiene le ore individuali)
    individual_hours = 0.0
    for (duration, key), n in enrolls.items():
        if key in ("solo_fiato", "solo_arco", "fiato_solf", "arco_solf"):
            individual_hours += int(n) * (duration / 60.0) * num_lessons

    # 2) Solfeggio in classe: classi durano 60' ma gli allievi sono raggruppati in base al minutaggio dello strumento.
    #    per d in (30,45,60) contiamo quanti alunni di quella durata hanno scelto +solfeggio;
    #    al gruppo 60 aggiungiamo anche i solo_solfeggio.
    solfeggio_class_count_by_duration = {}
    solfeggio_students_by_duration = {}
    total_solfeggio_students = 0

    for d in (30, 45, 60):
        students = int(enrolls.get((d, "fiato_solf"), 0)) + int(
            enrolls.get((d, "arco_solf"), 0)
        )
        if d == 60:
            students += int(specials.get("solo_solfeggio_num", 0))
        solfeggio_students_by_duration[d] = students
        total_solfeggio_students += students
        class_count = ceil(students / min_students) if students > 0 else 0
        solfeggio_class_count_by_duration[d] = class_count

    # ore solfeggio per pacchetto: ogni classe è 1 ora
    solfeggio_class_hours = sum(
        count * 1.0 * num_lessons
        for count in solfeggio_class_count_by_duration.values()
    )

    # 3) Altri corsi in classe: propedeutica, sviluppo, musica in fasce
    other_class_hours = 0.0
    if int(specials.get("prop_num", 0)) > 0:
        other_class_hours += (
            ceil(int(specials.get("prop_num")) / min_students)
            * (prop_duration / 60.0)
            * num_lessons
        )
    if int(specials.get("sviluppo_num", 0)) > 0:
        other_class_hours += (
            ceil(int(specials.get("sviluppo_num")) / min_students)
            * (svil_duration / 60.0)
            * num_lessons
        )
    if int(specials.get("musica_in_fasce_num", 0)) > 0:
        other_class_hours += (
            ceil(int(specials.get("musica_in_fasce_num")) / min_students)
            * (fasce_duration / 60.0)
            * num_lessons
        )

    total_package_hours = individual_hours + solfeggio_class_hours + other_class_hours

    # -----------------------
    # ORE SETTIMANALI (stesse logiche senza moltiplicare per num_lessons)
    weekly_individual_hours = 0.0
    for (duration, key), n in enrolls.items():
        if key in ("solo_fiato", "solo_arco", "fiato_solf", "arco_solf"):
            weekly_individual_hours += int(n) * (duration / 60.0)

    weekly_solfeggio_hours = sum(
        count * 1.0 for count in solfeggio_class_count_by_duration.values()
    )
    weekly_solfeggio_class_count_total = sum(solfeggio_class_count_by_duration.values())

    weekly_other_class_hours = 0.0
    if int(specials.get("prop_num", 0)) > 0:
        weekly_other_class_hours += ceil(
            int(specials.get("prop_num")) / min_students
        ) * (prop_duration / 60.0)
    if int(specials.get("sviluppo_num", 0)) > 0:
        weekly_other_class_hours += ceil(
            int(specials.get("sviluppo_num")) / min_students
        ) * (svil_duration / 60.0)
    if int(specials.get("musica_in_fasce_num", 0)) > 0:
        weekly_other_class_hours += ceil(
            int(specials.get("musica_in_fasce_num")) / min_students
        ) * (fasce_duration / 60.0)

    weekly_total_hours = (
        weekly_individual_hours + weekly_solfeggio_hours + weekly_other_class_hours
    )

    # -----------------------
    # COSTI
    teacher_cost = hourly_teacher_cost * (individual_hours + other_class_hours)
    solfeggio_cost = hourly_teacher_cost * solfeggio_class_hours
    total_costs = teacher_cost + solfeggio_cost + other_fixed_costs
    deviation = total_revenue - total_costs

    teacher_cost_weekly = hourly_teacher_cost * (
        weekly_individual_hours + weekly_other_class_hours
    )
    solfeggio_cost_weekly = hourly_teacher_cost * weekly_solfeggio_hours
    total_costs_weekly = teacher_cost_weekly + solfeggio_cost_weekly + other_fixed_costs

    saturation_pct = (
        (weekly_total_hours / total_available_hours) * 100
        if total_available_hours > 0
        else 0.0
    )

    # -----------------------
    # Dizionario solfeggio per durata (compatibilità)
    solfeggio_students_by_duration["total_students"] = total_solfeggio_students
    solfeggio_students_by_duration["class_count_total"] = (
        weekly_solfeggio_class_count_total
    )

    return {
        # pacchetto
        "num_lessons": num_lessons,
        "total_revenue": total_revenue,
        "individual_hours": individual_hours,
        "solfeggio_class_hours": solfeggio_class_hours,
        "solfeggio_class_count_by_duration": solfeggio_class_count_by_duration,
        "other_class_hours": other_class_hours,
        "total_hours": total_package_hours,
        "teacher_cost": teacher_cost,
        "solfeggio_cost": solfeggio_cost,
        "other_fixed_costs": other_fixed_costs,
        "total_costs": total_costs,
        "deviation": deviation,
        "detail_rows": detail_rows,
        # settimanali
        "weekly_individual_hours": weekly_individual_hours,
        "weekly_solfeggio_hours": weekly_solfeggio_hours,
        "weekly_other_class_hours": weekly_other_class_hours,
        "weekly_total_hours": weekly_total_hours,
        "weekly_teacher_cost": teacher_cost_weekly,
        "weekly_solfeggio_cost": solfeggio_cost_weekly,
        "weekly_total_costs": total_costs_weekly,
        "saturation_pct": saturation_pct,
        "solfeggio_students_by_duration": solfeggio_students_by_duration,
        "weekly_solfeggio_class_count_total": weekly_solfeggio_class_count_total,
    }


# Calcoli per 1 pacchetto (10 lezioni) e 3 pacchetti (30 lezioni)
enrolls, specials = read_enrollments_from_state(enrollment_keys)
tot_10 = compute_totals_from_state(10)
tot_30 = compute_totals_from_state(30)


# -----------------------------
# SEZIONE: Dashboard riepilogo pacchetto 10 lezioni
# -----------------------------
st.subheader("💡 Riepilogo rapido - Pacchetto 10 lezioni")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric(label="Totale costi pacchetto", value=f"€ {tot_10['total_costs']:,.0f}")

with c2:
    st.metric(
        label="Ricavi totali pacchetto", value=f"€ {tot_10['total_revenue']:,.0f}"
    )
with c3:
    st.metric(
        label="Costi - Ricavi",
        value=f"€ {(tot_10['total_costs']-tot_10["total_revenue"]):,.0f}",
    )

with c4:
    st.metric(
        label="Ore totali per pacchetto", value=f"{tot_10['weekly_total_hours']:.2f} h"
    )

with c5:
    st.metric(
        label="Saturazione settimanale", value=f"{tot_10['saturation_pct']:.2f} %"
    )


# -----------------------------
# SEZIONE: Dettaglio costi e ore
# -----------------------------
st.subheader("📊 Riepilogo Pacchetto e Ore Settimanali")

col1, col2 = st.columns(2)

with col1:
    st.write("**Dettaglio per pacchetto (10 lezioni)**:")
    st.write(f"Ore totali per pacchetto: {tot_10['total_hours']:.2f} h")
    st.write(
        f"Costo docente (lezioni individuali + altri corsi) per pacchetto: € {tot_10['teacher_cost']:,.2f}"
    )
    st.write(
        f"Costo solfeggio (classi) per pacchetto: € {tot_10['solfeggio_cost']:,.2f}"
    )
    st.write(f"Totale costi per pacchetto: € {tot_10['total_costs']:,.2f}")
    st.write(
        f"Ricavi totali (1 pacchetto = {LESSONS_PER_PACKAGE} lezioni): € {tot_10['total_revenue']:,.2f}"
    )
    st.write(
        f"Scostamento per pacchetto (ricavi - costi): € {tot_10['deviation']:,.2f}"
    )

with col2:
    st.write(
        "**Ore settimanali (effettive)** — ogni studente: max 1 lezione strumento/settimana e max 1 lezione di gruppo/solfeggio a settimana"
    )
    st.write(
        f"Ore individuali (strumento) per settimana: {tot_10['weekly_individual_hours']:.2f} h"
    )
    st.write(
        f"Ore solfeggio in classe per settimana: {tot_10['weekly_solfeggio_hours']:.2f} h"
    )
    st.write(
        f"Ore altri corsi in classe per settimana: {tot_10['weekly_other_class_hours']:.2f} h"
    )
    st.write(f"Ore totali richieste a settimana: {tot_10['weekly_total_hours']:.2f} h")
    st.write(f"Ore disponibili a settimana (tu): {total_available_hours:.2f} h")
    st.write(
        f"Percentuale di saturazione settimanale: {tot_10['saturation_pct']:.2f} %"
    )


# -----------------------------
# SEZIONE: Riepilogo Classi (basato su pacchetto 10 lezioni)
# -----------------------------
st.subheader("📚 Riepilogo Classi Formate — Pacchetto da 10 lezioni")

# Ricavo i dati dal risultato 10 lezioni
solf_30 = tot_10["solfeggio_class_count_by_duration"].get(30, 0)
solf_45 = tot_10["solfeggio_class_count_by_duration"].get(45, 0)
solf_60 = tot_10["solfeggio_class_count_by_duration"].get(60, 0)

# Classi corsi speciali
prop_classes = (
    ceil(specials["prop_num"] / min_students) if specials["prop_num"] > 0 else 0
)
fasce_classes = (
    ceil(specials["musica_in_fasce_num"] / min_students)
    if specials["musica_in_fasce_num"] > 0
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
            solf_30,
            solf_45,
            solf_60,
            prop_classes,
            fasce_classes,
        ],
    }
)

st.markdown(classi_df.to_html(index=False, justify="center"), unsafe_allow_html=True)


# --- OUTPUT: dettaglio ricavi per corso (tabella) ---
st.markdown("---")
st.header("Risultati: dettagli per corso")
df_rev = pd.DataFrame(tot_10["detail_rows"])
if not df_rev.empty:
    df_rev_display = df_rev.copy()
    df_rev_display["revenue_for_package"] = df_rev_display["revenue_for_package"].map(
        lambda x: f"€ {x:,.2f}"
    )
    df_rev_display["price_per_10_lezioni"] = df_rev_display["price_per_10_lezioni"].map(
        lambda x: f"€ {x:,.2f}"
    )
    st.dataframe(df_rev_display)
else:
    st.write("Nessun corso con iscritti.")

# st.write(
#     f"Ricavi totali (1 pacchetto = {LESSONS_PER_PACKAGE} lezioni): € {tot_10['total_revenue']:,.2f}"
# )

# --- OUTPUT: riepilogo pacchetti 10 e 30 lezioni ---
st.markdown("---")
st.header("Riepilogo costi e ricavi per pacchetto")
summary_df = pd.DataFrame(
    [
        {
            "pacchetto_lezioni": f"{tot_10['num_lessons']} lezioni (1 pacchetto)",
            "ricavi": tot_10["total_revenue"],
            "ore_totali_h": tot_10["total_hours"],
            "costo_docente (ind.+altri)": tot_10["teacher_cost"],
            "costo_solfeggio (classi)": tot_10["solfeggio_cost"],
            "altri_costi_fissi": tot_10["other_fixed_costs"],
            "costi_totali": tot_10["total_costs"],
            "scostamento": tot_10["deviation"],
        },
        {
            "pacchetto_lezioni": f"{tot_30['num_lessons']} lezioni (3 pacchetti)",
            "ricavi": tot_30["total_revenue"],
            "ore_totali_h": tot_30["total_hours"],
            "costo_docente (ind.+altri)": tot_30["teacher_cost"],
            "costo_solfeggio (classi)": tot_30["solfeggio_cost"],
            "altri_costi_fissi": tot_30["other_fixed_costs"],
            "costi_totali": tot_30["total_costs"],
            "scostamento": tot_30["deviation"],
        },
    ]
)

summary_display = summary_df.copy()
summary_display["ricavi"] = summary_display["ricavi"].map(lambda x: f"€ {x:,.2f}")
summary_display["costo_docente (ind.+altri)"] = summary_display[
    "costo_docente (ind.+altri)"
].map(lambda x: f"€ {x:,.2f}")
summary_display["costo_solfeggio (classi)"] = summary_display[
    "costo_solfeggio (classi)"
].map(lambda x: f"€ {x:,.2f}")
summary_display["altri_costi_fissi"] = summary_display["altri_costi_fissi"].map(
    lambda x: f"€ {x:,.2f}"
)
summary_display["costi_totali"] = summary_display["costi_totali"].map(
    lambda x: f"€ {x:,.2f}"
)
summary_display["scostamento"] = summary_display["scostamento"].map(
    lambda x: f"€ {x:,.2f}"
)
summary_display["ore_totali_h"] = summary_display["ore_totali_h"].map(
    lambda x: f"{x:.2f} h"
)

st.dataframe(summary_display)

# CSV download: dettagli (numerico) e summary (numerico)
csv_detail = pd.DataFrame(tot_10["detail_rows"]).to_csv(index=False)
st.download_button(
    "Scarica dettagli ricavi (CSV, 1 pacchetto)",
    data=csv_detail,
    file_name="dettagli_ricavi_1_pacchetto.csv",
    mime="text/csv",
)

csv_summary = summary_df.to_csv(index=False)
st.download_button(
    "Scarica riepilogo numerico (CSV)",
    data=csv_summary,
    file_name="riepilogo_pacchetti.csv",
    mime="text/csv",
)

# --- Output: dettaglio ore / studenti solfeggio e saturazione settimanale ---
st.markdown("---")
st.subheader(
    "Dettaglio ore / studenti solfeggio e saturazione settimanale (vista rapida)"
)
st.write("Studenti di solfeggio per durata (usati per calcolo classi):")
st.write(tot_10["solfeggio_students_by_duration"])
st.write(
    f"Numero totale classi di solfeggio (per pacchetto): {sum(tot_10['solfeggio_class_count_by_duration'].values())}"
)
st.write("---")
st.write(
    "**Ore settimanali (effettive)** — ogni studente: max 1 lezione strumento/settimana e max 1 lezione di gruppo/solfeggio a settimana"
)
st.write(
    f"Ore individuali (strumento) per settimana: {tot_10['weekly_individual_hours']:.2f} h"
)
st.write(
    f"Ore solfeggio in classe per settimana: {tot_10['weekly_solfeggio_hours']:.2f} h"
)
st.write(
    f"Ore altri corsi in classe per settimana: {tot_10['weekly_other_class_hours']:.2f} h"
)
st.write(f"Ore totali richieste a settimana: {tot_10['weekly_total_hours']:.2f} h")
st.write(f"Ore disponibili a settimana (tu): {total_available_hours:.2f} h")
st.write(f"Percentuale di saturazione settimanale: {tot_10['saturation_pct']:.2f} %")
st.write("---")
st.write("**Dettaglio per pacchetto (10 lezioni)**:")
st.write(f"Ore totali per pacchetto: {tot_10['total_hours']:.2f} h")
st.write(
    f"Costo docente (lezioni individuali + altri corsi) per pacchetto: € {tot_10['teacher_cost']:,.2f}"
)
st.write(f"Costo solfeggio (classi) per pacchetto: € {tot_10['solfeggio_cost']:,.2f}")
st.write(f"Totale costi per pacchetto: € {tot_10['total_costs']:,.2f}")
st.write(
    f"Ricavi totali (1 pacchetto = {LESSONS_PER_PACKAGE} lezioni): € {tot_10['total_revenue']:,.2f}"
)
st.write(f"Scostamento per pacchetto (ricavi - costi): € {tot_10['deviation']:,.2f}")
st.markdown("---")

st.info(
    "Pulsante 'Azzera iscritti' azzera solo i campi della sezione 1). Le sezioni 1) e 2) sono ora dentro expander apribili/chiudibili."
)
