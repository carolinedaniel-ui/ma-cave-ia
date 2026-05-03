import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from github import Github
from datetime import datetime
import io

# Configuration
st.set_page_config(page_title="Ma Cave IA", page_icon="🍷")
st.title("🍷 Ma Cave Intelligente")

# Récupération des secrets
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
except Exception:
    st.error("Les secrets ne sont pas configurés dans Streamlit Cloud.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

def save_to_github(new_data_dict):
    """Enregistre une nouvelle ligne dans le fichier CSV sur GitHub"""
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    contents = repo.get_contents("cave.csv")
    
    # Lecture du CSV actuel
    df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    
    # Ajout de la nouvelle ligne
    new_row = pd.DataFrame([new_data_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Mise à jour sur GitHub
    repo.update_file(contents.path, "Ajout d'une bouteille via Streamlit", df.to_csv(index=False), contents.sha)

# --- INTERFACE ---
photo = st.camera_input("Scanner une étiquette")

if photo:
    base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
    
    if st.button("Analyser et Enregistrer"):
        with st.spinner("L'IA travaille..."):
            # Prompt optimisé pour extraire des données structurées
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyse ce vin. Réponds UNIQUEMENT au format CSV avec ces colonnes: Nom,Maison,Appellation,Annee,Cepages,Note_Vivino,Accords,Apogee. Pas de texte avant ou après."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }]
            )
            
            raw_res = response.choices[0].message.content.replace('"', '').split(',')
            
            # Création du dictionnaire de données
            data = {
                "Date": datetime.now().strftime("%d/%m/%Y"),
                "Nom": raw_res[0],
                "Maison": raw_res[1],
                "Appellation": raw_res[2],
                "Annee": raw_res[3],
                "Cepages": raw_res[4],
                "Note_Vivino": raw_res[5],
                "Accords": raw_res[6],
                "Apogee": raw_res[7]
            }
            
            st.write("### ✅ Résultats trouvés :")
            st.table(pd.DataFrame([data]))
            
            try:
                save_to_github(data)
                st.success("Bouteille ajoutée avec succès au fichier CSV !")
            except Exception as e:
                st.error(f"Erreur lors de la sauvegarde : {e}")

# Affichage de la cave actuelle
if st.checkbox("Voir ma cave"):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    contents = repo.get_contents("cave.csv")
    df_view = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    st.dataframe(df_view)
