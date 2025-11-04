import streamlit as st
import pandas as pd
import random
import re
from datetime import datetime

# ---------- CONFIG ----------
ROLES = ["responsable", "arbitre1", "arbitre2", "table1", "table2"]
TEAM1_KEYS = [r"SG1", r"SG 1", r"Equipe 1", r"Équipe 1", r"Equipe1", r"\b1\b"]
SPECIAL_PERSON = "Matteo Bompas"
MATTEO_ALLOWED_SAT_TIME = "21:00"

# ---------- Fonctions ----------
def is_team1_match(match_name):
    for k in TEAM1_KEYS:
        if re.search(k, match_name, flags=re.IGNORECASE):
            return True
    return False

def is_matteo_available(slot_time, day, name):
    if name != SPECIAL_PERSON:
        return True
    if day.lower().startswith("sam"):
        try:
            tslot = datetime.strptime(slot_time,"%H:%M").time()
            tallow = datetime.strptime(MATTEO_ALLOWED_SAT_TIME,"%H:%M").time()
            return tslot >= tallow
        except:
            return False
    return True

def assign_slots(names_df, slots_df):
    names_list = names_df['name'].tolist()
    capabilities = {n: set(names_df[names_df['name']==n]['role'].iloc[0].split(';')) if 'role' in names_df.columns else set(["responsable","arbitre","table"]) for n in names_list}
    assign_counts = {(n,r):0 for n in names_list for r in ROLES}
    results = []

    for idx, slot in slots_df.iterrows():
        row = slot.to_dict()
        row.update({r:"" for r in ROLES})

        # Matches avec arbitres officiels
        if is_team1_match(str(slot['match'])):
            row["arbitre1"] = "OFFICIEL"
            row["arbitre2"] = "OFFICIEL"

        for r in ROLES:
            if r in ("arbitre1","arbitre2") and row[r]=="OFFICIEL":
                continue

            need_role = "responsable" if r=="responsable" else ("arbitre" if r.startswith("arbitre") else "table")
            eligibles = []

            for n in names_list:
                if need_role not in capabilities[n]:
                    continue
                if not is_matteo_available(row['time'], row['day'], n):
                    continue
                if n in row.values():
                    continue
                if 'unavailable' in slot and pd.notna(slot['unavailable']):
                    unavailable_list = [x.strip() for x in str(slot['unavailable']).split(';')]
                    if n in unavailable_list:
                        continue
                eligibles.append(n)

            if not eligibles:
                row[r] = "AFFECTER"
            else:
                eligibles.sort(key=lambda nm: (assign_counts[(nm,r)], random.random()))
                chosen = eligibles[0]
                row[r] = chosen
                assign_counts[(chosen,r)] += 1

        results.append(row)

    return pd.DataFrame(results)

# ---------- Streamlit UI ----------
st.title("Planning d'Arbitrage Avancé")

st.header("1️⃣ Importer la liste des personnes")
uploaded_names = st.file_uploader("CSV des personnes (colonnes : name, role optionnel, ex : 'responsable;arbitre')", type="csv")
if uploaded_names:
    names_df = pd.read_csv(uploaded_names)
    st.write("Aperçu des personnes :", names_df)

st.header("2️⃣ Importer les créneaux")
uploaded_slots = st.file_uploader("CSV des créneaux (colonnes : day, time, match, unavailable optionnel)", type="csv")
if uploaded_slots:
    slots_df = pd.read_csv(uploaded_slots)
    st.write("Aperçu des créneaux :", slots_df)

if uploaded_names and uploaded_slots:
    if st.button("Générer le planning"):
        assigned_df = assign_slots(names_df, slots_df)
        st.success("Planning généré !")
        st.dataframe(assigned_df)
        csv = assigned_df.to_csv(index=False).encode("utf-8")
        st.download_button("Télécharger le planning CSV", data=csv, file_name="planning_advanced.csv", mime="text/csv")
