import sys
import requests
import streamlit as st
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime
import base64
import os
import smtplib
import hashlib
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from urllib.parse import urlparse, parse_qs

# ⚠️ Firebase API URL
FIREBASE_URL = "https://pirivensmartboardmonitoring-default-rtdb.asia-southeast1.firebasedatabase.app/"

# ලංකාවේ නිල දිස්ත්‍රික්ක 25
SRI_LANKA_DISTRICTS = [
    "Colombo", "Gampaha", "Kalutara", "Kandy", "Matale", "Nuwara Eliya", 
    "Galle", "Matara", "Hambantota", "Jaffna", "Kilinochchi", "Mannar", 
    "Vavuniya", "Mullaitivu", "Batticaloa", "Ampara", "Trincomalee", 
    "Kurunegala", "Puttalam", "Anuradhapura", "Polonovaruwa", "Badulla", 
    "Monaragala", "Ratnapura", "Kegalle"
]

# 💡 ආරක්ෂිත එන්ජින්
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

def get_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

def convert_hours_to_hm_string(decimal_hours):
    try:
        hours = int(decimal_hours)
        minutes = int(round((decimal_hours - hours) * 60))
        return f"{hours}h : {minutes:02d}m"
    except: return "0h : 00m"

# 🔐 Login Logic
def check_admin_login(user, pwd):
    if user == "admin" and make_hashes(pwd) == "7757ee92a17058be91a134bf47738f711202e864ee91d8b7b25e11f7c32bf17b":
        st.session_state["user_role"] = "super_admin"
        return True
    try:
        res = requests.get(f"{FIREBASE_URL}system_admins/{user}.json", timeout=4)
        if res.status_code == 200 and res.json():
            if make_hashes(pwd) == res.json().get("password_hash"):
                st.session_state["user_role"] = "standard_admin"
                return True
    except: pass
    return False

def create_new_admin_user(new_user, new_pwd):
    try:
        check_res = requests.get(f"{FIREBASE_URL}system_admins/{new_user}.json", timeout=3)
        if check_res.status_code == 200 and check_res.json(): return "exists"
        pwd_hash = make_hashes(new_pwd)
        user_node = {"username": new_user, "password_hash": pwd_hash, "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        res = requests.put(f"{FIREBASE_URL}system_admins/{new_user}.json", json=user_node, timeout=3)
        return "success" if res.status_code == 200 else "error"
    except: return "error"

def is_device_actually_active(last_ping_str):
    try:
        if not last_ping_str: return False
        last_ping_time = datetime.datetime.strptime(last_ping_str, "%Y-%m-%d %H:%M:%S")
        srilanka_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
        return (srilanka_now - last_ping_time).total_seconds() < 600
    except: return False

# --- UI ආරම්භය ---
st.set_page_config(page_title="Ministry Admin Dashboard", layout="wide")

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "user_role" not in st.session_state: st.session_state["user_role"] = "standard_admin"

if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center;'>🏛️ Ministry Admin Portal</h2>", unsafe_allow_html=True)
    u = st.text_input("Username").strip().lower()
    p = st.text_input("Password", type="password")
    if st.button("🔑 LOGIN"):
        if check_admin_login(u, p):
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = u
            st.rerun()
    st.stop()

# --- ප්‍රධාන ඩෑෂ්බෝඩ් එක ---
st.title("🏛️ Central Monitoring Dashboard")
if st.button("🔒 LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# දත්ත ලබා ගැනීම
reg_data = requests.get(f"{FIREBASE_URL}ministry_excel_registry.json").json() or []
df = pd.DataFrame(reg_data)

tabs = st.tabs(["🗺️ Live Map", "📊 Analytics & Leaderboard", "📝 Manage Users"])

with tabs[1]:
    st.subheader("📊 Performance Analytics")
    if not df.empty:
        # Leaderboard දත්ත සැකසීම
        df["Usage (Minutes)"] = df.get("Monthly Usage (Hours)", 0) * 60
        df_top10 = df.sort_values(by="Usage (Minutes)", ascending=False).head(10)
        
        st.bar_chart(df_top10.set_index("Piriven Name")["Usage (Minutes)"])
        
        # Excel ඩවුන්ලෝඩ් බොත්තම් දෙකම නිවැරදිව
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download Leaderboard (.xlsx)", 
                get_excel_bytes(df_top10), 
                "Top_10_Piriven.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col2:
            st.download_button(
                "📥 Download Full Registry (.xlsx)", 
                get_excel_bytes(df), 
                "Full_Registry.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

with tabs[0]:
    st.subheader("🗺️ Live Tracking Map")
    m = folium.Map(location=[7.8731, 80.7718], zoom_start=8)
    st_folium(m, width=800, height=500)

with tabs[2]:
    if st.session_state["user_role"] == "super_admin":
        st.subheader("📝 Manage Users")
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        if st.button("Create Admin"):
            create_new_admin_user(nu, np)
            st.success("User Created!")
