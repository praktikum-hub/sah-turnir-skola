import streamlit as st
import pandas as pd
import json
import os
import requests
import base64
from datetime import datetime

SIGURNA_SIFRA = "SahSkola2026"


# Postavke datoteka
DATA_FILE = "sah_podaci.json"
LOG_FILE = "sah_povijest_meceva.json"
POCETNI_REJTING = 1200
K_FAKTOR = 32

# --- FUNKCIJE ZA UPRAVLJANJE PODACIMA ---
# def ucitaj_podatke():
#     if os.path.exists(DATA_FILE):
#         with open(DATA_FILE, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return {}

# def spremi_podatke(podaci):
#     with open(DATA_FILE, "w", encoding="utf-8") as f:
#         json.dump(podaci, f, indent=4, ensure_ascii=False)

# def ucitaj_povijest():
#     if os.path.exists(LOG_FILE):
#         with open(LOG_FILE, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return []

# def spremi_povijest(povijest):
#     with open(LOG_FILE, "w", encoding="utf-8") as f:
#         json.dump(povijest, f, indent=4, ensure_ascii=False)

# --- FUNKCIJE ZA UPRAVLJANJE PODACIMA PREKO GITHUBA ---

# Dohvaćanje sigurnih ključeva iz Streamlit Secrets postavki
GH_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GH_REPO = st.secrets.get("GITHUB_REPO", "")

# GH_TOKEN = ""
# GH_REPO = ""

def dohvati_s_githuba(filename):
    """Učitava datoteku izravno s GitHub API-ja."""
    if not GH_TOKEN or not GH_REPO:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        return [] if "povijest" in filename else {}



    if "/repos/" in GH_REPO:
        cista_putanja = GH_REPO.lstrip("/")
        url = f"https://api.github.com/repos/{cista_putanja}/contents/{filename}"
    else:
        cisti_repo = GH_REPO.strip("/")
        url = f"https://api.github.com/repos/{cisti_repo}/contents/{filename}"


 
    headers = {
        #"Authorization": f"token {GH_TOKEN}",
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Streamlit-Chess-App"
    }
    
    try:
        odgovor = requests.get(url, headers=headers, timeout=5)
        
        if odgovor.status_code == 200:
            sadrzaj_base64 = odgovor.json()["content"]
            sadrzaj_tekst = base64.b64decode(sadrzaj_base64).decode("utf-8")
            return json.loads(sadrzaj_tekst)
    except Exception as e:
        st.sidebar.error(f"⚠️ Problem s GitHub vezom: {e}")
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
                
    return [] if "povijest" in filename else {}

def spremi_na_github(filename, podaci):
    """Sprema datoteku natrag na GitHub repozitorij."""
    novi_sadrzaj = json.dumps(podaci, indent=4, ensure_ascii=False)
    
    if not GH_TOKEN or not GH_REPO:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(novi_sadrzaj)
        return

    # Čvrsto definirana i ispravna API putanja
    #url = f"https://api.github.com{GH_REPO}/contents/{filename}"
    if "/repos/" in GH_REPO:
        cista_putanja = GH_REPO.lstrip("/")
        url = f"https://api.github.com/repos/{cista_putanja}/contents/{filename}"
    else:
        cisti_repo = GH_REPO.strip("/")
        url = f"https://api.github.com/repos/{cisti_repo}/contents/{filename}"


    headers = {
        #"Authorization": f"token {GH_TOKEN}",
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Streamlit-Chess-App"
    }
    
    try:
        sha = ""
        odgovor_get = requests.get(url, headers=headers, timeout=5)      
        
        if odgovor_get.status_code == 200:
            sha = odgovor_get.json()["sha"]
            
        sadrzaj_base64 = base64.b64encode(novi_sadrzaj.encode("utf-8")).decode("utf-8")
        payload = {
            "message": f"Automatsko ažuriranje {filename} s turnira",
            "content": sadrzaj_base64,
            #"sha": sha if sha else None
       # }
        }
        if sha:
            payload["sha"] = sha
        
        requests.put(url, headers=headers, json=payload, timeout=5)
        odgovor_put = requests.put(url, headers=headers, json=payload, timeout=5)
        
    except Exception:
        # Ako internet zakže, spremi lokalno na disk poslužitelja
        with open(filename, "w", encoding="utf-8") as f:
            f.write(novi_sadrzaj)


# Preusmjeravanje starih funkcija na novi GitHub sustav
def ucitaj_podatke(): return dohvati_s_githuba(DATA_FILE)
def spremi_podatke(podaci): spremi_na_github(DATA_FILE, podaci)
def ucitaj_povijest(): return dohvati_s_githuba(LOG_FILE)
def spremi_povijest(povijest): spremi_na_github(LOG_FILE, povijest)


def izracunaj_elo_promjenu(rejting_a, rejting_b, ishod_a):
    ocekivani = 1 / (1 + 10 ** ((rejting_b - rejting_a) / 400))
    novi_rejting = rejting_a + K_FAKTOR * (ishod_a - ocekivani)
    return round(novi_rejting, 1)


def preracunaj_sve_iz_povijesti():
    podaci = ucitaj_podatke()
    povijest = ucitaj_povijest()
    
    # Resetiraj sve igrače na početne vrijednosti
    for igrac in podaci:
        podaci[igrac] = {"rejting": float(POCETNI_REJTING), "odigrano": 0, "pobjede": 0, "remiji": 0, "porazi": 0}
        
    # Ponovno odigraj sve mečeve kronološkim redom
    for mec in povijest:
        b = mec["bijeli"]
        c = mec["crni"]
        ishod = mec["ishod"]
        
        # Osiguraj da igrači postoje u bazi (ako su dodani u međuvremenu)
        for igrac in [b, c]:
            if igrac not in podaci:
                podaci[igrac] = {"rejting": float(POCETNI_REJTING), "odigrano": 0, "pobjede": 0, "remiji": 0, "porazi": 0}
        
        if ishod == "1-0":
            ib, ic = 1.0, 0.0
            podaci[b]["pobjede"] += 1
            podaci[c]["porazi"] += 1
        elif ishod == "0-1" or ishod == "0-1":  # Pokriva tipfeler
            ib, ic = 0.0, 1.0
            podaci[c]["pobjede"] += 1
            podaci[b]["porazi"] += 1
        else:
            ib, ic = 0.5, 0.5
            podaci[b]["remiji"] += 1
            podaci[c]["remiji"] += 1
            
        stari_b = podaci[b]["rejting"]
        stari_c = podaci[c]["rejting"]
        
        podaci[b]["rejting"] = izracunaj_elo_promjenu(stari_b, stari_c, ib)
        podaci[c]["rejting"] = izracunaj_elo_promjenu(stari_c, stari_b, ic)
        podaci[b]["odigrano"] += 1
        podaci[c]["odigrano"] += 1
        
    spremi_podatke(podaci)

# --- STREAMLIT SUČELJE ---
st.set_page_config(page_title="Školski Šahovski Turnir", layout="wide", page_icon="👑")
st.title("👑 Školski Šahovski Turnir - Rang Lista")


# --- PROVJERA ZAKLJUČAVANJA (LOGIN) ---
if "autentificiran" not in st.session_state:
    st.session_state["autentificiran"] = False

if not st.session_state["autentificiran"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])  # Centriranje forme na ekranu
    with col2:
        st.subheader("🔐 Prijava u šahovski sustav")
        unesena_sifra = st.text_input("Unesite lozinku za pristup:", type="password")
        if st.button("Prijavi se", use_container_width=True):
            if unesena_sifra == SIGURNA_SIFRA:
                st.session_state["autentificiran"] = True
                st.success("Uspješna prijava!")
                st.rerun()
            else:
                st.error("❌ Pogrešna lozinka. Pokušajte ponovno.")
    st.stop()  # Zaustavlja prikaz ostatka aplikacije ako lozinka nije točna


# Inicijalizacija i učitavanje podataka
podaci = ucitaj_podatke()
povijest = ucitaj_povijest()

# Bočna traka za administraciju (Profesor)
st.sidebar.header("🛠️ Administracija za Profesora")

# 1. DODAVANJE IGRAČA
# novi_igrac = st.sidebar.text_input("Dodaj novog učenika/ca:")
# if st.sidebar.button("Registriraj igrača"):
#     if novi_igrac.strip() and novi_igrac.strip() not in podaci:
#         podaci[novi_igrac.strip()] = {"rejting": float(POCETNI_REJTING), "odigrano": 0, "pobjede": 0, "remiji": 0, "porazi": 0}
#         spremi_podatke(podaci)
#         st.sidebar.success(f"Učenik {novi_igrac} uspješno dodan!")
#         st.rerun()
#     elif novi_igrac.strip() in podaci:
#         st.sidebar.warning("Učenik već postoji.")

# 1. DODAVANJE I BRISANJE IGRAČA
st.sidebar.subheader("👥 Upravljanje učenicima")
novi_igrac = st.sidebar.text_input("Dodaj novog učenika/ca:")
if st.sidebar.button("Registriraj igrača", width='stretch'):
    if novi_igrac.strip() and novi_igrac.strip() not in podaci:
        podaci[novi_igrac.strip()] = {"rejting": float(POCETNI_REJTING), "odigrano": 0, "pobjede": 0, "remiji": 0, "porazi": 0}
        spremi_podatke(podaci)
        st.sidebar.success(f"Učenik {novi_igrac} uspješno dodan!")
        st.rerun()
    elif novi_igrac.strip() in podaci:
        st.sidebar.warning("Učenik već postoji.")

# --- NOVI DIO KODA ZA BRISANJE UČENIKA ---
if podaci:
    st.sidebar.markdown(" ")
    lista_za_brisanje = sorted(list(podaci.keys()))
    igrac_za_brisanje = st.sidebar.selectbox("Odaberi učenika za brisanje:", lista_za_brisanje, key="brisanje_odabir")
    
    if st.sidebar.button("🗑️ Trajno obriši učenika", type="primary", width='stretch'):
        # 1. Ukloni igrača iz baze igrača
        del podaci[igrac_za_brisanje]
        spremi_podatke(podaci)
        
        # 2. Očisti povijest mečeva u kojima je taj igrač sudjelovao da se ne kvari matematika
        povijest = [m for m in povijest if m["bijeli"] != igrac_za_brisanje and m["crni"] != igrac_za_brisanje]
        # Ponovno indeksiraj ID-ove preostalih mečeva od 1 nadalje
        for i, m in enumerate(povijest, start=1):
            m["id"] = i
        spremi_povijest(povijest)
        
        # 3. Preračunaj sve ponovno kako bi tablica bila čista
        preracunaj_sve_iz_povijesti()
        st.sidebar.success(f"Učenik {igrac_za_brisanje} i svi njegovi mečevi su uklonjeni!")
        st.rerun()


# 2. UPIS REZULTATA MEČA
st.sidebar.markdown("---")
st.sidebar.subheader("📝 Unos rezultata meča")
if len(podaci) >= 2:
    lista_igraca = sorted(list(podaci.keys()))
    bijeli = st.sidebar.selectbox("Bijele figure:", lista_igraca, key="bijeli_odabir")
    crni = st.sidebar.selectbox("Crne figure:", lista_igraca, key="crni_odabir")
    
    ishod = st.sidebar.selectbox("Ishod meča:", ["Pobjeda Bijelog (1-0)", "Pobjeda Crnog (0-1)", "Remi (1/2 - 1/2)"])
    
    if st.sidebar.button("Spremi rezultat"):
        if bijeli == crni:
            st.sidebar.error("Igrač ne može igrati protiv samog sebe!")
        else:
            kratica_ishoda = "1-0" if "1-0" in ishod else "0-1" if "0-1" in ishod else "1/2-1/2"
            novi_mec = {
                "id": len(povijest) + 1,
                "datum": datetime.now().strftime("%d.%m.%Y. %H:%M"),
                "bijeli": bijeli,
                "crni": crni,
                "ishod": kratica_ishoda
            }
            povijest.append(novi_mec)
            spremi_povijest(povijest)
            preracunaj_sve_iz_povijesti()

           # st.session_state["podaci"] = ucitaj_podatke()
           # st.session_state["povijest"] = ucitaj_povijest()

            # DODAJTE OVO NA VRH GLAVNOG KODA (izvan funkcija, odmah nakon učitavanja datoteka):
            if "podaci" not in st.session_state:
                st.session_state["podaci"] = podaci
            if "povijest" not in st.session_state:
                st.session_state["povijest"] = povijest

            
            st.sidebar.success("Rezultat uspješno spremljen!")
            st.rerun()
else:
    st.sidebar.info("Dodajte barem 2 igrača za unos mečeva.")


    # Gumb za odjavu na dnu bočne trake
st.sidebar.markdown("---")
if st.sidebar.button("🔒 Odjavi se", use_container_width=True):
    st.session_state["autentificiran"] = False
    st.rerun()


# --- GLAVNI EKRAN (Prikaz rezultata) ---
tab1, tab2 = st.tabs(["📊 Rang Lista", "⏳ Administracija "])

with tab1:
    st.subheader("Trenutni poredak učenika")
    if podaci:
        df = pd.DataFrame.from_dict(podaci, orient="index").reset_index()
        df.columns = ["Ime i Prezime", "Elo Rejting", "Broj Mečeva", "Pobjede", "Remiji", "Porazi"]
        df = df.sort_values(by=["Elo Rejting", "Pobjede"], ascending=False).reset_index(drop=True)
        df.index += 1  # Rang kreće od 1 umjesto 0
        st.dataframe(df, width='stretch')
    else:
        st.info("Nema registriranih igrača. Koristite bočni izbornik za unos.")

with tab2:
    st.subheader("Povijest odigranih mečeva")
    if povijest:
        df_povijest = pd.DataFrame(povijest)
        # Reorganizacija stupaca za ljepši prikaz
        df_povijest = df_povijest[["id", "datum", "bijeli", "crni", "ishod"]]
        df_povijest.columns = ["ID Meča", "Datum i Vrijeme", "Bijeli", "Crni", "Rezultat"]
        st.dataframe(df_povijest.sort_values(by="ID Meča", ascending=False), width='stretch', hide_index=True)
        
        # Alati za profesora u slučaju pogreške
        st.markdown("### 🛠️ Ispravak pogrešnog unosa")
        st.caption("Ako ste pogriješili pri unosu, ovdje možete obrisati zadnji meč ili meč prema njegovom ID broju. Sustav će automatski preračunati točne bodove.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ Obriši zadnji uneseni meč"):
                povijest.pop()
                spremi_povijest(povijest)
                preracunaj_sve_iz_povijesti()
                st.success("Zadnji meč je uspješno izbrisan, tablica je ažurirana!")
                st.rerun()
        
        with col2:
            id_za_brisanje = st.number_input("Unesite ID meča za brisanje:", min_value=1, max_value=len(povijest), step=1)
            if st.button("🗑️ Obriši odabrani ID"):
                povijest = [m for m in povijest if m["id"] != id_za_brisanje]
                # Ponovno indeksiraj ID-ove da ostanu po redu
                for i, m in enumerate(povijest, start=1):
                    m["id"] = i
                spremi_povijest(povijest)
                preracunaj_sve_iz_povijesti()
                st.success(f"Meč s ID-om {id_za_brisanje} je izbrisan, bodovi preračunati!")
                st.rerun()
    else:
        st.info("Još nema odigranih mečeva.")
