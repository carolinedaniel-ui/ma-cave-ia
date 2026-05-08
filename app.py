import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Ma Cave", page_icon="🍷")

try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
except:
    st.error("Secrets non configurés dans Streamlit Cloud.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# --- FONCTIONS TECHNIQUES ---
def get_csv_from_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    contents = repo.get_contents("cave.csv")
    df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    return df, contents

def save_to_github(df_updated, contents):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    repo.update_file(contents.path, "Mise à jour stock cave", df_updated.to_csv(index=False), contents.sha)

# --- INTERFACE ---
st.title("🍷 Ma Cave Intelligente")

photo = st.camera_input("Scanner une étiquette")

if photo:
    if "current_vin" not in st.session_state:
        with st.spinner("Analyse et recherche (Vivino & Bibliothèque)..."):
            # 1. Extraction Vision (Identité)
            base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
            v_res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": "Identifie ce vin. Réponds uniquement: Nom;Maison;Appellation;Annee"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}]
            ).choices[0].message.content.strip().replace('"', '').split(";")

            nom_v, maison_v, app_v, annee_v = v_res[0], v_res[1], v_res[2], v_res[3]

            # 2. Vérification Bibliothèque locale
            df_cave, contents = get_csv_from_github()
            existing_vin = df_cave[df_cave['Nom'].str.contains(nom_v, case=False, na=False)].head(1)
            
            if not existing_vin.empty:
                cepages, accords = existing_vin['Cepages'].values[0], existing_vin['Accords'].values[0]
                st.info(f"✨ Vin connu. Accords récupérés de votre bibliothèque.")
            else:
                cepages, accords = "N.C", "N.C"

            # 3. Requête Texte (Note & Apogée)
            q_text = f"Pour le vin {nom_v} {maison_v} millésime {annee_v}, donne UNIQUEMENT la note Vivino et l'année d'apogée max. Format: Note;Apogee"
            if cepages == "N.C":
                q_text += ";Cepages;Accords (2 max)"

            m_res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": q_text}]
            ).choices[0].message.content.strip().replace('"', '').split(";")

            # 4. Stockage session
            st.session_state.current_vin = {
                "Date": datetime.now().strftime("%d/%m/%Y"),
                "Nom": nom_v, "Maison": maison_v, "Appellation": app_v, "Annee": annee_v,
                "Note_Vivino": m_res[0],
                "Apogee": m_res[1],
                "Cepages": m_res[2] if cepages == "N.C" else cepages,
                "Accords": m_res[3] if accords == "N.C" else accords,
                "Quantite": 1 # Valeur par défaut
            }

    # --- VALIDATION AVEC QUANTITÉ ---
    if "current_vin" in st.session_state:
        v = st.session_state.current_vin
        st.subheader(f"📝 {v['Nom']} {v['Annee']}")
        
        col_q1, col_q2 = st.columns([1, 2])
        with col_q1:
            v["Quantite"] = st.number_input("Nombre de bouteilles", min_value=1, value=1, step=1)
        
        with st.expander("Modifier les détails techniques"):
            v["Nom"] = st.text_input("Nom", v["Nom"])
            v["Annee"] = st.text_input("Millésime", v["Annee"])
            v["Apogee"] = st.text_input("Apogée (Année)", v["Apogee"])
            v["Accords"] = st.text_area("Accords", v["Accords"])

        if st.button("💾 Confirmer l'ajout au stock"):
            df_cave, contents = get_csv_from_github()
            new_row = pd.DataFrame([v])
            df_updated = pd.concat([df_cave, new_row], ignore_index=True)
            save_to_github(df_updated, contents)
            st.success(f"Ajouté : {v['Quantite']}x {v['Nom']} !")
            st.balloons()
            del st.session_state.current_vin

# --- CONSULTATION & ALERTES ---
st.markdown("---")
if st.checkbox("📊 Consulter l'inventaire complet"):
    df_cave, _ = get_csv_from_github()
    # On affiche la colonne Quantité bien en évidence
    st.dataframe(df_cave[['Quantite', 'Nom', 'Annee', 'Maison', 'Apogee', 'Note_Vivino']])

if st.checkbox("📢 Vins à boire (Apogée proche)"):
    df_cave, _ = get_csv_from_github()
    annee_actuelle = datetime.now().year
    alertes = df_cave[pd.to_numeric(df_cave['Apogee'], errors='coerce') <= annee_actuelle + 1]
    if not alertes.empty:
        st.warning(f"Attention, {len(alertes)} vins arrivent à maturité.")
        st.table(alertes[['Quantite', 'Nom', 'Annee', 'Apogee']])

# Masquage style Streamlit
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)
