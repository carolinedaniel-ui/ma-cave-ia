import streamlit as st
from openai import OpenAI
import base64

# Configuration
st.set_page_config(page_title="Ma Cave IA", page_icon="🍷")
st.title("🍷 Analyseur de Cave")

# --- CONFIGURATION API ---
# Au lieu de : os_api_key = "sk-proj-..."
# On utilise la méthode sécurisée de Streamlit :

import streamlit as st

os_api_key = st.secrets["OPENAI_API_KEY"]

client = OpenAI(api_key=os_api_key)

def encoder_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# --- INTERFACE ---
photo = st.camera_input("Prenez l'étiquette en photo")

if photo:
    st.image(photo, caption="Analyse en cours...")
    
    if st.button("Identifier cette bouteille"):
        base64_image = encoder_image(photo)
        
        with st.spinner("L'IA examine le domaine et le millésime..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Analyse cette étiquette de vin. Donne moi : Nom, Maison, Appellation, Année, Cépages, et 2 idées d'accords mets-vins. Réponds sous forme de liste à puces."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ],
                        }
                    ],
                    max_tokens=300,
                )
                
                resultat = response.choices[0].message.content
                st.markdown("### 📋 Fiche de la bouteille")
                st.write(resultat)
                
                # Petit bouton pour simuler l'enregistrement
                if st.button("Ajouter à ma cave"):
                    st.success("Bouteille enregistrée (virtuellement) !")
                    
            except Exception as e:
                st.error(f"Erreur : {e}")