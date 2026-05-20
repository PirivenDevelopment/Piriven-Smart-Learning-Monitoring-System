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
    
    div[data-testid="stMetricValue"] { 
        color: #f8fafc !important; 
        font-size: 32px; 
        font-weight: bold;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    div[data-testid="stMetricLabel"] p { color: #cbd5e1 !important; font-weight: 600; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

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
        df_raw["Census No"] = df_raw["Census No"].fillna("").astype(str).str.strip().apply(lambda x: x.split('.')[0] if '.' in x else x)
        df_raw["Piriven Name"] = df_raw["Piriven Name"].fillna("").astype(str).str.strip()
        df_raw["District"] = df_raw["District"].fillna("").astype(str).str.strip().str.title() 
        df_raw["Zone"] = df_raw["Zone"].fillna("").astype(str).str.strip().str.title() if "Zone" in df_raw.columns else df_raw["District"]
        df_raw["Latitude"] = df_raw["Latitude"].fillna(0.0)
        df_raw["Longitude"] = df_raw["Longitude"].fillna(0.0)
        df_raw["Monthly Usage (Hours)"] = df_raw["Monthly Usage (Hours)"].fillna(0)

        for index, row in df_raw.iterrows():
            lat, lon = float(row.get("Latitude", 0.0)), float(row.get("Longitude", 0.0))
            if lat > 70.0 and lon < 15.0:
                df_raw.at[index, "Latitude"] = lon
                df_raw.at[index, "Longitude"] = lat

        df_temp = pd.DataFrame()
        df_temp["Census No"], df_temp["Piriven Name"] = df_raw["Census No"], df_raw["Piriven Name"]
        df_temp["District"] = [([d for d in SRI_LANKA_DISTRICTS if d.lower() == x.lower()] + ["Other/Unclassified"])[0] for x in df_raw["District"]]
        df_temp["Zone"], df_temp["Latitude"], df_temp["Longitude"], df_temp["Monthly Usage (Hours)"] = df_raw["Zone"], df_raw["Latitude"], df_raw["Longitude"], df_raw["Monthly Usage (Hours)"]
        
        requests.put(f"{FIREBASE_URL}ministry_excel_registry.json", json=df_temp.to_dict(orient="records"))
        df_usage = df_temp.copy()
        st.sidebar.success("✅ Excel Saved to Cloud!")
    except Exception as e: st.sidebar.error(f"Error: {e}")

if df_usage is None and cloud_excel_data:
    df_usage = pd.DataFrame(cloud_excel_data)
    df_usage["Census No"] = df_usage["Census No"].astype(str).str.strip().apply(lambda x: x.split('.')[0] if '.' in x else x)
    df_usage["District"] = df_usage["District"].astype(str).str.strip().str.title()
    st.sidebar.info("☁️ Registry Loaded from Cloud")

if df_usage is None:
    df_usage = pd.DataFrame({"Census No": ["0542"], "Piriven Name": ["Sample Pirivena"], "District": ["Colombo"], "Zone": ["Central"], "Status": ["Offline"], "Latitude": [6.9271], "Longitude": [79.8612], "Monthly Usage (Hours)": [0]})

def is_device_actually_active(last_ping_str):
    try:
        if not last_ping_str: return False
        last_ping_time = datetime.datetime.strptime(last_ping_str, "%Y-%m-%d %H:%M:%S")
        if (datetime.datetime.now() - last_ping_time).total_seconds() < 600: return True
    except: pass
    return False

live_census_list = []
for c_id, devices in live_boards_data.items():
    if isinstance(devices, dict):
        for d_id, d_info in devices.items():
            if d_id != "attendance" and isinstance(d_info, dict) and is_device_actually_active(d_info.get("last_ping")):
                live_census_list.append(str(c_id).strip())
                break

df_usage["Status"] = ["Active" if str(row["Census No"]).strip() in live_census_list else "Offline" for i, row in df_usage.iterrows()]
census_to_name = dict(zip(df_usage["Census No"].astype(str), df_usage["Piriven Name"]))

# Filters
st.sidebar.write("---")
st.sidebar.header("🔍 Live Filters")
dist_list = ["All Island"] + sorted([d for d in df_usage["District"].unique().tolist() if d and d != "Nan"])
selected_district = st.sidebar.selectbox("Select District:", dist_list)
df_step1 = df_usage[df_usage["District"] == selected_district] if selected_district != "All Island" else df_usage.copy()

pir_list = ["All Piriven"] + sorted(df_step1["Piriven Name"].unique().tolist())
selected_piriven = st.sidebar.selectbox("Select Piriven Name:", pir_list)
df_filtered = df_step1[df_step1["Piriven Name"] == selected_piriven] if selected_piriven != "All Piriven" else df_step1.copy()

tab1, tab2, tab3 = st.tabs(["🗺️ Live Map & Remote Control", "📊 Analytics & Usage Stats", "🛠️ Support Tickets & Live Chat"])

with tab2:
    st.subheader("📊 Performance Analytics")
    c_left, c_middle, c_right = st.columns(3) 
    c_left.metric("Registered Boards", len(df_filtered))
    
    total_active_devices = 0
    total_live_students = 0
    filtered_census_nos = df_filtered["Census No"].astype(str).tolist()
    
    for c_no in filtered_census_nos:
        if c_no in live_boards_data and isinstance(live_boards_data[c_no], dict):
            # 💡 [විසඳුම] Multi-Device Fix: හැම ඩිවයිස් එකක්ම වෙන වෙනම ගණන් ගැනීම
            for dev_id, dev_info in live_boards_data[c_no].items():
                if dev_id != "attendance" and isinstance(dev_info, dict) and is_device_actually_active(dev_info.get("last_ping")):
                    total_active_devices += 1
            if "attendance" in live_boards_data[c_no] and isinstance(live_boards_data[c_no]["attendance"], dict):
                att_info = live_boards_data[c_no]["attendance"]
                if is_device_actually_active(att_info.get("last_captured")):
                    total_live_students += int(att_info.get("live_student_count", 0))
            
    c_middle.metric("Total Active Devices Now", total_active_devices)
    c_right.metric("👨‍🎓 Total Live Students Learning Now", total_live_students) 
    st.write("---")
    
    # Software chart logics
    app_hours_dict = {}
    try:
        res_apps = requests.get(f"{FIREBASE_URL}software_analytics.json")
        if res_apps.status_code == 200 and res_apps.json():
            apps_cloud_data = res_apps.json()
            for c_no in filtered_census_nos:
                if c_no in apps_cloud_data and isinstance(apps_cloud_data[c_no], dict):
                    for app_name, minutes in apps_cloud_data[c_no].items():
                        if app_name not in app_hours_dict: app_hours_dict[app_name] = 0.0
                        app_hours_dict[app_name] += round(minutes / 60.0, 2)
    except: pass
    if not app_hours_dict: app_hours_dict = {"No Software Tracked Yet": 0.0}
    software_chart_data = pd.DataFrame({"Software Application": list(app_hours_dict.keys()), "Total Active Execution (Hours)": list(app_hours_dict.values())})
    
    col_sw1, col_sw2 = st.columns(2)
    with col_sw1: st.bar_chart(software_chart_data.set_index("Software Application"))
    with col_sw2: st.dataframe(software_chart_data, use_container_width=True)

with tab1:
    col_map, col_ctrl = st.columns([3, 2])
    with col_map:
        st.subheader("Live Board Tracking")
        m = folium.Map(location=map_center, zoom_start=map_zoom)
        
        for i, r in df_filtered.iterrows():
            c_no = str(r["Census No"]).strip()
            is_any_device_live = False
            
            if c_no in live_boards_data and isinstance(live_boards_data[c_no], dict):
                live_stu_popup = 0
                if "attendance" in live_boards_data[c_no] and isinstance(live_boards_data[c_no]["attendance"], dict):
                    att_info = live_boards_data[c_no]["attendance"]
                    if is_device_actually_active(att_info.get("last_captured")):
                        live_stu_popup = att_info.get("live_student_count", 0)

                # 💡 [විසඳුම] Multi-Device Fix: ලැප්ටොප් සහ ස්මාර්ට්බෝඩ් දෙකම තිබේ නම් දෙකම වෙන වෙනම සිතියමේ අඳියි
                for dev_id, dev_info in live_boards_data[c_no].items():
                    if dev_id == "attendance" or not isinstance(dev_info, dict): continue
                    
                    if is_device_actually_active(dev_info.get("last_ping")):
                        is_any_device_live = True
                        d_type = dev_info.get("device_type", "Smart Board")
                        l_lat = dev_info.get("live_lat", r["Latitude"])
                        l_lon = dev_info.get("live_lon", r["Longitude"])
                        l_city = "Ministry Zone" if l_lat == 7.8731 or l_lat == 0.0 else dev_info.get("live_city", "Unknown")
                        
                        icon_color = "green" if d_type == "Smart Board" else "blue" if d_type == "Laptop" else "orange"
                        adv_spec = dev_info.get("spec_advanced", {})
                        
                        popup_html = f"""
                        <div style='font-family: sans-serif; font-size: 11px; min-width: 250px;'>
                            <b>🏛️ {r['Piriven Name']}</b><br>
                            📟 <b>Type:</b> {d_type} (Serial: {dev_id})<br>
                            🟢 <b>Status:</b> Active Now | 👨‍🎓 <b>Students:</b> {live_stu_popup}<br>
                            <table style='width:100%; border-collapse:collapse; margin-top:5px;'>
                                <tr style='background:#f1f5f9;'><td><b>Spec:</b></td><td>{adv_spec.get('processor','N/A')} | {adv_spec.get('ram','N/A')}</td></tr>
                                <tr><td><b>Disk/OS:</b></td><td>{adv_spec.get('harddisk','N/A')} | {adv_spec.get('os','N/A')}</td></tr>
                            </table>
                        </div>
                        """
                        folium.Marker([l_lat, l_lon], popup=popup_html, icon=folium.Icon(color=icon_color, icon="desktop" if d_type != "Laptop" else "laptop")).add_to(m)
            
            if not is_any_device_live and r["Latitude"] != 0:
                folium.Marker([r["Latitude"], r["Longitude"]], popup=f"🏛️ {r['Piriven Name']}<br>🔴 Offline", icon=folium.Icon(color="red", icon="remove-sign")).add_to(m)
                                      
        st_folium(m, width=700, height=600, key=f"map_{selected_district}_{selected_piriven}")

    with col_ctrl:
        st.subheader("📢 Command Center")
        yt_input = st.text_input("YouTube URL:")
        if st.button("🚀 BROADCAST TO ALL BOARDS"):
            if yt_input: requests.put(f"{FIREBASE_URL}current_lesson.json", json=process_youtube_link(yt_input)); st.success("✅ Broadcast Successful!")
        st.write("---")
        ann_t, ann_b = st.text_input("Announcement Title:"), st.text_area("Message Body:")
        if st.button("📢 PUSH LIVE NOTIFICATION"):
            if ann_t and ann_b: requests.put(f"{FIREBASE_URL}latest_announcement.json", json={"title": ann_t, "body": ann_b}); st.success("✅ Pushed Successfully!")

# 💡 [නව විශේෂාංගය] Support Tickets & Live Chat සිස්ටම් එක
with tab3:
    st.subheader("🛠️ Technical Support & Ticket Interactive Chat Panel")
    
    def resolve_ticket(ticket_id):
        requests.patch(f"{FIREBASE_URL}support_tickets/{ticket_id}.json", json={"status": "Solved"})
        st.rerun()

    try:
        res_t = requests.get(f"{FIREBASE_URL}support_tickets.json", timeout=4)
        if res_t.status_code == 200 and res_t.json():
            t_data = res_t.json()
            
            # වටිනාකම් සහ සන්නිවේදන ලැයිස්තුව නිර්මාණය කිරීම
            for tid, det in t_data.items():
                c_no = str(det.get("census_no", "")).strip()
                p_name = census_to_name.get(c_no, f"Unknown ({c_no})")
                if selected_piriven != "All Piriven" and p_name != selected_piriven: continue
                
                # ජොබ් කාඩ් එක (Expandable UI)
                with st.expander(f"🏛️ {p_name} - [{det.get('issue_type')}] (⏱️ {det.get('reported_at', 'N/A')}) - Status: {det.get('status')}"):
                    st.markdown(f"**📝 Issue Description:** {det.get('description')}")
                    st.caption(f"Device Serial: {det.get('device_serial', 'N/A')} | Ticket ID: {tid}")
                    
                    # 💡 [Live Chat] පණිවුඩ කියවීම සහ යැවීම
                    st.write("---")
                    st.markdown("💬 **Live Discussion / අමාත්‍යාංශ පිළිතුරු:**")
                    chats = det.get("chats", {})
                    if chats:
                        for cid, cmsg in chats.items():
                            sender = "🏛️ Ministry" if cmsg.get("sender") == "ministry" else "🏫 Piriven"
                            st.markdown(f"**{sender}:** {cmsg.get('msg')}  *<small>({cmsg.get('time')})</small>*", unsafe_allow_html=True)
                    
                    # චැට් එක ටයිප් කර සෙන්ඩ් කරන කොටස
                    chat_input = st.text_input("Type your response here / පිළිතුර සටහන් කරන්න:", key=f"chat_in_{tid}")
                    if st.button("↩️ Send Message", key=f"send_btn_{tid}"):
                        if chat_input:
                            new_chat_node = {
                                "sender": "ministry",
                                "msg": chat_input,
                                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            requests.post(f"{FIREBASE_URL}support_tickets/{tid}/chats.json", json=new_chat_node)
                            st.rerun()
                    
                    st.write("---")
                    if det.get('status') == "Pending":
                        st.button("Mark as Solved ✅", key=f"sol_{tid}", on_click=resolve_ticket, args=(tid,))
        else: st.info("No reported tickets found.")
    except Exception as e: st.error(f"Error loading tickets: {e}")

# Footer (කලින් කේතයේ පරිදිම පවතී)
