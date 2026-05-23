import requests
import streamlit as st
import streamlit.components.v1 as components  # 💡 JS ඔරලෝසුව සජීවීව පණගැන්වීමට
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
        if "list=" in url_str: return {"type": "playlist", "value": url_str}
        if "/c/" in url_str or "/channel/" in url_str or "/@" in url_str or "user/" in url_str: return {"type": "channel", "value": url_str}
        if parsed_url.hostname == 'youtu.be': return {"type": "video", "value": parsed_url.path[1:]}
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com') and parsed_url.path == '/watch': return {"type": "video", "value": parse_qs(parsed_url.query)['v'][0]}
    except: pass
    return {"type": "custom", "value": url_str}

st.set_page_config(page_title="Ministry Admin Dashboard", layout="wide")

# 💡 සජීවී ඔරලෝසුව
col_title, col_clock = st.columns([4, 1])
with col_title:
    st.markdown("<h2 style='color: #1a365d; margin-top: -10px;'>🏛️ Ministry of Education - Piriven Division</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #4a5568; font-size: 14px; font-weight: bold; margin-top: -15px;'>Central Control, Analytics & Monitoring Dashboard</p>", unsafe_allow_html=True)
with col_clock:
    st.markdown("<p style='text-align:center; margin-bottom:0px; font-weight:bold; color:#475569; font-size:12px;'>💻 DEVICE TIME</p>", unsafe_allow_html=True)
    clock_html = """
    <div id="clock-span" style="background-color: #1e293b; color: #60a5fa; padding: 8px; border-radius: 8px; text-align: center; font-family: monospace; font-size: 14px; font-weight: bold; border: 1px solid #475569;">Loading...</div>
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
    """
    components.html(clock_html, height=60)

st.write("---")

live_boards_data, cloud_excel_data = {}, None
try:
    live_boards_data = requests.get(f"{FIREBASE_URL}live_boards.json").json() or {}
    cloud_excel_data = requests.get(f"{FIREBASE_URL}ministry_excel_registry.json").json()
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
        df_raw["Latitude"] = df_raw["Latitude"].fillna(0.0); df_raw["Longitude"] = df_raw["Longitude"].fillna(0.0)
        df_raw["Monthly Usage (Hours)"] = df_raw["Monthly Usage (Hours)"].fillna(0)

        for index, row in df_raw.iterrows():
            lat, lon = float(row.get("Latitude", 0.0)), float(row.get("Longitude", 0.0))
            if lat > 70.0 and lon < 15.0: df_raw.at[index, "Latitude"], df_raw.at[index, "Longitude"] = lon, lat

        df_temp = pd.DataFrame()
        df_temp["Census No"], df_temp["Piriven Name"] = df_raw["Census No"], df_raw["Piriven Name"]
        df_temp["District"] = [([d for d in SRI_LANKA_DISTRICTS if d.lower() == x.lower()] + ["Other/Unclassified"])[0] for x in df_raw["District"]]
        df_temp["Zone"], df_temp["Latitude"], df_temp["Longitude"], df_temp["Monthly Usage (Hours)"] = df_raw["Zone"], df_raw["Latitude"], df_raw["Longitude"], df_raw["Monthly Usage (Hours)"]
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
        if not last_ping_str: return False
        srilanka_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
        if (srilanka_now - datetime.datetime.strptime(last_ping_str, "%Y-%m-%d %H:%M:%S")).total_seconds() < 600: return True
    except: pass
    return False

live_census_list = []
for c_id, devices in live_boards_data.items():
    if isinstance(devices, dict):
        for d_id, d_info in devices.items():
            if d_id != "attendance" and isinstance(d_info, dict) and is_device_actually_active(d_info.get("last_ping")): live_census_list.append(str(c_id).strip()); break

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
    
    total_active_devices = 0; total_live_students = 0; filtered_census_nos = df_filtered["Census No"].astype(str).tolist()
    for c_no in filtered_census_nos:
        if c_no in live_boards_data and isinstance(live_boards_data[c_no], dict):
            for dev_id, dev_info in live_boards_data[c_no].items():
                if dev_id != "attendance" and isinstance(dev_info, dict) and is_device_actually_active(dev_info.get("last_ping")): total_active_devices += 1
            if "attendance" in live_boards_data[c_no] and isinstance(live_boards_data[c_no]["attendance"], dict) and is_device_actually_active(live_boards_data[c_no]["attendance"].get("last_captured")):
                total_live_students += int(live_boards_data[c_no]["attendance"].get("live_student_count", 0))
            
    c_middle.metric("Total Active Devices Now", total_active_devices)
    c_right.metric("👨‍🎓 Total Live Students Learning Now", total_live_students) 
    st.write("---")
    
    # 💡 [විසඳුම] ඉතිහාසගත දිනපතා ලොග් සටහන් වෙන් කර පෙන්වන රේඩියෝ බොත්තම් ව්‍යුහය (Historical Logic)
    st.markdown("### ⏱️ Select Log Time Frame (භාවිතා කළ කාල සීමාව තෝරන්න)")
    time_frame = st.radio(
        "Filter Logs By:",
        ["Today (අද දවසේ)", "This Week (මේ සතියේ)", "This Month (මේ මාසයේ)", "Total Historical Log (සමස්ත ඉතිහාසය)"],
        horizontal=True,
        key="history_radio"
    )
    
    # දින වකවානු පෙරහන් තර්කනය (Date Filtering Calculation)
    srilanka_today = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).date()
    
    app_hours_dict = {}
    piriven_time_sum_dict = {c: 0.0 for c in filtered_census_nos}
    
    try:
        res_apps = requests.get(f"{FIREBASE_URL}software_analytics.json").json()
        if res_apps:
            for c_no in filtered_census_nos:
                if c_no in res_apps and isinstance(res_apps[c_no], dict):
                    for date_str, apps_data in res_apps[c_no].items():
                        try: log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                        except: continue
                        
                        # රේඩියෝ බොත්තමේ ටික් එක අනුව දත්ත පෙරීම (Filter by Date Range)
                        is_valid = False
                        if time_frame.startswith("Today") and log_date == srilanka_today: is_valid = True
                        elif time_frame.startswith("This Week") and (srilanka_today - log_date).days <= 7: is_valid = True
                        elif time_frame.startswith("This Month") and log_date.month == srilanka_today.month and log_date.year == srilanka_today.year: is_valid = True
                        elif time_frame.startswith("Total"): is_valid = True
                        
                        if is_valid and isinstance(apps_data, dict):
                            for app_name, minutes in apps_data.items():
                                app_hours_dict[app_name] = app_hours_dict.get(app_name, 0.0) + round(minutes / 60.0, 2)
                                piriven_time_sum_dict[c_no] += round(minutes / 60.0, 2)
    except: pass

    if not app_hours_dict: app_hours_dict = {"No Logs for this Period": 0.0}
    software_chart_data = pd.DataFrame({"Software Application": list(app_hours_dict.keys()), "Total Execution (Hours)": list(app_hours_dict.values())})
    
    col_sw1, col_sw2 = st.columns(2)
    with col_sw1:
        st.markdown(f"**Software Usage Comparison ({time_frame.split(' ')[0]})**")
        st.bar_chart(software_chart_data.set_index("Software Application"))
    with col_sw2:
        st.markdown(f"**Application Log Breakdown (Hours)**")
        st.dataframe(software_chart_data, use_container_width=True)
            
    st.write("---")
    # පිරිවෙන් ප්‍රස්ථාරය ද තෝරාගත් කාලයට අනුව යාවත්කාලීන කිරීම
    df_filtered["Filtered Usage (Hours)"] = [piriven_time_sum_dict.get(str(row["Census No"]).strip(), 0.0) for i, row in df_filtered.iterrows()]
    st.markdown(f"**Overall Piriven Runtime Log ({time_frame.split(' ')[0]} - Hours)**")
    st.bar_chart(df_filtered.set_index("Piriven Name")["Filtered Usage (Hours)"])
    
    st.write("---")
    st.markdown("### 📋 Device Registry & Quick Map Link")
    styled_df = df_filtered.drop(columns=["Latitude", "Longitude", "Filtered Usage (Hours)"], errors="ignore").style.map(
        lambda v: "background-color: #d1fae5; color: #065f46; font-weight: bold;" if v == "Active" else ("background-color: #fee2e2; color: #991b1b; font-weight: bold;" if v == "Offline" else ""), subset=["Status"]
    )
    st.dataframe(styled_df, use_container_width=True)

# Map setup
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
                live_stu_popup = live_boards_data[c_no]["attendance"].get("live_student_count", 0) if "attendance" in live_boards_data[c_no] and is_device_actually_active(live_boards_data[c_no]["attendance"].get("last_captured")) else 0
                for dev_id, dev_info in live_boards_data[c_no].items():
                    if dev_id != "attendance" and isinstance(dev_info, dict) and is_device_actually_active(dev_info.get("last_ping")):
                        is_any_device_live = True; d_type = dev_info.get("device_type", "Smart Board")
                        adv_spec = dev_info.get("spec_advanced", {})
                        popup_html = f"""<div style='font-family: sans-serif; font-size: 11px; min-width: 250px;'><b>🏛️ {r['Piriven Name']}</b><br>📟 {d_type} ({dev_id})<br>🟢 Active Now | 👨‍🎓 Students: {live_stu_popup}<br>Processor: {adv_spec.get('processor','N/A')}<br>RAM/OS: {adv_spec.get('ram','N/A')} | {adv_spec.get('os','N/A')}</div>"""
                        folium.Marker([dev_info.get("live_lat", r["Latitude"]), dev_info.get("live_lon", r["Longitude"])], popup=popup_html, icon=folium.Icon(color="green" if d_type == "Smart Board" else "blue", icon="desktop" if d_type != "Laptop" else "laptop")).add_to(m)
            if not is_any_device_live and r["Latitude"] != 0: folium.Marker([r["Latitude"], r["Longitude"]], popup=f"🏛️ {r['Piriven Name']}<br>🔴 Offline", icon=folium.Icon(color="red", icon="remove-sign")).add_to(m)
        st_folium(m, width=700, height=600, key=f"map_{selected_district}_{selected_piriven}")
    with col_ctrl:
        st.subheader("📢 Command Center")
        yt_input = st.text_input("YouTube URL:")
        if st.button("🚀 BROADCAST TO ALL BOARDS") and yt_input: requests.put(f"{FIREBASE_URL}current_lesson.json", json=process_youtube_link(yt_input)); st.success("✅ Broadcast Successful!")
        st.write("---")
        ann_t, ann_b = st.text_input("Announcement Title:"), st.text_area("Message Body:")
        if st.button("📢 PUSH LIVE NOTIFICATION") and ann_t and ann_b: requests.put(f"{FIREBASE_URL}latest_announcement.json", json={"title": ann_t, "body": ann_b}); st.success("✅ Message Pushed Successfully!")

# support tickets
with tab3:
    st.subheader("🛠️ Technical Support & Ticket Interactive Chat Panel")
    def resolve_ticket(ticket_id):
        try:
            if requests.patch(f"{FIREBASE_URL}support_tickets/{ticket_id}.json", json={"status": "Solved"}, timeout=4).status_code == 200: st.toast("🟢 ටිකට් එක සාර්ථකව යාවත්කාලීන වුණා!", icon="✅"); st.rerun()
        except: st.sidebar.error("❌ Connection Error.")
    try:
        res_t = requests.get(f"{FIREBASE_URL}support_tickets.json", timeout=4).json()
        if res_t:
            ticket_index = 1
            for tid, det in res_t.items():
                c_no = str(det.get("census_no", "")).strip(); p_name = census_to_name.get(c_no, f"Unknown ({c_no})")
                if selected_piriven != "All Piriven" and p_name != selected_piriven: continue
                with st.expander(f"🎫 TICKET #{ticket_index} | 🏛️ {p_name} - [{det.get('issue_type')}] - Status: {det.get('status')}"):
                    st.markdown(f"**📝 Description:** {det.get('description')}")
                    st.write("---")
                    chats = det.get("chats", {})
                    if chats:
                        for cid, cmsg in chats.items(): st.markdown(f"**{'🏛️ Ministry' if cmsg.get('sender')=='ministry' else '🏫 Piriven'}:** {cmsg.get('msg')}  *<small>({cmsg.get('time')[11:16]})</small>*", unsafe_allow_html=True)
                    if det.get('status') == "Pending":
                        chat_input = st.text_input("Type your response here:", key=f"chat_in_{tid}")
                        if st.button("↩️ Send Message", key=f"send_btn_{tid}") and chat_input:
                            requests.post(f"{FIREBASE_URL}support_tickets/{tid}/chats.json", json={"sender": "ministry", "msg": chat_input, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                            st.rerun()
                        st.write("---")
                        st.button("Mark as Solved ✅", key=f"sol_{tid}", on_click=resolve_ticket, args=(tid,))
                    else: st.info("🔒 This ticket has been marked as solved. Chat is locked.")
                ticket_index += 1
        else: st.info("No reported tickets found.")
    except Exception as e: st.error(f"Error loading tickets: {e}")

# Footer Section
st.write("---")
cur_year = datetime.datetime.now().year
def get_base64_image(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as image_file: return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode()}"
    return ""
state_img_base64, piriven_img_base64 = get_base64_image("statelogo.png"), get_base64_image("pirivenlogo.png")
footer_html = f"""<div style="background-color: #1e293b; padding: 25px; border-radius: 12px; text-align: center; color: white; margin-top: 40px; font-family: sans-serif;"><table style="width: 100%; border-collapse: collapse; border: none; background-color: transparent; margin: 0 auto;"><tr style="border: none; background-color: transparent;"><td style="width: 20%; text-align: right; border: none; background-color: transparent; padding: 10px; vertical-align: middle;">{"<img src='" + state_img_base64 + "' style='height: 60px; max-width: 100%; object-fit: contain;'>" if state_img_base64 else ""}</td><td style="width: 60%; text-align: center; border-top: none; border-bottom: none; border-left: 2px solid #475569; border-right: 2px solid #475569; background-color: transparent; padding: 10px 20px; vertical-align: middle;"><p style="margin: 0; font-size: 16px; font-weight: bold; color: #60a5fa; letter-spacing: 0.5px;">Piriven Development Branch</p><p style="margin: 6px 0 0 0; font-size: 13px; color: #cbd5e1;">📧 Email: <a href="mailto:info.pirivendevelopment@gmail.com" style="color: #60a5fa; text-decoration: none; font-weight: bold;">info.pirivendevelopment@gmail.com</a></p></td><td style="width: 20%; text-align: left; border: none; background-color: transparent; padding: 10px; vertical-align: middle;">{"<img src='" + piriven_img_base64 + "' style='height: 60px; max-width: 100%; object-fit: contain;'>" if piriven_img_base64 else ""}</td></tr></table><div style="font-size: 11px; color: #94a3b8; margin-top: 20px; padding-top: 15px; border-top: 1px solid #334155; line-height: 1.5;">© {cur_year} | All Rights Reserved | Ministry of Education.</div></div>"""
st.markdown(footer_html, unsafe_allow_html=True)
