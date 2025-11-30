# app_with_spinner.py

import streamlit as st
from openai import OpenAI
import tempfile
from pathlib import Path
import json
import pandas as pd
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import pgeocode
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Function to load Google Sheet
def load_private_google_sheet(sheet_name: str, worksheet_name: str = None):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(worksheet_name) if worksheet_name else sheet.sheet1
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

st.set_page_config(page_title="Assisted Living Locator", layout="wide")
st.title("Assisted Living Community Recommender")

if "step" not in st.session_state:
    st.session_state.step = "upload"

if "audio_files" not in st.session_state:
    st.session_state.audio_files = None

api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")

if st.session_state.step == "upload":
    st.header("Step 1: Upload Audio File")
    uploaded = st.file_uploader("Upload audio file", type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"])
    if uploaded:
        st.session_state.audio_files = uploaded
        st.session_state.step = "transcribe"
        st.rerun()

elif st.session_state.step == "transcribe":
    st.header("Step 2: Transcribing Audio...")
    if not api_key:
        st.warning("Please enter your OpenAI API Key.")
        st.stop()
    try:
        with st.spinner("Transcribing audio with Whisper..."):
            client = OpenAI(api_key=api_key)
            audio_file = st.session_state.audio_files
            file_ext = audio_file.name.split('.')[-1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                tmp.write(audio_file.getbuffer())
                temp_path = tmp.name
            with open(temp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            Path(temp_path).unlink()
        st.session_state.transcription = transcript.text
        st.success("Transcription complete!")
        st.text_area("Transcribed Text:", transcript.text)
        st.session_state.step = "preferences"
        st.rerun()
    except Exception as e:
        st.error(f"Transcription Error: {e}")

elif st.session_state.step == "preferences":
    st.header("Step 3: Extracting Preferences...")
    try:
        with st.spinner("Extracting preferences using GPT-4..."):
            client = OpenAI(api_key=api_key)
            system_prompt = """Extract structured JSON with:
            name_of_patient, age_of_patient, injury_or_reason,
            primary_contact_information, mentally, care_level,
            preferred_location, enhanced, enriched, move_in_window,
            max_budget, pet_friendly, tour_availability,
            other_keywords."""
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": st.session_state.transcription},
                ],
            )
            prefs = json.loads(response.choices[0].message.content)
            st.session_state.preferences = prefs
            st.json(prefs)
        st.session_state.step = "rank"
        st.rerun()
    except Exception as e:
        st.error(f"Preference Extraction Error: {e}")

elif st.session_state.step == "rank":
    st.header("Step 4: Ranking Communities...")
    try:
        prefs = st.session_state.preferences
        with st.spinner("Loading community data from Google Sheet..."):
            df = load_private_google_sheet("Living_Locators_Data", "Rochester")
        st.write(f"Loaded {len(df)} communities.")

        with st.spinner("Filtering based on preferences..."):
            if prefs.get("care_level"):
                df = df[df["Type of Service"].str.contains(prefs["care_level"], case=False, na=False)]
            if prefs.get("enhanced") == "Yes":
                df = df[df["Enhanced"].astype(str).str.lower() == "yes"]
            if prefs.get("enriched") == "Yes":
                df = df[df["Enriched"].astype(str).str.lower() == "yes"]
            if prefs.get("max_budget"):
                df["Monthly Fee"] = pd.to_numeric(df["Monthly Fee"], errors="coerce")
                df = df[df["Monthly Fee"] <= prefs["max_budget"]]

        with st.spinner("Assigning priority level..."):
            def assign_priority(row):
                c = str(row.get("Contract (w rate)?", "")).strip().lower()
                p = str(row.get("Work with Placement?", "")).strip().lower()
                if c not in ["no", "", "nan"]:
                    return 1
                if c == "no" and p == "yes":
                    return 2
                return 3
            df["Priority_Level"] = df.apply(assign_priority, axis=1)

        with st.spinner("Calculating distances..."):
            geolocator = Nominatim(user_agent="assisted_living_locator_v1")
            client_locations = prefs.get("preferred_location", ["Rochester, NY"])
            if isinstance(client_locations, str):
                client_locations = [client_locations]
            client_coords_list = []
            for loc in client_locations:
                try:
                    geo = geolocator.geocode(loc)
                    if geo:
                        client_coords_list.append((geo.latitude, geo.longitude))
                    time.sleep(1)
                except:
                    pass
            if not client_coords_list:
                client_coords_list = [(43.1566, -77.6088)]
            zip_col = next((c for c in df.columns if "zip" in c.lower()), None)
            def get_coords(row):
                if zip_col:
                    zip_code = row.get(zip_col)
                    if pd.notna(zip_code):
                        try:
                            loc = geolocator.geocode(f"{int(float(zip_code)):05d}, NY")
                            time.sleep(1)
                            if loc:
                                return (loc.latitude, loc.longitude)
                        except:
                            pass
                return None
            df["Community_Coords"] = df.apply(get_coords, axis=1)
            def compute_distance(coords):
                if coords is None:
                    return None
                try:
                    return min(geodesic(coords, c).miles for c in client_coords_list)
                except:
                    return None
            df["Distance_miles"] = df["Community_Coords"].apply(compute_distance)

        with st.spinner("Adding city and state info..."):
            nomi = pgeocode.Nominatim("us")
            if zip_col:
                df["Town"] = df[zip_col].apply(
                    lambda z: nomi.query_postal_code(str(int(float(z))).zfill(5)).place_name
                    if pd.notna(z) else None
                )
                df["State"] = df[zip_col].apply(
                    lambda z: nomi.query_postal_code(str(int(float(z))).zfill(5)).state_code
                    if pd.notna(z) else None
                )

        with st.spinner("Sorting results..."):
            df = df.sort_values(by=["Priority_Level", "Distance_miles"], ascending=[True, True])
        st.session_state.results = df
        st.session_state.step = "results"
        st.rerun()
    except Exception as e:
        st.error(f"Ranking Error: {e}")

elif st.session_state.step == "results":
    st.header("Step 5: Recommended Communities")
    df = st.session_state.results
    st.write(df)
    st.download_button("Download Results as CSV", data=df.to_csv(index=False), file_name="recommendations.csv", mime="text/csv")
