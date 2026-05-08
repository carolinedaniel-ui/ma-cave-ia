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
    st.error("Secrets non configurés.")
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
        with st.spinner("Analyse et recherche..."):
            # 1. Extraction Vision (Identité)
            base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
            v_res_raw = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": "Identifie ce vin. Réponds uniquement: Nom;Maison;Appellation;Annee"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}]
            ).choices[0].message.content.strip().replace('"', '')
            
            v_res = v_res_raw.split(";")
            
            if len(v_res) < 4:
                st.error("L'IA n'a pas pu identifier le vin correctement. Réessayez avec une photo plus nette.")
                st.stop()

            nom_v, maison_v, app_v, annee_v = v_res[0], v_res[1], v_res[2], v_res[3]

            # 2. Vérification Bibliothèque
            df_cave, contents = get_csv_from_github()
            existing_vin = df_cave[df_cave['Nom'].str.contains(nom_v, case=False, na=False)].head(1)
            
            cepages, accords = ("N.C", "N.C")
            if not existing_vin.empty:
                cepages = existing_vin['Cepages'].values[0]
                accords = existing_vin['Accords'].values[0]
                st.info("✨ Vin connu dans la bibliothèque.")

            # 3. Requête Texte (Note & Apogée)
            q_text = f"Pour le vin {nom_v} {maison_v} millésime {annee_v}, donne UNIQUEMENT la note Vivino et l'année d'apogée. Format: Note;Apogee"
            if cepages == "N.C":
                q_text += ";Cepages;Accords"

            m_res_raw = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": q_text}]
            ).choices[0].message.content.strip().replace('"', '')
            
            m_res = m_res_raw.split(";")

            # --- SÉCURITÉ ANTI-BUG (L'ERREUR ÉTAIT ICI) ---
            # On remplit avec des valeurs par défaut si l'IA ne renvoie pas assez d'éléments
            note_final = m_res[0] if len(m_res) > 0 else "N.C"
            apogee_final = m_res[1] if len(m_res) > 1 else "N.C"
            cepages_final = cepages if cepages != "N.C" else (m_res[2] if len(m_res) > 2 else "N.C")
            accords_final = accords if accords != "N.C" else (m_res[3] if len(m_res) > 3 else "N.C")

            st.session_state.current_vin = {
                "Date": datetime.now().strftime("%d/%m/%Y"),
                "Nom": nom_v, "Maison": maison_v, "Appellation": app_v, "Annee": annee_v,
                "Note_Vivino": note_final,
                "Apogee": apogee_final,
                "Cepages": cepages_final,
                "Accords": accords_final,
                "Quantite": 1
            }

    # --- VALIDATION ---
    if "current_vin" in st.session_state:
        v = st.session_state.current_vin
        st.subheader(f"📝 {v['Nom']} {v['Annee']}")
        
        v["Quantite"] = st.number_input("Nombre de bouteilles", min_value=1, value=int(v.get("Quantite", 1)))
        
        with st.expander("Vérifier/Modifier les détails"):
            v["Nom"] = st.text_input("Nom", v["Nom"])
            v["Annee"] = st.text_input("Millésime", v["Annee"])
            v["Note_Vivino"] = st.text_input("Note Vivino", v["Note_Vivino"])
            v["Apogee"] = st.text_input("Apogée", v["Apogee"])
            v["Accords"] = st.text_area("Accords", v["Accords"])

        if st.button("💾 Enregistrer dans la cave"):
            df_cave, contents = get_csv_from_github()
            new_row = pd.DataFrame([v])
            df_updated = pd.concat([df_cave, new_row], ignore_index=True)
            save_to_github(df_updated, contents)
            st.success("Enregistré !")
            del st.session_state.current_vin
            st.rerun()

# --- VUE CAVE ---
st.markdown("---")
if st.checkbox("📊 Voir mon stock"):
    df_c, _ = get_csv_from_github()
    st.dataframe(df_c[['Quantite', 'Nom', 'Annee', 'Apogee']])
