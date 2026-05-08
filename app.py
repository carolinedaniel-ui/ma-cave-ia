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
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
except:
    st.error("Secrets non configurés.")
    st.stop()

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
    repo.update_file(contents.path, "Mise à jour cave", df_updated.to_csv(index=False), contents.sha)

# --- INTERFACE ---
st.title("🍷 Ma Gestion de Cave")

# MODIFICATION ICI : On utilise label_visibility pour un affichage plus propre sur mobile
# Note : Pour forcer la caméra arrière sur Android/iOS, il est crucial d'ouvrir 
# l'application dans Chrome ou Safari (hors de l'aperçu Instagram/WhatsApp)
photo = st.camera_input("Scanner une étiquette", label_visibility="visible")

if photo:
    if "current_vin" not in st.session_state:
        with st.spinner("Analyse complète de l'étiquette..."):
            base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
            
            # 1. ANALYSE VISION
            v_res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": "Analyse ce vin. Réponds uniquement avec ce format strict : Nom;Maison;Appellation;Annee;Cepages;Note_Vivino;Accords;Apogee"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}]
            ).choices[0].message.content.strip().replace('"', '').split(";")

            while len(v_res) < 8:
                v_res.append("N.C")

            # 2. VÉRIFICATION BIBLIOTHÈQUE
            df_cave, contents = get_csv_from_github()
            nom_ia = v_res[0]
            
            match = df_cave[df_cave['Nom'].str.contains(nom_ia, case=False, na=False)].head(1)
            
            if not match.empty:
                st.info(f"✨ Informations complétées par votre bibliothèque pour {nom_ia}")
                v_cepages = match['Cepages'].values[0] if v_res[4] == "N.C" else v_res[4]
                v_accords = match['Accords'].values[0] if v_res[6] == "N.C" else v_res[6]
            else:
                v_cepages, v_accords = v_res[4], v_res[6]

            # 3. CRÉATION DE LA FICHE SESSION
            st.session_state.current_vin = {
                "Date": datetime.now().strftime("%d/%m/%Y"),
                "Nom": v_res[0],
                "Maison": v_res[1],
                "Appellation": v_res[2],
                "Annee": v_res[3],
                "Cepages": v_cepages,
                "Note_Vivino": v_res[5],
                "Accords": v_accords,
                "Apogee": v_res[7],
                "Quantite": 1
            }

    # --- VALIDATION ---
    if "current_vin" in st.session_state:
        v = st.session_state.current_vin
        st.subheader(f"📝 {v['Nom']} ({v['Annee']})")
        
        v["Quantite"] = st.number_input("Nombre de bouteilles", min_value=1, value=int(v.get("Quantite", 1)))
        
        col1, col2 = st.columns(2)
        with col1:
            v["Nom"] = st.text_input("Nom", v["Nom"])
            v["Maison"] = st.text_input("Maison", v["Maison"])
            v["Appellation"] = st.text_input("Appellation", v["Appellation"])
            v["Annee"] = st.text_input("Année", v["Annee"])
        with col2:
            v["Cepages"] = st.text_input("Cépages", v["Cepages"])
            v["Note_Vivino"] = st.text_input("Note Vivino", v["Note_Vivino"])
            v["Apogee"] = st.text_input("Apogée", v["Apogee"])
            v["Accords"] = st.text_area("Accords", v["Accords"])

        if st.button("💾 Confirmer l'ajout"):
            df_cave, contents = get_csv_from_github()
            new_row = pd.DataFrame([v])
            df_updated = pd.concat([df_cave, new_row], ignore_index=True)
            save_to_github(df_updated, contents)
            st.success("Enregistré avec succès !")
            del st.session_state.current_vin
            st.rerun()

# --- ONGLETS BAS DE PAGE ---
st.markdown("---")
tab1, tab2 = st.tabs(["📊 Inventaire", "📢 À Boire"])

with tab1:
    df_c, _ = get_csv_from_github()
    if not df_c.empty:
        st.dataframe(df_c[['Quantite', 'Nom', 'Maison', 'Appellation', 'Annee', 'Note_Vivino', 'Apogee']])
    else:
        st.info("Cave vide.")

with tab2:
    if not df_c.empty:
        annee_now = datetime.now().year
        df_c['Apogee_Num'] = pd.to_numeric(df_c['Apogee'], errors='coerce')
        alertes = df_c[df_c['Apogee_Num'] <= (annee_now + 1)]
        if not alertes.empty:
            st.warning(f"{len(alertes)} bouteilles à boire rapidement.")
            st.table(alertes[['Quantite', 'Nom', 'Annee', 'Apogee']])
        else:
            st.success("Rien d'urgent !")
