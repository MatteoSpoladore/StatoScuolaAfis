import streamlit as st
import pandas as pd

import plotly.graph_objects as go
import plotly.express as px
from math import ceil

# ----------------------------
# CONFIGURAZIONE PAGINA / COSTANTI
# ----------------------------
st.set_page_config(page_title="Piano ricavi/costi - Corsi Musicali", layout="wide")
st.title("Stato scuola di musica")
# st.markdown(
#     "App per calcolare ricavi, costi, ore e saturazione settimanale a partire dagli iscritti per corso e minutaggio. "
#     "Logica: **strumento** = lezione individuale; **solfeggio** = lezioni in classe; "
#     "gli altri corsi sono in classe. I costi di solfeggio sono calcolati automaticamente."
# )
st.markdown(
    """
### App per visualizzare la macro situazione del bilancio della scuola di musica  

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

defaults_specials = {
    "prop": {"students": 0, "duration": 60, "price": 100},
    "svil": {"students": 5, "duration": 45, "price": 80},
    "fasce": {"students": 0, "duration": 30, "price": 80},
    "solo_solfeggio": {"students": 12, "duration": 60, "price": 100},
}

# ----------------------------
# FUNZIONI
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


def render_sidebar_settings():
    st.sidebar.header("Impostazioni generali")
    st.sidebar.write(
        "Queste informazioni sono considerate costanti, la loro modifica comporta importanti cambiamenti nel bilancio"
    )
    min_students = st.sidebar.number_input(
        "Numero minimo allievi per classe di solfeggio", 1, 15, 6
    )
    hourly_teacher_cost = st.sidebar.number_input(
        "Costo docente per ora (€)", 0.0, 50.0, 24.0, step=0.5
    )
    total_available_hours = st.sidebar.number_input(
        "Totale ore disponibili a settimana", 1, 500, 150, step=1
    )
    contributi = st.sidebar.number_input(
        "Contributi accantonati (€)", 0, 20000, 0, step=500
    )
    other_fixed_costs = st.sidebar.number_input("Altri costi fissi (€)", 0, 1000, 0)
    return (
        min_students,
        hourly_teacher_cost,
        total_available_hours,
        contributi,
        other_fixed_costs,
    )


def render_input_iscritti(defaults):
    with st.expander("1) Inserisci iscritti per corso e durata", expanded=False):
        st.subheader("Inserisci iscritti per corso e durata")
        enrollment_keys = {}
        for duration in [30, 45, 60]:
            st.markdown(f"**Durata {duration} min**")
            cols = st.columns(4)
            for i, (key, label) in enumerate(courses):
                session_key = f"iscr_{key}_{duration}"
                val = cols[i].number_input(
                    label,
                    min_value=0,
                    value=defaults.get((duration, key), 0),
                    key=session_key,
                )
                enrollment_keys[(duration, key)] = session_key
        enrollment_keys_list = [
            v for v in enrollment_keys.values()
        ]  # tutte le chiavi numeriche
        st.button(
            "🔄 Azzera iscritti principali",
            on_click=reset_session_keys,
            kwargs={"keys": enrollment_keys_list},
        )
        return enrollment_keys


def render_input_specials(defaults):
    with st.expander("2) Inserisci corsi di gruppo", expanded=False):
        st.subheader("Inserisci altri corsi / attività")
        specials_data = {}
        cols = st.columns(4)
        for i, key in enumerate(["prop", "svil", "fasce", "solo_solfeggio"]):
            s = cols[i].number_input(
                f"{key} - numero iscritti",
                0,
                100,
                defaults[key]["students"],
                key=f"special_{key}_students",
            )
            specials_data[key] = {
                "students": s,
                "duration": defaults[key]["duration"],
                "price": defaults[key]["price"],
            }
        special_keys = [
            "iscr_prop",
            "iscr_sviluppo",
            "iscr_fasce",
            "iscr_solo_solfeggio",
        ]
        st.button(
            "🔄 Azzera specials",
            on_click=reset_session_keys,
            kwargs={"keys": special_keys},
        )
        return specials_data


def render_prices(defaults):
    with st.expander("3) Inserisci prezzi per singolo corso", expanded=False):
        st.subheader("Inserisci Prezzi per singolo corso (€/10 lezioni)")
        price_overrides = {}
        for duration in [30, 45, 60]:
            st.markdown(f"**Durata {duration} min**")
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
    other_fixed_costs,
    num_lessons=LESSONS_PER_PACKAGE,
):
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
    total_revenue += contributi

    # Ore per pacchetto
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
            # aggiungo i "solo solfeggio" presi da specials (numero) oppure da specials_data fallback
            students += int(specials.get("solo_solfeggio", 0))
        class_count = ceil(students / min_students) if students > 0 else 0
        solfeggio_class_count_by_duration[d] = class_count

    solfeggio_class_hours = sum(
        count * 1.0 * num_lessons
        for count in solfeggio_class_count_by_duration.values()
    )

    # Altri corsi in classe: prop, svil, fasce
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

    teacher_cost = hourly_teacher_cost * (individual_hours + other_class_hours)
    solf_cost = hourly_teacher_cost * solfeggio_class_hours
    total_costs = teacher_cost + solf_cost + other_fixed_costs
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
        "teacher_cost": teacher_cost,
        "solfeggio_cost": solf_cost,
        "total_costs": total_costs,
        "deviation": deviation,
        "detail_rows": detail_rows,
        "solfeggio_class_count_by_duration": solfeggio_class_count_by_duration,
    }


def render_dashboard(totals):
    st.subheader("💡 Riepilogo rapido")
    cols = st.columns(5)
    cols[0].metric("Totale costi", f"€ {totals['total_costs']:,.0f}")
    cols[1].metric("Ricavi totali", f"€ {totals['total_revenue']:,.0f}")
    cols[2].metric(
        "Ricavi - Costi", f"€ {totals['total_revenue'] - totals['total_costs']:,.0f}"
    )
    cols[3].metric("Ore totali", f"{totals['total_week_hours']:.2f} h")
    cols[4].metric("Saturazione", f"{totals['saturation']:.2f} %")


def render_detail_table(totals):
    st.subheader("📊 Dettaglio ricavi per corso")
    with st.expander("dettagli ricavi per corso", expanded=False):
        df = pd.DataFrame(totals["detail_rows"])
        if not df.empty:
            df_display = df.copy()
            for col in ["revenue_for_package", "price_per_10_lezioni"]:
                df_display[col] = df_display[col].map(lambda x: f"€ {x:,.2f}")
            st.dataframe(df_display)
        else:
            st.write("Nessun corso con iscritti.")


# ----------------------------
# LOGICA STREAMLIT
# ----------------------------
(
    min_students,
    hourly_teacher_cost,
    total_available_hours,
    contributi,
    other_fixed_costs,
) = render_sidebar_settings()
enrollment_keys = render_input_iscritti(default_enrollments)
specials_data = render_input_specials(defaults_specials)
price_overrides = render_prices(PRICE_TABLE)

enrolls, specials = read_enrollments(enrollment_keys, specials_data)
tot_10 = compute_totals(
    enrolls,
    specials,
    specials_data,
    price_overrides,
    min_students,
    hourly_teacher_cost,
    contributi,
    other_fixed_costs,
)


col_left, col_right = st.columns(2)

totals = tot_10  # alias

used_week_hours = totals.get("total_week_hours", totals.get("weekly_total_hours", 0.0))
available_hours = (
    float(total_available_hours) if "total_available_hours" in globals() else 1.0
)
used = min(used_week_hours, available_hours)
remaining = max(available_hours - used, 0.0)

# --- Semicerchio orizzontale (alla "alba/tramonto") ---
# costruiamo le tre fette: [used, remaining, filler]
# il filler serve a coprire la metà inferiore (respingendo le due fette visibili nella metà superiore)
semi_vals = [used, remaining, available_hours]  # il terzo valore sarà reso trasparente

# colori: ore usate rosso, ore rimanenti blu, filler trasparente
colors = ["#EF553B", "#636EFA", "rgba(0,0,0,0)"]

fig_semi = go.Figure(
    go.Pie(
        values=[remaining, used],  # ordine invertito
        hole=0.5,
        sort=False,
        direction="clockwise",
        marker=dict(
            colors=[
                "rgba(0,0,0,0)",  # metà inferiore invisibile
                # "#636EFA",  # blu: ore rimanenti
                "#EF553B",  # rosso: ore usate
            ],
            line=dict(color="white", width=1),
        ),
        textinfo="none",
        hoverinfo="value",
        rotation=0,  # ruota per mettere i colori nella metà superiore
    )
)

# centro con testo e percentuale
pct = (used / available_hours * 100) if available_hours > 0 else 0.0
fig_semi.update_layout(
    title="Utilizzo ore sede",
    title_x=0.38,
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

# disegno: metti il semicerchio nella colonna di destra
with col_right:
    st.plotly_chart(fig_semi, width="stretch")


# --- Grafico a barre: Ricavi vs Costi (nella colonna di sinistra) ---
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
    title="Confronto Ricavi e Costi",
    title_x=0.4,
    margin=dict(t=30, b=30, l=20, r=20),
    yaxis_title="€",
    xaxis_title="",
    showlegend=False,
)
max_val = max(ricavi, costi)
fig_bar.update_yaxes(
    tickformat=",", range=[0, max_val + 5000]  # aggiunge +1000 al limite superiore
)

with col_left:
    st.plotly_chart(fig_bar, width="stretch")


render_dashboard(tot_10)
render_detail_table(tot_10)


# -----------------------------
# AGGIUNTA: Riepilogo Classi + Dettaglio costi/ore (usa enrolls, specials, min_students, tot_10)
# -----------------------------

# calcoli locali per classi di solfeggio raggruppate per minutaggio strumento
solfeggio_class_count_by_duration = {}
solfeggio_students_by_duration = {}
for d in (30, 45, 60):
    students = int(enrolls.get((d, "fiato_solf"), 0)) + int(
        enrolls.get((d, "arco_solf"), 0)
    )
    if d == 60:
        # i solo_solfeggio partecipano al gruppo 60'
        students += int(
            specials_data.get("solo_solfeggio", {}).get(
                "students", defaults_specials["solo_solfeggio"]["students"]
            )
        )
    solfeggio_students_by_duration[d] = students
    solfeggio_class_count_by_duration[d] = (
        ceil(students / min_students) if students > 0 else 0
    )

# classi per corsi speciali (propedeutica, musica in fasce)
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

# Tabella classi (centrata via to_html)
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

st.markdown("### 📚 Riepilogo Classi Formate")
with st.expander("riepilogo classi formate", expanded=False):
    st.markdown(
        classi_df.to_html(index=False, justify="center"), unsafe_allow_html=True
    )

# -----------------------------
# Dettaglio costi e ore (due colonne)
# -----------------------------
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
# prop, svil, fasce: prendo i valori reali da specials_data (numero studenti e durata impostata nella UI)
for key in ("prop", "svil", "fasce"):
    students = int(
        specials_data.get(key, {}).get("students", defaults_specials[key]["students"])
    )
    duration = defaults_specials[key]["duration"]
    if students > 0:
        weekly_other_class_hours += ceil(students / min_students) * (duration / 60.0)

weekly_total_hours = (
    weekly_individual_hours + weekly_solfeggio_hours + weekly_other_class_hours
)
saturation_pct = (
    (weekly_total_hours / total_available_hours) * 100
    if total_available_hours > 0
    else 0.0
)

# ora mostriamo le due colonne
st.markdown("### 📊 Riepilogo Costi, Ricavi e Ore")
with st.expander("Riepilogo costi, ricavi e ore espanso", expanded=False):
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
            f"Ore individuali (strumento) per settimana: {weekly_individual_hours:.2f} h"
        )
        st.write(
            f"Ore solfeggio in classe per settimana: {weekly_solfeggio_hours:.2f} h"
        )
        st.write(
            f"Ore altri corsi in classe per settimana: {weekly_other_class_hours:.2f} h"
        )
        st.write(f"Ore totali richieste a settimana: {weekly_total_hours:.2f} h")
        st.write(f"Ore disponibili a settimana (tu): {total_available_hours:.2f} h")
        st.write(f"Percentuale di saturazione settimanale: {saturation_pct:.2f} %")
