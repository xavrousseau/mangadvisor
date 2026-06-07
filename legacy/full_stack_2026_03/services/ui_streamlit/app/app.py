import os
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.title("Mangadvisor — V1 (Stack check)")

st.write("But : vérifier que l'UI parle bien à l'API.")

if st.button("Tester /health API"):
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=5)
        st.success(r.json())
    except Exception as e:
        st.error(str(e))

st.caption(f"API_BASE_URL = {API_BASE_URL}")