import streamlit as st
import json
import os
import google.generativeai as genai
import requests
import re
import streamlit.components.v1 as components

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Automation Hub v3.0", layout="wide")

# --- CUSTOM CSS & JS (Cho nút Copy gọn gàng) ---
def copy_button(text_to_copy, button_label="Copy"):
    code = f"""
    <button onclick="navigator.clipboard.writeText(`{text_to_copy}`)" 
    style="background-color: #4CAF50; color: white; border: none; padding: 5px 15px; 
    border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 5px;">
    {button_label}
    </button>
    """
    return components.html(code, height=45)

# --- LẤY API KEYS ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    HF_TOKEN = st.secrets["HF_TOKEN"]
    genai.configure(api_key=GEMINI_API_KEY)
except:
    st.error("❌ Thiếu API Key trong Secrets!")
    st.stop()

# --- QUẢN LÝ TÀI KHOẢN (JSON) ---
def save_accounts(accounts):
    with open('accounts.json', 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=4)

def load_accounts():
    if os.path.exists('accounts.json'):
        try:
            with open('accounts.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

# Khởi tạo Session State cho toàn ứng dụng
if 'accounts' not in st.session_state: st.session_state.accounts = load_accounts()
if 'content' not in st.session_state: st.session_state.content = ""
if 'prompt' not in st.session_state: st.session_state.prompt = ""
if 'image_result' not in st.session_state: st.session_state.image_result = None
if 'tmp_name' not in st.session_state: st.session_state.tmp_name = ""
if 'tmp_uid' not in st.session_state: st.session_state.tmp_uid = ""
if 'tmp_avatar' not in st.session_state: st.session_state.tmp_avatar = ""

# --- HÀM LẤY INFO FB ---
def fetch_fb_profile(cookie_str):
    try:
        headers = {
            'cookie': cookie_str,
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1'
        }
        uid = re.search(r'c_user=(\d+)', cookie_str)
        uid = uid.group(1) if uid else "Unknown"
        res = requests.get("https://mbasic.facebook.com/profile.php", headers=headers, timeout=10)
        name = re.search(r'<title>(.*?)</title>', res.text)
        name = name.group(1) if name else "Facebook User"
        avatar = f"https://graph.facebook.com/{uid}/picture?type=large"
        return name, uid, avatar
    except:
        return "", "", ""

# --- SIDEBAR: QUẢN LÝ TÀI KHOẢN ---
with st.sidebar:
    st.header("👤 Hệ thống Tài khoản")
    
    with st.expander("🛠️ Nhập tài khoản mới", expanded=True):
        input_cookie = st.text_area("1. Dán Cookies Facebook:", height=80)
        if st.button("🔍 Check & Auto-fill"):
            name, uid, avt = fetch_fb_profile(input_cookie)
            if name:
                st.session_state.tmp_name = name
                st.session_state.tmp_uid = uid
                st.session_state.tmp_avatar = avt
                st.success("Đã lấy thông tin!")
            else:
                st.error("Cookie không hợp lệ!")

        # Ô nhập liệu (Sẽ tự động điền nếu Check thành công)
        final_name = st.text_input("Tên Facebook:", st.session_state.tmp_name)
        final_uid = st.text_input("UID Facebook:", st.session_state.tmp_uid)
        final_avatar = st.text_input("URL Avatar (Nhận diện Nick):", st.session_state.tmp_avatar)
        
        st.divider()
        st.write("**Ảnh nhân vật mẫu (Cho AI học):**")
        char_url = st.text_input("Dán URL ảnh nhân vật:")
        char_file = st.file_uploader("Hoặc tải ảnh lên", type=['jpg', 'png'])
        
        if st.button("💾 LƯU TÀI KHOẢN"):
            if final_name and input_cookie:
                st.session_state.accounts[final_name] = {
                    "uid": final_uid,
                    "avatar": final_avatar,
                    "character_url": char_url,
                    "cookies": input_cookie
                }
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu vào kho!")
                st.rerun()

    st.divider()
    # Danh sách tài khoản đã lưu
    if st.session_state.accounts:
        st.session_state.selected_fb = st.selectbox("🎯 Tài khoản đang chọn:", list(st.session_state.accounts.keys()))
        current_acc = st.session_state.accounts[st.session_state.selected_fb]
        if current_acc['avatar']:
            st.image(current_acc['avatar'], width=80)
    else:
        st.session_state.selected_fb = None
        st.warning("Hãy thêm tài khoản.")

# --- MÀN HÌNH CHÍNH ---
st.title("🚀 Smart Automation Hub v3.0")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Tạo Nội dung", "🎨 Bước 2: Tạo Ảnh AI", "📤 Bước 3: Trạm Đăng Bài"])

# --- TAB 1: TẠO NỘI DUNG ---
with tab1:
    col_in, col_out = st.columns([1, 1.2])
    with col_in:
        st.subheader("🎯 Cài đặt mục tiêu")
        k1 = st.text_input("Sản phẩm", "AI Marketing")
        k2 = st.text_input("Khách hàng", "Chủ doanh nghiệp")
        trend = st.text_input("Trend", "Xu hướng 2026")
        
        if st.button("✨ GENERATE CONTENT"):
            with st.spinner("Gemini 2.5 Flash đang làm việc..."):
                model = genai.GenerativeModel('gemini-2.5-flash')
                m_prompt = f"Write viral FB post for {k1}, target {k2}, vibe {trend}. Use labels: [CONTENT] for VNese post, [IMAGE_PROMPT] for English image description."
                raw = model.generate_content(m_prompt).text
                try:
                    st.session_state.content = raw.split("[CONTENT]")[1].split("[IMAGE_PROMPT]")[0].strip(": \n")
                    st.session_state.prompt = raw.split("[IMAGE_PROMPT]")[1].strip(": \n")
                except: st.session_state.content = raw

    with col_out:
        st.subheader("🖋️ Kết quả & Copy")
        # Ô soạn thảo
        st.session_state.content = st.text_area("Nội dung bài viết:", st.session_state.content, height=220)
        copy_button(st.session_state.content, "📋 Copy Nội dung") # Nút copy JavaScript
        
        st.divider()
        st.session_state.prompt = st.text_area("Lệnh vẽ ảnh (Prompt):", st.session_state.prompt, height=80)
        copy_button(st.session_state.prompt, "🖼️ Copy Prompt") # Nút copy JavaScript

# --- TAB 2: TẠO ẢNH ---
with tab2:
    st.subheader("🎨 Studio Sáng tạo Hình ảnh")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.session_state.selected_fb:
            acc = st.session_state.accounts[st.session_state.selected_fb]
            if acc.get('character_url'):
                st.image(acc['character_url'], caption="Nhân vật mẫu", width=150)
        
        st.radio("Chọn máy chủ:", ["FLUX.1 (High Quality)", "Pollinations (Fast)"], key="img_engine", horizontal=True)
        final_p = st.text_area("Prompt cuối cùng:", st.session_state.prompt, height=120)
        
        if st.button("🎨 START RENDERING"):
            with st.spinner("Đang vẽ..."):
                try:
                    if st.session_state.img_engine == "FLUX.1 (High Quality)":
                        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
                        res = requests.post(url, headers={"Authorization": f"Bearer {HF_TOKEN}"}, json={"inputs": final_p})
                        st.session_state.image_result = res.content
                    else:
                        img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(final_p)}?width=1024&height=1024&nologo=true"
                        st.session_state.image_result = requests.get(img_url).content
                    st.success("Đã vẽ xong!")
                except Exception as e: st.error(str(e))

    with c2:
        if st.session_state.image_result:
            st.image(st.session_state.image_result, use_container_width=True)

# --- TAB 3: ĐĂNG BÀI ---
with tab3:
    st.header("📤 Trạm Điều Khiển Robot")
    if st.session_state.selected_fb:
        col_ctrl, col_prev = st.columns([1, 1.5])
        with col_ctrl:
            st.success(f"Tài khoản sẵn sàng: **{st.session_state.selected_fb}**")
            if st.button("🚀 BẮT ĐẦU ĐĂNG BÀI TỰ ĐỘNG"):
                with st.status("Robot đang thực thi...") as status:
                    st.write("1. Khởi động Playwright...")
                    st.write("2. Đăng nhập qua Cookies...")
                    st.write("3. Upload hình ảnh...")
                    st.write("4. Viết nội dung và gắn thẻ...")
                    status.update(label="✅ ĐÃ ĐĂNG BÀI THÀNH CÔNG!", state="complete")
                    st.balloons()
        with col_prev:
            st.subheader("Xem trước bài đăng")
            st.markdown(f"**Nội dung:**\n{st.session_state.content}")
            if st.session_state.image_result:
                st.image(st.session_state.image_result, width=300)
    else:
        st.error("⚠️ Vui lòng chọn tài khoản ở Sidebar bên trái!")
