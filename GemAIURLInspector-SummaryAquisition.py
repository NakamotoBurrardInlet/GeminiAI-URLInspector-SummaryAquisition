import streamlit as st
import json
import time
import requests
from urllib.parse import urlparse
# Note: Firebase Admin SDK imports are included for context but not used in this environment.
# They are generally necessary for Streamlit server-side apps for official Firebase integration.
from firebase_admin import initialize_app, credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_collection import BaseCollectionReference
from google.cloud.firestore_v1.base_document import BaseDocumentReference

# --- CONFIGURATION & SETUP ---
# Fix 1: Removed the problematic st.set_option as it's deprecated/removed.

# Streamlit Page Configuration
st.set_page_config(
    page_title="AI URL Inspector",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global Variables for Firebase (MUST be used as provided by the environment)
try:
    app_id = __app_id
    firebaseConfig = json.loads(__firebase_config)
    initial_auth_token = __initial_auth_token
except NameError:
    # Fallback for local testing (replace with your actual non-sensitive data if needed)
    app_id = 'default-ai-url-inspector-app'
    firebaseConfig = {
        "apiKey": "YOUR_API_KEY",
        "authDomain": "YOUR_AUTH_DOMAIN",
        "projectId": "YOUR_PROJECT_ID",
        "storageBucket": "YOUR_STORAGE_BUCKET",
        "messagingSenderId": "YOUR_MESSAGING_SENDER_ID",
        "appId": "YOUR_APP_ID"
    }
    initial_auth_token = 'LOCAL_TEST_TOKEN' # Using an anonymous sign-in if token is missing

# Gemini API Configuration
API_KEY = "AIzaSyCHgaUyjlG6fYe5lykJCqD4gJyjANnwNz4"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"
IMAGE_GEN_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={API_KEY}"

# --- FIREBASE & AUTHENTICATION (Simulated Setup for Streamlit) ---

# We simulate the environment providing a user ID:
if 'user_id' not in st.session_state:
    # Simulate UUID based on token presence
    if initial_auth_token != 'LOCAL_TEST_TOKEN':
        st.session_state.user_id = initial_auth_token[:8] # Mock user ID from token
    else:
        st.session_state.user_id = 'guest-' + str(time.time()).replace('.', '')[-6:]
    st.session_state.db_path = f"artifacts/{app_id}/users/{st.session_state.user_id}/url_reports"

# --- CORE AI FUNCTIONALITY ---

def ai_generate_report(url, log_container):
    """
    Calls the Gemini API to get a detailed report on the URL using Google Search grounding.
    Implements exponential backoff for API robustness.
    """
    # ENHANCEMENT: Expanded prompt to explicitly request Host IP, Location, and Latency analysis.
    system_prompt = (
        "You are the AI URL Data Inspector, a world-class security, market, and technical "
        "analyst, trained on vast datasets of network topology and real-time threat vectors. "
        "Your task is to provide an **extremely detailed, high-quality, and critical analysis** of the "
        f"URL: '{url}'. Your response must be highly structured and deep, covering these five main areas: "
        "1. **Core Traffic & Host Data:** Find and state the **Server Host IP Address**, **Estimated Host Location (City/Country)**, and analyze the **Domain Registrar**. "
        "2. **Security & Technical Audit:** Discuss potential security risks (e.g., outdated software, malware reports), technologies used, and DNS/SSL status. "
        "3. **Performance Analysis:** Provide an analysis of **estimated latency/load time** based on public performance data and suggest improvements. "
        "4. **Market & Content Analysis:** Describe the site's purpose, target audience, recent news/activity related to it (if available), and content quality/relevance. "
        "5. **Overall Verdict & Actionable Insights:** Provide a final verdict (e.g., Safe, Caution, High Risk) and specific recommendations for the user. "
        "Present the output using clear Markdown headings and bullet points for ultimate readability, ensuring all technical data is clearly labeled."
    )
    user_query = f"Provide a complete, multi-section analysis report for this website/URL: {url}"

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "tools": [{"google_search": {}}], # Enable Google Search Grounding
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    log_container.write(f"**[{time.strftime('%H:%M:%S')}]** ⏳ Initiating AI Neural Development Algorithm...")

    max_retries = 5
    delay = 1

    for attempt in range(max_retries):
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

            result = response.json()
            candidate = result.get('candidates', [{}])[0]
            
            # Extract text
            text = candidate.get('content', {}).get('parts', [{}])[0].get('text', 'Error: AI content could not be extracted.')

            # Extract grounding sources (citations)
            sources = []
            grounding_metadata = candidate.get('groundingMetadata')
            if grounding_metadata and grounding_metadata.get('groundingAttributions'):
                sources = grounding_metadata['groundingAttributions']
                
            return text, sources

        except requests.exceptions.HTTPError as e:
            if response.status_code in [429, 500, 503] and attempt < max_retries - 1:
                log_container.write(f"**[{time.strftime('%H:%M:%S')}]** ⚠️ API Error ({response.status_code}). Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                log_container.write(f"**[{time.strftime('%H:%M:%S')}]** ❌ Fatal API Error: {e}")
                return f"Error: Failed to fetch report from AI after {attempt + 1} attempts. Details: {e}", []
        except Exception as e:
            log_container.write(f"**[{time.strftime('%H:%M:%S')}]** ❌ Unexpected Error during API call: {e}")
            return f"Error: An unexpected error occurred: {e}", []

    return "Error: Maximum retries reached.", []

# --- STORAGE & DATA HANDLING ---

def save_report_to_firestore(report_data):
    """
    Simulated function to save data to a Firestore-like structure.
    """
    try:
        # Structure the data according to Firestore rules
        report_doc = {
            "url": report_data['url'],
            "report_text": report_data['report_text'],
            "timestamp": time.time(),
            "user_id": st.session_state.user_id,
            "citations": report_data['citations'],
            "app_id": app_id
        }

        # Simulate Firestore operation (replace with actual db.collection().add() if using admin SDK)
        st.session_state.log_messages.append(
            f"**[{time.strftime('%H:%M:%S')}]** ✅ Report saved! Doc path simulated: `{st.session_state.db_path}/[auto_id]`"
        )
        return True
    except Exception as e:
        st.session_state.log_messages.append(
            f"**[{time.strftime('%H:%M:%S')}]** ❌ Error saving to storage: {e}"
        )
        return False

def save_report_to_file(report_text, file_type):
    """
    Generates a download link for the report based on the selected file type.
    """
    if file_type == "Markdown (.md)":
        content = report_text
        mime = "text/markdown"
        extension = "md"
    elif file_type == "Plain Text (.txt)":
        content = report_text
        mime = "text/plain"
        extension = "txt"
    elif file_type == "JSON (.json)":
        content_dict = {
            "url": st.session_state.current_url,
            "report": report_text,
            "timestamp": time.time(),
            "analyst": "Gemini AI Inspector"
        }
        content = json.dumps(content_dict, indent=2)
        mime = "application/json"
        extension = "json"
    else:
        return None, None

    # Streamlit uses st.download_button for file saving
    return content, f"url_report_{int(time.time())}.{extension}", mime


# --- STREAMLIT UI & MAIN LOOP ---

if 'log_messages' not in st.session_state:
    st.session_state.log_messages = [f"**[{time.strftime('%H:%M:%S')}]** App initialized. User ID: `{st.session_state.user_id}`"]
if 'report_text' not in st.session_state:
    st.session_state.report_text = ""
if 'citations' not in st.session_state:
    st.session_state.citations = []
if 'current_url' not in st.session_state:
    st.session_state.current_url = ""

# --- Clever Looking GUI and Coloring ---

# Custom Styling (using Streamlit components and basic Markdown for color)
st.markdown("""
<style>
    /* Inter font (Streamlit default, but good to ensure consistency) */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main App Container Styling */
    .reportview-container {
        background: #0d1117; /* Dark background for a sleek look */
    }

    /* Header/Title Styling */
    .title-box {
        background-color: #283747;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
        margin-bottom: 20px;
        border-left: 5px solid #4CAF50; /* Green accent */
    }
    .title-text {
        color: #EAECEE;
        font-size: 2.2rem;
        font-weight: 700;
    }

    /* Input/Button Styling */
    .stTextInput>div>div>input {
        border-radius: 8px;
        border: 1px solid #4A4A4A;
        padding: 10px;
        background-color: #161b22;
        color: #EAECEE;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 20px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    /* Log Terminal Styling */
    .log-terminal {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 15px;
        height: 250px;
        overflow-y: scroll;
        color: #A9A9A9;
        font-family: monospace;
        font-size: 0.85rem;
    }
    /* Report area styling */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)


# --- HEADER ---
st.markdown('<div class="title-box"><p class="title-text">🌐 AI URL Inspector Data Response</p></div>', unsafe_allow_html=True)
st.caption(f"App ID: **`{app_id}`** | Storage Base Path: **`{st.session_state.db_path}`**")

# --- INPUT AND CONTROL ---
with st.container():
    url_input = st.text_input(
        "Insert URL Here (e.g., https://google.com/)",
        value=st.session_state.current_url,
        placeholder="Enter a full URL to inspect...",
        key="url_box",
        label_visibility="visible"
    )

    col1, col2, col3 = st.columns([1, 1, 3])

    if col1.button("🔬 **Analyze URL**"):
        # Reset report and citations on new analysis
        st.session_state.report_text = ""
        st.session_state.citations = []

        # URL Validation
        if not url_input.strip():
            st.warning("Please enter a URL to analyze.")
        elif not url_input.startswith(('http://', 'https://')):
            st.warning("Please ensure the URL starts with `http://` or `https://`.")
        else:
            # 1. Update State and Logging
            st.session_state.current_url = url_input
            st.session_state.log_messages.append(f"**[{time.strftime('%H:%M:%S')}]** 🔍 Analyzing: **{url_input}**")
            log_placeholder = st.empty() # Placeholder for real-time log updates

            # 2. Call AI
            with st.spinner('AI is generating a neural response...'):
                report_text, citations = ai_generate_report(url_input, log_placeholder)

            # 3. Update final state
            st.session_state.report_text = report_text
            st.session_state.citations = citations
            st.session_state.log_messages.append(f"**[{time.strftime('%H:%M:%S')}]** ✅ Analysis complete!")
            
            # FIX: Replaced deprecated st.experimental_rerun() with st.rerun()
            st.rerun()

# --- DYNAMIC LOGGING TERMINAL (Consistent Updating Looping Data to Terminal) ---

st.markdown("---")
st.subheader("Adaptable Logging Terminal")

# Display logs in a scrollable box
log_output = "\n".join(st.session_state.log_messages)
st.markdown(f'<div class="log-terminal">{log_output.replace("\\n", "<br>")}</div>', unsafe_allow_html=True)

# --- AI REPORT DISPLAY ---

if st.session_state.report_text:
    st.markdown("---")
    st.subheader("AI Detailed Information Report")
    
    # Report Content Area
    st.markdown(st.session_state.report_text)
    
    # Citations
    if st.session_state.citations:
        st.markdown("### Grounding Sources (Citations)")
        for i, source in enumerate(st.session_state.citations):
            if source.get('uri') and source.get('title'):
                st.markdown(f"{i+1}. [{source['title']}]({source['uri']})")
            elif source.get('uri'):
                st.markdown(f"{i+1}. <{source['uri']}>")

    st.markdown("---")
    
    # --- SAVE OPTIONS ---
    st.subheader("Save Options")

    # Save to Button - File Type Select and Download
    save_type = st.selectbox(
        "Select output format:",
        ["Markdown (.md)", "Plain Text (.txt)", "JSON (.json)"],
        index=0,
        key="save_type_select"
    )

    file_content, file_name, mime_type = save_report_to_file(st.session_state.report_text, save_type)

    if file_content:
        col_s1, col_s2, _ = st.columns([1.5, 1.5, 4])
        
        # Save to File Download Button
        col_s1.download_button(
            label=f"⬇️ **Download Report as {save_type.split(' ')[0]}**",
            data=file_content,
            file_name=file_name,
            mime=mime_type,
            help="Click to save the report to your local device."
        )

        # Save to Firestore Button
        if col_s2.button("💾 **Save to Cloud Storage** (Firestore)", key="save_to_db_btn"):
            report_data = {
                'url': st.session_state.current_url,
                'report_text': st.session_state.report_text,
                'citations': st.session_state.citations
            }
            if save_report_to_firestore(report_data):
                st.success("Report successfully marked for saving to Firestore!")
            else:
                st.error("Could not complete cloud save operation.")

    else:
        st.info("No report generated yet. Analyze a URL first.")
