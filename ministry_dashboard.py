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

# ලංකාවේ නිල දිස්ත්‍රික්ක 25
SRI_LANKA_DISTRICTS = [
    "Colombo", "Gampaha", "Kalutara", "Kandy", "Matale", "Nuwara Eliya", 
    "Galle", "Matara", "Hambantota", "Jaffna", "Kilinochchi", "Mannar", 
    "Vavuniya", "Mullaitivu", "Batticaloa", "Ampara", "Trincomalee", 
    "Kurunegala", "Puttalam", "Anuradhapura", "Polonnaruwa", "Badulla", 
    "Monaragala", "Ratnapura", "Kegalle"
]

def process_youtube_link(url_or_id):
    url_str = url_or_id.strip()
    if "youtube.com" not in url_str and "youtu.be" not in url_str: return {"type": "video", "value": url_str}
    try:
        parsed_url = urlparse(url_str)
        if "list=" in url_str: return {"type": "playlist", "value": url_str}
        if "/c/" in url_str or "/channel/" in url_str or "/@" in url_str or "user/" in url_str: return {"type": "channel", "value": url_str}
        if parsed_url.hostname == 'youtu.be': return {"type": "video", "value": parsed_url.path[1:]}
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                p = parse_qs(parsed_url.query)
                return {"type": "video", "value": p['v'][0]}
    except: pass
    return {"type": "custom", "value": url_str}

st.set_page_config(page_title="Ministry Admin Dashboard", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 8px 8px 0px 0px;
        padding: 10px 20px; font-weight: bold; color: #475569;
    }
    .stTabs [aria-selected="true"] { background-color: #1e293b !important; color: white !important; }
    div[data-testid="stMetricValue"] { color: #1e293b; font-size: 28px; font-weight: bold; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# [Compact Header]
st.markdown("<h2 style='text-align: center; color: #1a365d; margin-top: -30px; margin-bottom: 0px;'>🏛️ Ministry of Education - Piriven Division</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #4a5568; font-size: 16px; font-weight: bold; margin-top: 0px; margin-bottom: -10px;'>Central Control, Analytics & Monitoring Dashboard</p>", unsafe_allow_html=True)
st.write("---")

live_boards_data, cloud_excel_data = {}, None
try:
    res1 = requests.get(f"{FIREBASE_URL}live_boards.json")
    if res1.status_code == 200: live_boards_data = res1.json() or {}
    res2 = requests.get(f"{FIREBASE_URL}ministry_excel_registry.json")
    if res2.status_code == 200: cloud_excel_data = res2.json()
except: pass

# Sidebar
st.sidebar.header("📁 Data Source Setup")
uploaded_file = st.sidebar.file_uploader("Upload Piriven Excel Registry (.xlsx)", type=["xlsx"])
df_usage = None

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip()
        df_raw["Census No"] = df_raw["Census No"].fillna("").astype(str).str.strip()
        df_raw["Piriven Name"] = df_raw["Piriven Name"].fillna("").astype(str).str.strip()
        df_raw["District"] = df_raw["District"].fillna("").astype(str).str.strip()
        df_raw["Zone"] = df_raw["Zone"].fillna("").astype(str).str.strip() if "Zone" in df_raw.columns else df_raw["District"]
        df_raw["Latitude"] = df_raw["Latitude"].fillna(0.0)
        df_raw["Longitude"] = df_raw["Longitude"].fillna(0.0)
        df_raw["Monthly Usage (Hours)"] = df_raw["Monthly Usage (Hours)"].fillna(0)

        df_temp = pd.DataFrame()
        df_temp["Census No"], df_temp["Piriven Name"] = df_raw["Census No"], df_raw["Piriven Name"]
        df_temp["District"] = [([d for d in SRI_LANKA_DISTRICTS if d.lower() == x.lower().capitalize()] + ["Other/Unclassified"])[0] for x in df_raw["District"]]
        df_temp["Zone"], df_temp["Latitude"], df_temp["Longitude"], df_temp["Monthly Usage (Hours)"] = df_raw["Zone"], df_raw["Latitude"], df_raw["Longitude"], df_raw["Monthly Usage (Hours)"]
        
        requests.put(f"{FIREBASE_URL}ministry_excel_registry.json", json=df_temp.to_dict(orient="records"))
        df_usage = df_temp.copy()
        st.sidebar.success("✅ Excel Saved to Cloud!")
    except Exception as e: st.sidebar.error(f"Error: {e}")

if df_usage is None and cloud_excel_data:
    df_usage = pd.DataFrame(cloud_excel_data)
    st.sidebar.info("☁️ Registry Loaded from Cloud")

if df_usage is None:
    df_usage = pd.DataFrame({"Census No": ["0542"], "Piriven Name": ["Sample Pirivena"], "District": ["Colombo"], "Zone": ["Central"], "Status": ["Offline"], "Latitude": [6.9271], "Longitude": [79.8612], "Monthly Usage (Hours)": [0]})

live_census_list = [str(k).strip() for k in live_boards_data.keys()]
df_usage["Status"] = ["Active" if str(row["Census No"]).strip() in live_census_list else "Offline" for i, row in df_usage.iterrows()]
census_to_name = dict(zip(df_usage["Census No"].astype(str), df_usage["Piriven Name"]))

# Filters
st.sidebar.write("---")
st.sidebar.header("🔍 Live Filters")
dist_list = ["All Island"] + sorted(df_usage["District"].unique().tolist())
selected_district = st.sidebar.selectbox("Select District:", dist_list)
df_step1 = df_usage[df_usage["District"] == selected_district] if selected_district != "All Island" else df_usage.copy()

pir_list = ["All Piriven"] + sorted(df_step1["Piriven Name"].unique().tolist())
selected_piriven = st.sidebar.selectbox("Select Piriven Name:", pir_list)
df_filtered = df_step1[df_step1["Piriven Name"] == selected_piriven] if selected_piriven != "All Piriven" else df_step1.copy()

# Tabs Layout
tab1, tab2, tab3 = st.tabs(["🗺️ Live Map & Remote Control", "📊 Analytics & Usage Stats", "🛠️ Support Tickets"])

with tab2:
    st.subheader("📊 Performance Analytics")
    c_left, c_right = st.columns(2)
    c_left.metric("Registered Boards", len(df_filtered))
    c_right.metric("Active Now", len(df_filtered[df_filtered["Status"]=="Active"]))
    st.write("---")
    
    # පිරිවෙන් මට්ටමින් මෘදුකාංග භාවිතය වෙන් කර බැලීම
    display_name = "All Island" if selected_piriven == "All Piriven" else selected_piriven
    st.markdown(f"### 🖥️ Smart Board Software Analytics ({display_name})")
    
    apps_list = ["Google Chrome", "Microsoft Edge", "VLC Media Player", "MS PowerPoint", "Zoom Meetings", "Microsoft Teams", "MS Whiteboard"]
    app_hours_dict = {app: 0.0 for app in apps_list}
    
    try:
        res_apps = requests.get(f"{FIREBASE_URL}software_analytics.json")
        if res_apps.status_code == 200 and res_apps.json():
            apps_cloud_data = res_apps.json()
            filtered_census_nos = df_filtered["Census No"].astype(str).tolist()
            
            for c_no in filtered_census_nos:
                if c_no in apps_cloud_data:
                    for app in apps_list:
                        minutes = apps_cloud_data[c_no].get(app, 0)
                        app_hours_dict[app] += round(minutes / 60.0, 2)
    except: pass
    
    software_chart_data = pd.DataFrame({
        "Software Application": list(app_hours_dict.keys()),
        "Total Active Execution (Hours)": list(app_hours_dict.values())
    })
    
    col_sw1, col_sw2 = st.columns(2)
    with col_sw1:
        st.markdown("**Software Usage Comparison (Hours)**")
        st.bar_chart(software_chart_data.set_index("Software Application"))
    with col_sw2:
        st.markdown("**Application Screen-Time Breakdown**")
        st.dataframe(software_chart_data, use_container_width=True)
            
    st.write("---")
    st.markdown("**Overall Board Runtime Log (Hours)**")
    st.bar_chart(df_filtered.set_index("Piriven Name")["Monthly Usage (Hours)"])
    
    # 💡 [විසඳුම] පිරිවෙන් ලැයිස්තුවෙන් පිරිවෙනක් තේරීමට නිල Dropdown එකක් මෙතැනට ලබා දීම (ලින්ක් කිරීම)
    st.write("---")
    st.markdown("### 📋 Device Registry & Quick Map Link")
    
    registry_piriven_list = ["None - Stay on Current View"] + sorted(df_filtered["Piriven Name"].unique().tolist())
    focused_piriven = st.selectbox("🔗 Select a Pirivena from below to target/focus on the Live Map:", registry_piriven_list)
    
    # වගුවේ තීරු සුදුසු පරිදි සකසා ගැනීම
    df_table_view = df_filtered.drop(columns=["Latitude", "Longitude"], errors="ignore").copy()
    
    # 💡 [විසඳුම] වගුවේ ඇති Active වචනය Green කිරීමට සහ Offline වචනය Red කිරීමට පැහැදිලි වර්ණ ගැන්වීම
    def color_status(val):
        if val == "Active":
            return "background-color: #d1fae5; color: #065f46; font-weight: bold;"
        elif val == "Offline":
            return "background-color: #fee2e2; color: #991b1b; font-weight: bold;"
        return ""
        
    styled_df = df_table_view.map(color_status, subset=["Status"])
    st.dataframe(styled_df, use_container_width=True)

# Map Cascading View Setup (Dropdown එකෙන් තෝරන පිරිවෙනට සිතියම සජීවීව ලින්ක් වීම)
map_center = [7.8731, 80.7718]
map_zoom = 8

# වගුව උඩ තියෙන Dropdown එකෙන් පිරිවෙනක් තේරුවොත් සිතියම එතැනට යනවා
if "focused_piriven" in locals() and focused_piriven != "None - Stay on Current View":
    selected_row = df_filtered[df_filtered["Piriven Name"] == focused_piriven]
    if not selected_row.empty and selected_row.iloc[0]["Latitude"] != 0:
        map_center = [selected_row.iloc[0]["Latitude"], selected_row.iloc[0]["Longitude"]]
        map_zoom = 14
# එසේ නොමැති නම් Sidebar එකේ ෆිල්ටර් එක අනුව සිතියම ක්‍රියාත්මක වීම
elif selected_piriven != "All Piriven" and not df_filtered.empty:
    first_row = df_filtered.iloc[0]
    if first_row["Latitude"] != 0:
        map_center = [first_row["Latitude"], first_row["Longitude"]]
        map_zoom = 14

with tab1:
    col_map, col_ctrl = st.columns([3, 2])
    with col_map:
        st.subheader("Live Board Tracking")
        m = folium.Map(location=map_center, zoom_start=map_zoom)
        for i, r in df_filtered.iterrows():
            if r["Latitude"] != 0:
                folium.Marker([r["Latitude"], r["Longitude"]], popup=f"{r['Piriven Name']} ({r['Status']})", 
                              icon=folium.Icon(color="green" if r["Status"]=="Active" else "red")).add_to(m)
        st_folium(m, width=700, height=600, key=f"map_{selected_district}_{selected_piriven}_{map_center[0]}")

    with col_ctrl:
        st.subheader("📢 Command Center")
        yt_input = st.text_input("YouTube URL (Video, Playlist or Channel):")
        if st.button("🚀 BROADCAST TO ALL BOARDS"):
            if yt_input:
                link_data = process_youtube_link(yt_input)
                try:
                    requests.put(f"{FIREBASE_URL}current_lesson.json", json=link_data)
                    st.success(f"✅ Broadcast Successful! Type: {link_data['type'].capitalize()}")
                except: st.error("❌ Cloud Connection Error.")
            else: st.warning("⚠️ Please paste a YouTube link.")
                
        st.write("---")
        ann_t = st.text_input("Announcement Title:")
        ann_b = st.text_area("Message Body:")
        if st.button("📢 PUSH LIVE NOTIFICATION"):
            if ann_t and ann_b: requests.put(f"{FIREBASE_URL}latest_announcement.json", json={"title": ann_t, "body": ann_b}); st.success("✅ Message Pushed Successfully!")

with tab3:
    st.subheader("🛠️ Technical Support Tickets (From App)")
    try:
        res_t = requests.get(f"{FIREBASE_URL}support_tickets.json")
        if res_t.status_code == 200 and res_t.json():
            t_data = res_t.json()
            t_list = []
            for tid, det in t_data.items():
                c_no = str(det.get("census_no", "")).strip()
                p_name = census_to_name.get(c_no, f"Unknown ({c_no})")
                if selected_piriven != "All Piriven" and p_name != selected_piriven: continue
                t_list.append({
                    "Piriven": p_name, "Device Serial No": det.get("device_serial", "N/A"),
                    "Issue Category": det.get("issue_type"), "Teacher's Description": det.get("description"), "Status": det.get("status")
                })
            if t_list: st.table(pd.DataFrame(t_list))
            else: st.info("No tickets reported.")
    except: st.error("Cloud Error.")

# Footer Section
st.write("---")
cur_year = datetime.datetime.now().year

def get_base64_image(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as image_file: return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode()}"
    return ""

state_img_base64 = get_base64_image("statelogo.png")
piriven_img_base64 = get_base64_image("pirivenlogo.png")

footer_html = f"""
<div style="background-color: #1e293b; padding: 25px; border-radius: 12px; text-align: center; color: white; margin-top: 40px; font-family: sans-serif;">
    <table style="width: 100%; border-collapse: collapse; border: none; background-color: transparent; margin: 0 auto;">
        <tr style="border: none; background-color: transparent;">
            <td style="width: 20%; text-align: right; border: none; background-color: transparent; padding: 10px; vertical-align: middle;">
                {"<img src='" + state_img_base64 + "' style='height: 60px; max-width: 100%; object-fit: contain;'>" if state_img_base64 else ""}
            </td>
            <td style="width: 60%; text-align: center; border-top: none; border-bottom: none; border-left: 2px solid #475569; border-right: 2px solid #475569; background-color: transparent; padding: 10px 20px; vertical-align: middle;">
                <p style="margin: 0; font-size: 16px; font-weight: bold; color: #60a5fa; letter-spacing: 0.5px;">Piriven Development Branch</p>
                <p style="margin: 6px 0 0 0; font-size: 13px; color: #cbd5e1;">📧 Email: <a href="mailto:info.pirivendevelopment@gmail.com" style="color: #60a5fa; text-decoration: none; font-weight: bold;">info.pirivendevelopment@gmail.com</a></p>
            </td>
            <td style="width: 20%; text-align: left; border: none; background-color: transparent; padding: 10px; vertical-align: middle;">
                {"<img src='" + piriven_img_base64 + "' style='height: 60px; max-width: 100%; object-fit: contain;'>" if piriven_img_base64 else ""}
            </td>
        </tr>
    </table>
    <div style="font-size: 11px; color: #94a3b8; margin-top: 20px; padding-top: 15px; border-top: 1px solid #334155; line-height: 1.5;">
        © {cur_year} | All Rights Reserved | Development Branch, Piriven Division, Ministry of Education, Higher Education and Vocational Education.
    </div>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
