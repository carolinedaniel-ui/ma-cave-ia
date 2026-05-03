import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Ma Cave", page_icon="🍷", layout="centered")

# --- CHARGEMENT DES SECRETS ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
except Exception:
    st.error("Erreur : Les secrets ne sont pas configurés dans Streamlit Cloud.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# --- FONCTION DE SAUVEGARDE ---
def save_to_github(dict_data):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        contents = repo.get_contents("cave.csv")
        
        # Lecture et mise à jour du CSV
        df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
        new_row = pd.DataFrame([dict_data])
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Envoi vers GitHub
        repo.update_file(
            contents.path, 
            f"Ajout de {dict_data['Nom']}", 
            df.to_csv(index=False), 
            contents.sha
        )
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# --- INTERFACE UTILISATEUR ---
st.title("🍷 Ma Cave Intelligente")
st.markdown("---")

# Capture de la photo
# Note : Sur mobile, cela propose généralement le choix de la caméra
photo = st.camera_input("Scanner une étiquette")

if photo:
    # On utilise le 'session_state' pour ne pas relancer l'IA à chaque clic sur un bouton
    if "vin_info" not in st.session_state:
        with st.spinner("Analyse de l'étiquette par l'IA..."):
            base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
            
            # Appel à GPT-4o avec un formatage strict
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Analyse ce vin. Donne les infos séparées par des points-virgules (;) SANS AUCUN AUTRE TEXTE, ni balise, ni introduction, dans cet ordre : Nom;Maison;Appellation;Annee;Cepages;Note_Vivino;Accords;Apogee"
                        },
                        {
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }]
            )
            
            # Nettoyage profond de la réponse pour éviter les bugs CSV
            raw_text = response.choices[0].message.content
            clean_text = raw_text.replace("`", "").replace("csv", "").replace("\n", "").strip()
            infos = clean_text.split(";")
            
            # Stockage temporaire dans la session
            st.session_state.vin_info = {
                "Date": datetime.now().strftime("%d/%m/%Y"),
                "Nom": infos[0] if len(infos) > 0 else "Inconnu",
                "Maison": infos[1] if len(infos) > 1 else "Inconnue",
                "Appellation": infos[2] if len(infos) > 2 else "Inconnue",
                "Annee": infos[3] if len(infos) > 3 else "N.C",
                "Cepages": infos[4] if len(infos) > 4 else "N.C",
                "Note_Vivino": infos[5] if len(infos) > 5 else "N.C",
                "Accords": infos[6] if len(infos) > 6 else "N.C",
                "Apogee": infos[7] if len(infos) > 7 else "N.C"
            }

    # --- ÉTAPE DE VALIDATION ---
    if "vin_info" in st.session_state:
        st.subheader("📝 Vérification des données")
        vin = st.session_state.vin_info
        
        # Champs modifiables
        col1, col2 = st.columns(2)
        with col1:
            vin["Nom"] = st.text_input("Nom du vin", vin["Nom"])
            vin["Annee"] = st.text_input("Millésime", vin["Annee"])
            vin["Appellation"] = st.text_input("Appellation", vin["Appellation"])
        with col2:
            vin["Maison"] = st.text_input("Domaine / Maison", vin["Maison"])
            vin["Apogee"] = st.text_input("Consommer avant", vin["Apogee"])
            vin["Note_Vivino"] = st.text_input("Note estimée", vin["Note_Vivino"])
        
        vin["Accords"] = st.text_area("Accords suggérés", vin["Accords"])

        # Bouton d'enregistrement final
        if st.button("💾 Confirmer et Ajouter à ma cave"):
            if save_to_github(vin):
                st.balloons()
                st.success(f"Bravo ! Le {vin['Nom']} est enregistré.")
                # On vide la session pour le prochain scan
                del st.session_state.vin_info
                # Petit bouton pour rafraîchir proprement
                st.button("Scanner une autre bouteille")

st.markdown("---")

# --- CONSULTATION DE LA CAVE ---
if st.checkbox("📊 Afficher ma cave actuelle"):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        contents = repo.get_contents("cave.csv")
        df_view = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
        st.dataframe(df_view.sort_index(ascending=False))
    except:
        st.info("Le fichier cave.csv est vide ou introuvable.")

# Masquer le menu Streamlit pour faire plus "App"
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_style, unsafe_allow_html=True)
