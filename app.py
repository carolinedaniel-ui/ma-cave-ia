import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from github import Github
from datetime import datetime
import io

# Config
st.set_page_config(page_title="Ma Cave", page_icon="🍷")

# Secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
except:
    st.error("Configuration des secrets manquante.")
    st.stop()

def save_to_github(dict_data):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    contents = repo.get_contents("cave.csv")
    df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    new_row = pd.DataFrame([dict_data])
    df = pd.concat([df, new_row], ignore_index=True)
    repo.update_file(contents.path, f"Ajout {dict_data['Nom']}", df.to_csv(index=False), contents.sha)

st.title("🍷 Ma Cave Perso")

# Utilisation de l'appareil photo ARRIÈRE
photo = st.camera_input("Scanner l'étiquette", label_visibility="collapsed")

if photo:
    # --- ÉTAPE 1 : ANALYSE ---
    if "vin_info" not in st.session_state:
        with st.spinner("L'IA déchiffre l'étiquette..."):
            base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyse ce vin. Donne les infos séparées par des points-virgules (;) dans cet ordre exact: Nom;Maison;Appellation;Annee;Cepages;Note_Vivino;Accords;Apogee. Ne mets aucun autre texte."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }]
            )
            # Nettoyage du texte pour éviter les bugs de format
            clean_res = response.choices[0].message.content.replace("`", "").replace("csv", "").strip().split(";")
            
            st.session_state.vin_info = {
                "Date": datetime.now().strftime("%d/%m/%Y"),
                "Nom": clean_res[0], "Maison": clean_res[1], "Appellation": clean_res[2],
                "Annee": clean_res[3], "Cepages": clean_res[4], "Note_Vivino": clean_res[5],
                "Accords": clean_res[6], "Apogee": clean_res[7]
            }

    # Affichage des résultats pour validation
    if "vin_info" in st.session_state:
        st.success("Bouteille identifiée !")
        res = st.session_state.vin_info
        
        # Formulaire modifiable avant enregistrement
        col1, col2 = st.columns(2)
        with col1:
            res['Nom'] = st.text_input("Nom", res['Nom'])
            res['Annee'] = st.text_input("Année", res['Annee'])
        with col2:
            res['Maison'] = st.text_input("Maison", res['Maison'])
            res['Apogee'] = st.text_input("Apogée", res['Apogee'])

        # --- ÉTAPE 2 : ENREGISTREMENT ---
        if st.button("💾 Confirmer l'ajout à la cave"):
            save_to_github(res)
            st.balloons()
            del st.session_state.vin_info # Réinitialise pour la prochaine photo
            st.success("Enregistré dans le fichier CSV !")

# Visualisation
if st.checkbox("Consulter l'inventaire"):
    # ... (code identique pour lire le CSV)
