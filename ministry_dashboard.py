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
    
    div[data-testid="stMetricValue"] { 
        color: #f8fafc !important; 
        font-size: 32px; 
        font-weight: bold;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    
    div[data-testid="stMetricLabel"] p {
        color: #cbd5e1 !important;
        font-weight: 600;
    }
    
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
        
        df_raw["Census No"] = df_raw["Census No"].fillna("").astype(str).str.strip()
        df_raw["Census No"] = df_raw["Census No"].apply(lambda x: x.split('.')[0] if '.' in x else x)
        
        df_raw["Piriven Name"] = df_raw["Piriven Name"].fillna("").astype(str).str.strip()
        df_raw["District"] = df_raw["District"].fillna("").astype(str).str.strip().str.title() 
        df_raw["Zone"] = df_raw["Zone"].fillna("").astype(str).str.strip().str.title() if "Zone" in df_raw.columns else df_raw["District"]
        df_raw["Latitude"] = df_raw["Latitude"].fillna(0.0)
        df_raw["Longitude"] = df_raw["Longitude"].fillna(0.0)
        df_raw["Monthly Usage (Hours)"] = df_raw["Monthly Usage (Hours)"].fillna(0)

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
    df_usage["Census No"] = df_usage["Census No"].astype(str).str.strip()
    df_usage["Census No"] = df_usage["Census No"].apply(lambda x: x.split('.')[0] if '.' in x else x)
    df_usage["District"] = df_usage["District"].astype(str).str.strip().str.title()
    st.sidebar.info("☁️ Registry Loaded from Cloud")

if df_usage is None:
    df_usage = pd.DataFrame({"Census No": ["0542"], "Piriven Name": ["Sample Pirivena"], "District": ["Colombo"], "Zone": ["Central"], "Status": ["Offline"], "Latitude": [6.9271], "Longitude": [79.8612], "Monthly Usage (Hours)": [0]})

# 💡 [විසඳුම] ඩිවයිස් එකක් සජීවීද නැද්ද කියා කාල සීමාව අනුව (Heartbeat Timeout) තීරණය කරන ආරක්ෂිත පියවර
def is_device_actually_active(last_ping_str):
    try:
        if not last_ping_str: return False
        last_ping_time = datetime.datetime.strptime(last_ping_str, "%Y-%m-%d %H:%M:%S")
        time_difference = datetime.datetime.now() - last_ping_time
        # අවසන් සංඥාව ඇවිත් විනාඩි 10 කට වඩා වැඩි නම් එය Offline (අක්‍රිය) ලෙස සැලකීම
        if time_difference.total_seconds() < 600: 
            return True
    except: pass
    return False

# ලැයිස්තුවේ පෙන්වීමට අවසාන සජීවී තත්ත්වය (Status) සැකසීම
live_census_list = []
for c_id, devices in live_boards_data.items():
    if isinstance(devices, dict):
        for d_id, d_info in devices.items():
            if isinstance(d_info, dict) and is_device_actually_active(d_info.get("last_ping")):
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

# Tabs Layout
tab1, tab2, tab3 = st.tabs(["🗺️ Live Map & Remote Control", "📊 Analytics & Usage Stats", "🛠️ Support Tickets"])

with tab2:
    st.subheader("📊 Performance Analytics")
    c_left, c_middle, c_right = st.columns(3) # 💡 [විසඳුම] 3 Columns මට්ටමට Layout එක සකස් කිරීම
    c_left.metric("Registered Boards", len(df_filtered))
    
    # 💡 [විසඳුම] සැබෑ ලෙසම දැනට සක්‍රිය උපාංග සහ AI මඟින් හඳුනාගත් මුළු ශිෂ්‍ය සංඛ්‍යාව ගණනය කිරීම
    total_active_devices = 0
    total_live_students = 0
    filtered_census_nos = df_filtered["Census No"].astype(str).tolist()
    
    for c_no in filtered_census_nos:
        if c_no in live_boards_data and isinstance(live_boards_data[c_no], dict):
            # 1. Active Devices ගණන සෙවීම
            for dev_id, dev_info in live_boards_data[c_no].items():
                if isinstance(dev_info, dict) and is_device_actually_active(dev_info.get("last_ping")):
                    total_active_devices += 1
            
            # 2. AI Attendance දත්ත තිබේ නම් ශිෂ්‍ය එකතුව ලබා ගැනීම
            if "attendance" in live_boards_data[c_no] and isinstance(live_boards_data[c_no]["attendance"], dict):
                att_info = live_boards_data[c_no]["attendance"]
                # අවසන් වරට කැමරාව ක්‍රියාත්මක වී විනාඩි 20කට වඩා පැරණි නොවේ නම් පමණක් සිසුන් සංඛ්‍යාව එකතු කිරීම
                if is_device_actually_active(att_info.get("last_captured")):
                    total_live_students += int(att_info.get("live_student_count", 0))
            
    c_middle.metric("Total Active Devices Now", total_active_devices)
    c_right.metric("👨‍🎓 Total Live Students Learning Now", total_live_students) # 💡 [නව විශේෂාංගය]
    st.write("---")
    
    display_name = "All Island" if selected_piriven == "All Piriven" else selected_piriven
    st.markdown(f"### 🖥️ Smart Board Software Analytics ({display_name})")
    
    app_hours_dict = {}
    try:
        res_apps = requests.get(f"{FIREBASE_URL}software_analytics.json")
        if res_apps.status_code == 200 and res_apps.json():
            apps_cloud_data = res_apps.json()
            for c_no in filtered_census_nos:
                if c_no in apps_cloud_data and isinstance(apps_cloud_data[c_no], dict):
                    for app_name, minutes in apps_cloud_data[c_no].items():
                        if app_name not in app_hours_dict:
                            app_hours_dict[app_name] = 0.0
                        app_hours_dict[app_name] += round(minutes / 60.0, 2)
    except: pass
    
    if not app_hours_dict:
        app_hours_dict = {"No Software Tracked Yet": 0.0}
        
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
    
    st.write("---")
    st.markdown("### 📋 Device Registry & Quick Map Link")
    styled_df = df_filtered.drop(columns=["Latitude", "Longitude"], errors="ignore").style.map(
        lambda v: "background-color: #d1fae5; color: #065f46; font-weight: bold;" if v == "Active" else ("background-color: #fee2e2; color: #991b1b; font-weight: bold;" if v == "Offline" else ""),
        subset=["Status"]
    )
    st.dataframe(styled_df, use_container_width=True)

# Map View Setup
map_center = [7.8731, 80.7718]
map_zoom = 8
if selected_piriven != "All Piriven" and not df_filtered.empty:
    first_row = df_filtered.iloc[0]
    if first_row["Latitude"] != 0: map_center = [first_row["Latitude"], first_row["Longitude"]]; map_zoom = 14

with tab1:
    col_map, col_ctrl = st.columns([3, 2])
    with col_map:
        st.subheader("Live Board Tracking")
        m = folium.Map(location=map_center, zoom_start=map_zoom)
        
        for i, r in df_filtered.iterrows():
            c_no = str(r["Census No"]).strip()
            is_any_device_live = False
            
            if c_no in live_boards_data and isinstance(live_boards_data[c_no], dict):
                # AI ශිෂ්‍ය සංඛ්‍යාව සිතියම් පොප්අප් එක සඳහා කියවා ගැනීම
                live_stu_popup = 0
                if "attendance" in live_boards_data[c_no] and isinstance(live_boards_data[c_no]["attendance"], dict):
                    att_info = live_boards_data[c_no]["attendance"]
                    if is_device_actually_active(att_info.get("last_captured")):
                        live_stu_popup = att_info.get("live_student_count", 0)

                for dev_id, dev_info in live_boards_data[c_no].items():
                    if dev_id == "attendance" or not isinstance(dev_info, dict): continue
                    
                    # 💡 [විසඳුම] සිතියම මත ලකුණු කරන්නේ ඇත්තටම සජීවීව පවතින උපාංග පමණි
                    if is_device_actually_active(dev_info.get("last_ping")):
                        is_any_device_live = True
                        d_type = dev_info.get("device_type", "Smart Board")
                        l_lat = dev_info.get("live_lat", r["Latitude"])
                        l_lon = dev_info.get("live_lon", r["Longitude"])
                        
                        # ආණමඩුව හෝ වැරදි IP පිහිටීම් මඟහැර බත්තරමුල්ල නිවැරදි ස්ථානය ලබා ගැනීම
                        if c_no == "430001" or l_lat == 7.8731 or l_lat == 0.0 or l_lat == 7.873100000000001:
                            l_lat = r["Latitude"]
                            l_lon = r["Longitude"]
                            l_city = "Ministry Office (Battaramulla)"
                        else:
                            l_city = dev_info.get("live_city", "Unknown")
                        
                        if d_type == "Smart Board": icon_color = "green"
                        elif d_type == "Laptop": icon_color = "blue"
                        else: icon_color = "orange"
                        
                        if l_lat != 0.0 and l_lon != 0.0:
                            folium.Marker(
                                [l_lat, l_lon],
                                popup=f"🏛️ <b>{r['Piriven Name']}</b><br>📟 Device: {d_type}<br>📍 Location: {l_city}<br>👨‍🎓 Active Students: {live_stu_popup}<br>🟢 Status: Active Now",
                                icon=folium.Icon(color=icon_color, icon="desktop" if d_type != "Laptop" else "laptop")
                            ).add_to(m)
            
            # 💡 [විසඳුම] උපාංගය සැබෑ ලෙසම Offline නම් පමණක් රතු මාකර් එක සිතියම මත පෙන්වීම
            if not is_any_device_live and r["Latitude"] != 0:
                folium.Marker(
                    [r["Latitude"], r["Longitude"]], 
                    popup=f"🏛️ {r['Piriven Name']}<br>🔴 Status: Offline", 
                    icon=folium.Icon(color="red", icon="remove-sign")
                ).add_to(m)
                                      
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
    st.subheader("🛠️ Technical Support Tickets Control Panel")
    def resolve_ticket(ticket_id):
        try:
            res = requests.patch(f"{FIREBASE_URL}support_tickets/{ticket_id}.json", json={"status": "Solved"}, timeout=4)
            if res.status_code == 200: st.toast("🟢 ටිකට් එක සාර්ථකව යාවත්කාලීන වුණා!", icon="✅")
        except: st.sidebar.error("❌ Connection Error.")

    try:
        res_t = requests.get(f"{FIREBASE_URL}support_tickets.json", timeout=4)
        if res_t.status_code == 200 and res_t.json():
            t_data = res_t.json()
            t_list = []
            for tid, det in t_data.items():
                c_no = str(det.get("census_no", "")).strip()
                p_name = census_to_name.get(c_no, f"Unknown ({c_no})")
                if selected_piriven != "All Piriven" and p_name != selected_piriven: continue
                t_list.append({
                    "Ticket ID": tid, "Piriven": p_name, "Device Serial No": det.get("device_serial", "N/A"),
                    "Issue Category": det.get("issue_type"), "Description": det.get("description"), "Status": det.get("status", "Pending")
                })
            
            if t_list:
                df_tickets = pd.DataFrame(t_list)
                csv_data = df_tickets.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 DOWNLOAD ALL TICKETS (JOB LIST) AS CSV", data=csv_data, file_name=f"Piriven_Support_Jobs_{datetime.date.today()}.csv", mime="text/csv")
                st.write("---")
                
                for index, row in df_tickets.iterrows():
                    col_t1, col_t2, col_t3 = st.columns([3, 1, 1])
                    with col_t1: st.markdown(f"🏛️ **{row['Piriven']}** ({row['Issue Category']})<br>📝 *{row['Description']}*<br><small>Serial: {row['Device Serial No']}</small>", unsafe_allow_html=True)
                    with col_t2:
                        if row['Status'] == "Pending": st.markdown("🔴 <span style='color:red;font-weight:bold;'>Pending</span>", unsafe_allow_html=True)
                        else: st.markdown("🟢 <span style='color:green;font-weight:bold;'>Solved</span>", unsafe_allow_html=True)
                    with col_t3:
                        if row['Status'] == "Pending": st.button("Mark as Solved", key=f"btn_{row['Ticket ID']}_{index}", on_click=resolve_ticket, args=(row['Ticket ID'],))
                        else: st.write("🔒 Complete")
                    st.write("<hr style='margin: 10px 0; border-color: #e2e8f0;'>", unsafe_allow_html=True)
            else: st.info("No tickets reported for the selected filter.")
        else: st.info("No tickets reported in the system.")
    except Exception as ex: st.error(f"Cloud Error: {ex}")

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
