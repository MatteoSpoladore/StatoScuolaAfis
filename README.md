# 🎼 Piano Corsi – App di gestione bilancio scuola di musica

Questa applicazione **Streamlit** permette di visualizzare e analizzare la situazione dei corsi e del bilancio di una scuola di musica, considerando iscritti, durata delle lezioni, costi docente e altri costi fissi. L'app fornisce sia un **riassunto macro** che un **dettaglio per corso** dei ricavi, costi e saturazione delle ore disponibili.

---

## 📌 Funzionalità principali

1. **Inserimento iscritti**
   - Inserimento del numero di allievi per corso e durata (30, 45, 60 minuti)
   - Gestione dei corsi principali:
     - Solo strumento a fiato
     - Strumento a fiato + solfeggio
     - Solo strumento ad arco
     - Strumento ad arco + solfeggio
   - Gestione dei corsi speciali / attività di gruppo:
     - Propedeutica
     - Sviluppo musicalità
     - Musica in fasce
     - Solo Solfeggio

2. **Gestione prezzi**
   - Inserimento dei prezzi per singolo corso (per pacchetto di 10 lezioni)
   - Possibilità di personalizzare il prezzo in base alla durata e tipo di corso

3. **Calcolo ricavi e costi**
   - Ricavi da corsi individuali e di gruppo
   - Costi docente per ore individuali, solfeggio e altri corsi di gruppo
   - Considerazione di costi fissi aggiuntivi e contributi
   - Calcolo dello **scostamento** tra ricavi e costi

4. **Visualizzazioni**
   - **Dashboard sintetica** con metriche principali:
     - Ricavi totali
     - Totale costi
     - Differenza ricavi/costi
     - Ore totali settimanali
     - Percentuale di saturazione delle ore disponibili
   - **Grafico a barre**: confronto Ricavi vs Costi
   - **Semicerchio (Pie Chart)**: utilizzo delle ore della sede
   - **Tabelle dettagliate** dei corsi con ricavi, costi e saldo
   - **Riepilogo classi formate** per solfeggio, propedeutica e attività di gruppo

5. **Gestione sessione**
   - Pulsanti per azzerare iscritti o corsi speciali
   - Valori di default preimpostati per ogni corso

---

## ⚙️ Configurazioni Sidebar

- Numero minimo di studenti per classe di solfeggio
- Costo docente per ora
- Totale ore disponibili a settimana
- Contributi accantonati
- Altri costi fissi

---

## 🧮 Logica di calcolo

- I corsi di **solfeggio** sono raggruppati per durata (30, 45, 60 minuti)
- Ogni classe di solfeggio dura 1 ora e il numero di classi è calcolato con `ceil(numero_studenti / min_students)`
- I costi docente sono calcolati su ore individuali e ore di classe
- Gli altri corsi di gruppo (propedeutica, sviluppo musicalità, musica in fasce) vengono calcolati considerando la durata specifica e il numero di classi necessarie

---

## 🛠️ Tecnologie utilizzate

- **Python 3.10+**
- **Streamlit** – per l'interfaccia web interattiva
- **Pandas** – per gestione e manipolazione dei dati
- **Plotly** – per grafici dinamici e interattivi

---

## 🚀 Come avviare l’app

1. Clona il repository:

```bash
git clone https://github.com/tuo-username/piano-corsi.git
cd piano-corsi
