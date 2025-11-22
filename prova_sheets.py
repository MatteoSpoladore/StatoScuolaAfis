####
import os
from oauth2client.service_account import ServiceAccountCredentials
import gspread

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# --- Credenziali (metti il file JSON in locale o usa variabile ambiente) ---
creds_path = (
    "credenziali.json"  # o usa os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
)
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
client = gspread.authorize(creds)

# --- Apri lo spreadsheet e lo sheet ---
spreadsheet = client.open("Database studenti 25/26")
sheet = spreadsheet.worksheet("Prospetto situazione attuale")

# --- Leggi tutto in DataFrame ---
df = pd.DataFrame(sheet.get_all_values())

# --- Estrazione tabelle dal foglio ---
# ATTENZIONE: modifica gli indici delle righe e colonne secondo la posizione reale delle tue tabelle

# PRICE_TABLE (A-C, righe 2-13)
price_df = df.iloc[1:13, 0:3]
price_df.columns = ["Durata", "Corso", "Prezzo"]
PRICE_TABLE = {
    (int(row["Durata"]), row["Corso"]): float(row["Prezzo"])
    for idx, row in price_df.iterrows()
    if row["Durata"] != "" and row["Corso"] != "" and row["Prezzo"] != ""
}

# DEFAULT_PRICES (E-F, righe 2-4)
default_df = df.iloc[1:4, 4:6]
default_df.columns = ["Durata", "Prezzo"]
DEFAULT_PRICES_BY_MIN = {
    int(row["Durata"]): float(row["Prezzo"])
    for idx, row in default_df.iterrows()
    if row["Durata"] != "" and row["Prezzo"] != ""
}


# ENROLLMENTS (H-J, righe 2-13)
def safe_int(x):
    try:
        return int(x)
    except:
        return None


# ENROLLMENTS (H-J, righe 2-13)
enroll_df = df.iloc[1:13, 7:10]
enroll_df.columns = ["Durata", "Corso", "Iscritti"]

default_enrollments = {}
for idx, row in enroll_df.iterrows():
    durata = safe_int(row["Durata"])
    iscritti = safe_int(row["Iscritti"])
    corso = row["Corso"]
    if durata is not None and iscritti is not None and corso != "":
        default_enrollments[(durata, corso)] = iscritti


# SPECIALS (L-O, righe 2-5)
def safe_int(x):
    try:
        return int(x)
    except:
        return None


def safe_float(x):
    try:
        return float(x)
    except:
        return None


# --- SPECIALS / DEFAULT_SPECIALS (L-O, righe 2-5) ---
specials_df = df.iloc[1:5, 11:15]  # modifica gli indici se servono
specials_df.columns = ["Corso", "Studenti", "Durata", "Prezzo"]

defaults_specials = {}
for idx, row in specials_df.iterrows():
    corso = row["Corso"]
    students = safe_int(row["Studenti"])
    duration = safe_int(row["Durata"])
    price = safe_float(row["Prezzo"])

    if (
        corso != ""
        and students is not None
        and duration is not None
        and price is not None
    ):
        defaults_specials[corso] = {
            "students": students,
            "duration": duration,
            "price": price,
        }
