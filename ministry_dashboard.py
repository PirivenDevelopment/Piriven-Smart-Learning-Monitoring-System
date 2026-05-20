import streamlit as st
import streamlit.components.v1 as components # 💡 [නව එකතු කිරීම] JS ඔරලෝසුව වැඩ කිරීමට මෙය අනිවාර්යයි
import requests
import folium
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime
import base64
import os
from urllib.parse import urlparse, parse_qs

# ⚠️ Firebase API URL
FIREBASE_URL = "https://pirivensmartboardmonitoring-default-rtdb.asia-southeast1.firebasedatabase.app/"
SRI_LANKA_DISTRICTS = ["Colombo", "Gampaha", "Kalutara", "Kandy", "Matale", "Nuwara Eliya", "Galle", "Matara", "Hambantota", "Jaffna", "Kilinochchi", "Mannar", "Vavuniya", "Mullaitivu", "Batticaloa", "Ampara", "Trincomalee", "Kurunegala", "Puttalam", "Anuradhapura", "Polonnaruwa", "Badulla", "Monaragala", "Ratnapura", "Kegalle"]

def process_youtube_link(url_or_id):
    url_str = url_or_id.strip()
    if "youtube.com" not in url_str and "youtu.be" not in url_str: return {"type": "video", "value": url_str}
    try:
        parsed_url = urlparse(url_str)
        if parsed_url.hostname == 'youtu.be': return {"type": "video", "value": parsed_url.path[1:]}
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com') and parsed_url.path == '/watch': return {"type": "video", "value": parse_qs(parsed_url.query)['v'][0]}
    except: pass
    return {"type": "custom", "value": url_str}

st.set_page_config(page_title="Ministry Admin Dashboard", layout="wide")

col_title, col_clock = st.columns([4, 1])
with col_title:
    st.markdown("<h2 style='color: #1a365d; margin-top: -10px;'>🏛️ Ministry of Education - Piriven Division</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #4a5568; font-size: 14px; font-weight: bold; margin-top: -15px;'>Central Control, Analytics & Monitoring Dashboard</p>", unsafe_allow_html=True)
with col_clock:
    # 💡 [විසඳුම] HTML/JS භාවිත කර සර්වර් වෙලාව වෙනුවට ඩෑෂ්බෝඩ් එක බලන පරිගණකයේ නියම සජීවී වෙලාව (Device Time) පෙන්වීම
    st.markdown("""
        <div id="device-clock" style='background-color: #1e293b; color: #60a5fa; padding: 8px; border-radius: 8px; text-align: center; font-family: monospace; font-size: 14px; font-weight: bold; border: 1px solid #475569;'>
            💻 DEVICE TIME<br><span id="clock-span">Loading...</span>
        </div>
        <script>
            function updateClock() {
                var now = new Date();
                var year = now.getFullYear();
                var month = String(now.getMonth() + 1).padStart(2, '0');
                var day = String(now.getDate()).padStart(2, '0');
                var hours = String(now.getHours()).padStart(2, '0');
                var minutes = String(now.getMinutes()).padStart(2, '0');
                var seconds = String(now.getSeconds()).padStart(2, '0');
                document.getElementById('clock-span').innerText = year + '-' + month + '-' + day + ' ' + hours + ':' + minutes + ':' + seconds;
            }
            setInterval(updateClock, 1000);
            updateClock();
        </script>
    """, unsafe_allow_html=True)

st.write("---")

live_boards_data, cloud_excel_data = {}, None
try:
    live_boards_data = requests.get(f"{FIREBASE_URL}live_boards.json").json() or {}
    cloud_excel_data = requests.get(f"{FIREBASE_URL}ministry_excel_registry.json").json()
except: pass

# Sidebar Registry Management
st.sidebar.header("📁 Data Source Setup")
uploaded_file = st.sidebar.file_uploader("Upload Piriven Excel Registry (.xlsx)", type=["xlsx"])
df_usage = None

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip()
        df_raw["Census No"] = df_raw["Census No"].fillna("").astype(str).str.strip().apply(lambda x: x.split('.')[0] if '.' in x else x)
        df_raw["Piriven Name"] = df_raw["Piriven Name"].fillna("").astype(str).str.strip()
        df_raw["District"] = df_raw["District"].fillna("").astype(str).str.strip().str.title() 
        df_raw["Latitude"] = df_raw["Latitude"].fillna(0.0); df_raw["Longitude"] = df_raw["Longitude"].fillna(0.0)
        df_raw["Monthly Usage (Hours)"] = df_raw["Monthly Usage (Hours)"].fillna(0)

        for index, row in df_raw.iterrows():
            lat, lon = float(row.get("Latitude", 0.0)), float(row.get("Longitude", 0.0))
            if lat > 70.0 and lon < 15.0: df_raw.at[index, "Latitude"], df_raw.at[index, "Longitude"] = lon, lat

        df_temp = pd.DataFrame()
        df_temp["Census No"], df_temp["Piriven Name"], df_temp["Latitude"], df_temp["Longitude"], df_temp["Monthly Usage (Hours)"] = df_raw["Census No"], df_raw["Piriven Name"], df_raw["Latitude"], df_raw["Longitude"], df_raw["Monthly Usage (Hours)"]
        df_temp["District"] = [([d for d in SRI_LANKA_DISTRICTS if d.lower() == x.lower()] + ["Other/Unclassified"])[0] for x in df_raw["District"]]
        df_temp["Zone"] = df_temp["District"]
        
        requests.put(f"{FIREBASE_URL}ministry_excel_registry.json", json=df_temp.to_dict(orient="records"))
        df_usage = df_temp.copy(); st.sidebar.success("✅ Excel Saved to Cloud!")
    except Exception as e: st.sidebar.error(f"Error: {e}")

if df_usage is None and cloud_excel_data:
    df_usage = pd.DataFrame(cloud_excel_data)
    df_usage["Census No"] = df_usage["Census No"].astype(str).str.strip().apply(lambda x: x.split('.')[0] if '.' in x else x)
    df_usage["District"] = df_usage["District"].astype(str).str.strip().str.title(); st.sidebar.info("☁️ Registry Loaded from Cloud")

if df_usage is None: df_usage = pd.DataFrame({"Census No": ["0542"], "Piriven Name": ["Sample"], "District": ["Colombo"], "Latitude": [6.9271], "Longitude": [79.8612], "Monthly Usage (Hours)": [0]})

def is_device_actually_active(last_ping_str):
    try:
        if last_ping_str and (datetime.datetime.now() - datetime.datetime.strptime(last_ping_str, "%Y-%m-%d %H:%M:%S")).total_seconds() < 600: return True
    except: pass
    return False

live_census_list = []
for c_id, devices in live_boards_data.items():
    if isinstance(devices, dict):
        for d_id, d_info in devices.items():
            if d_id != "attendance" and isinstance(d_info, dict) and is_device_actually_active(d_info.get("last_ping")):
                live_census_list.append(str(c_id).strip()); break

df_usage["Status"] = ["Active" if str(row["Census No"]).strip() in live_census_list else "Offline" for i, row in df_usage.iterrows()]
census_to_name = dict(zip(df_usage["Census No"].astype(str), df_usage["Piriven Name"]))

# Filters
st.sidebar.write("---")
selected_district = st.sidebar.selectbox("Select District:", ["All Island"] + sorted([d for d in df_usage["District"].unique().tolist() if d and d != "Nan"]))
df_step1 = df_usage[df_usage["District"] == selected_district] if selected_district != "All Island" else df_usage.copy()
selected_piriven = st.sidebar.selectbox("Select Piriven Name:", ["All Piriven"] + sorted(df_step1["Piriven Name"].unique().tolist()))
df_filtered = df_step1[df_step1["Piriven Name"] == selected_piriven] if selected_piriven != "All Piriven" else df_step1.copy()

tab1, tab2, tab3 = st.tabs(["🗺️ Live Map & Remote Control", "📊 Analytics & Usage Stats", "🛠️ Support Tickets & Live Chat"])

with tab2:
    st.subheader("📊 Performance Analytics")
    c_left, c_middle, c_right = st.columns(3)
    c_left.metric("Registered Boards", len(df_filtered))
    total_active_devices = 0; filtered_census_nos = df_filtered["Census No"].astype(str).tolist()
    for c_no in filtered_census_nos:
        if c_no in live_boards_data and isinstance(live_boards_data[c_no], dict):
            for dev_id, dev_info in live_boards_data[c_no].items():
                if dev_id != "attendance" and isinstance(dev_info, dict) and is_device_actually_active(dev_info.get("last_ping")): total_active_devices += 1
    c_middle.metric("Total Active Devices Now", total_active_devices)
    st.dataframe(df_filtered.drop(columns=["Latitude", "Longitude"], errors="ignore"), use_container_width=True)

# Map Logics
map_center = [7.8731, 80.7718]; map_zoom = 8
if selected_piriven != "All Piriven" and not df_filtered.empty and float(df_filtered.iloc[0].get("Latitude", 0.0)) != 0.0:
    map_center, map_zoom = [float(df_filtered.iloc[0]["Latitude"]), float(df_filtered.iloc[0]["Longitude"])], 14

with tab1:
    col_map, col_ctrl = st.columns([3, 2])
    with col_map:
        m = folium.Map(location=map_center, zoom_start=map_zoom)
        for i, r in df_filtered.iterrows():
            c_no = str(r["Census No"]).strip(); is_any_device_live = False
            if c_no in live_boards_data and isinstance(live_boards_data[c_no], dict):
                for dev_id, dev_info in live_boards_data[c_no].items():
                    if dev_id != "attendance" and isinstance(dev_info, dict) and is_device_actually_active(dev_info.get("last_ping")):
                        is_any_device_live = True
                        adv_spec = dev_info.get("spec_advanced", {})
                        popup_html = f"<b>🏛️ {r['Piriven Name']}</b><br>📟 {dev_info.get('device_type')} ({dev_id})<br>🧠 Specs: {adv_spec.get('processor','N/A')} | {adv_spec.get('ram','N/A')}"
                        folium.Marker([dev_info.get("live_lat", r["Latitude"]), dev_info.get("live_lon", r["Longitude"])], popup=popup_html, icon=folium.Icon(color="green" if dev_info.get('device_type')=="Smart Board" else "blue")).add_to(m)
            if not is_any_device_live and r["Latitude"] != 0: folium.Marker([r["Latitude"], r["Longitude"]], popup=f"🏛️ {r['Piriven Name']}<br>🔴 Offline", icon=folium.Icon(color="red")).add_to(m)
        st_folium(m, width=700, height=550, key=f"map_{selected_district}_{selected_piriven}")
    with col_ctrl:
        st.subheader("📢 Command Center")
        yt_input = st.text_input("YouTube URL:")
        if st.button("🚀 BROADCAST TO ALL BOARDS") and yt_input: requests.put(f"{FIREBASE_URL}current_lesson.json", json=process_youtube_link(yt_input)); st.success("Broadcasted!")
        st.write("---")
        ann_t, ann_b = st.text_input("Announcement Title:"), st.text_area("Message Body:")
        if st.button("📢 PUSH LIVE NOTIFICATION") and ann_t and ann_b: requests.put(f"{FIREBASE_URL}latest_announcement.json", json={"title": ann_t, "body": ann_b}); st.success("Pushed!")

# Support Ticket Controls
with tab3:
    st.subheader("🛠️ Ticket Desk & Private Chat Panel")
    try:
        t_data = requests.get(f"{FIREBASE_URL}support_tickets.json", timeout=4).json()
        if t_data:
            for tid, det in t_data.items():
                c_no = str(det.get("census_no", "")).strip()
                p_name = census_to_name.get(c_no, f"Unknown ({c_no})")
                if selected_piriven != "All Piriven" and p_name != selected_piriven: continue
                
                with st.expander(f"🏛️ {p_name} - [{det.get('issue_type')}] (⏱️ {det.get('reported_at', 'N/A')}) - Status: {det.get('status')}"):
                    st.markdown(f"**📝 Description:** {det.get('description')}")
                    st.caption(f"Serial: {det.get('device_serial')} | ID: {tid}")
                    st.write("---")
                    chats = det.get("chats", {})
                    if chats:
                        for cid, cmsg in chats.items(): st.markdown(f"**{'🏛️ Ministry' if cmsg.get('sender')=='ministry' else '🏫 Piriven'}:** {cmsg.get('msg')} *<small>({cmsg.get('time')[11:16]})</small>*", unsafe_allow_html=True)
                    chat_input = st.text_input("Type response / පිළිතුර ලියන්න:", key=f"chat_in_{tid}")
                    if st.button("↩️ Send Message", key=f"send_btn_{tid}") and chat_input:
                        requests.post(f"{FIREBASE_URL}support_tickets/{tid}/chats.json", json={"sender": "ministry", "msg": chat_input, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                        st.rerun()
                    if det.get('status') == "Pending":
                        if st.button("Mark as Solved ✅", key=f"sol_{tid}"): requests.patch(f"{FIREBASE_URL}support_tickets/{tid}.json", json={"status": "Solved"}); st.rerun()
        else: st.info("No tickets.")
    except Exception as e: st.error(f"Error: {e}")
