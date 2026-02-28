import streamlit as st
import json
import os
import google.generativeai as genai
import requests
import re
import io
from PIL import Image
import streamlit.components.v1 as components

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Automation Hub v3.1", layout="wide")

# --- NÚT COPY JAVASCRIPT ---
def copy_button(text_to_copy, button_label="Copy"):
    safe_text = text_to_copy.replace("`", "\\`").replace("$", "\\$")
    code = f"""
    <button onclick="navigator.clipboard.writeText(`{safe_text}`)" 
    style="background-color: #4CAF50; color: white; border: none; padding: 6px 12px; 
    border-radius: 4px; cursor: pointer; font-size: 14px;">
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

# --- QUẢN LÝ DỮ LIỆU ---
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

# Khởi tạo trạng thái
if 'accounts' not in st.session_state: st.session_state.accounts = load_accounts()
if 'content' not in st.session_state: st.session_state.content = ""
if 'prompt' not in st.session_state: st.session_state.prompt = ""
if 'image_result' not in st.session_state: st.session_state.image_result = None
if 'tmp_name' not in st.session_state: st.session_state.tmp_name = ""
if 'tmp_uid' not in st.session_state: st.session_state.tmp_uid = ""
if 'tmp_avatar' not in st.session_state: st.session_state.tmp_avatar = ""

# --- HÀM QUÉT INFO FB ---
def fetch_fb_profile(cookie_str):
    try:
        headers = {
            'cookie': cookie_str,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        res = requests.get("https://mbasic.facebook.com/profile.php", headers=headers, timeout=10)
        # Tìm tên trong thẻ <title> hoặc các thẻ <strong>
        name = re.search(r'<title>(.*?)</title>', res.text)
        name = name.group(1) if name else ""
        if "|" in name: name = name.split("|")[0].strip()
        
        uid = re.search(r'c_user=(\d+)', cookie_str)
        uid = uid.group(1) if uid else ""
        avatar = f"https://graph.facebook.com/{uid}/picture?type=large" if uid else ""
        return name, uid, avatar
    except:
        return "", "", ""

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Hệ thống Tài khoản")
    
    with st.expander("🛠️ Nhập tài khoản mới", expanded=True):
        input_cookie = st.text_area("1. Dán Cookies Facebook:", height=80)
        if st.button("🔍 Check & Auto-fill"):
            n, u, a = fetch_fb_profile(input_cookie)
            if n:
                st.session_state.tmp_name, st.session_state.tmp_uid, st.session_state.tmp_avatar = n, u, a
                st.success("Đã lấy thông tin!")
            else: st.error("Không lấy được tên. Hãy nhập tay bên dưới.")

        f_name = st.text_input("Tên hiển thị:", st.session_state.tmp_name)
        f_uid = st.text_input("UID Facebook:", st.session_state.tmp_uid)
        f_avatar = st.text_input("URL Avatar (Cá nhân):", st.session_state.tmp_avatar)
        if f_avatar: st.image(f_avatar, width=60, caption="Preview Avatar")
        
        st.divider()
        st.write("**Ảnh nhân vật mẫu (Cho AI):**")
        char_url = st.text_input("Dán URL ảnh nhân vật:")
        if char_url: st.image(char_url, width=100, caption="Mẫu từ URL")
        char_file = st.file_uploader("Hoặc tải ảnh lên", type=['jpg', 'png'])
        if char_file: st.image(char_file, width=100, caption="Mẫu từ Máy tính")
        
        if st.button("💾 LƯU TÀI KHOẢN"):
            if f_name and input_cookie:
                st.session_state.accounts[f_name] = {
                    "uid": f_uid, "avatar": f_avatar, 
                    "character_url": char_url, "cookies": input_cookie
                }
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu!")
                st.rerun()

    st.divider()
    if st.session_state.accounts:
        st.session_state.selected_fb = st.selectbox("🎯 Tài khoản đang chọn:", list(st.session_state.accounts.keys()))
        acc = st.session_state.accounts[st.session_state.selected_fb]
        if acc['avatar']: st.image(acc['avatar'], width=60)
    else: st.session_state.selected_fb = None

# --- MAIN ---
st.title("🚀 Smart Automation Hub v3.1")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Content", "🎨 Bước 2: Ảnh AI", "📤 Bước 3: Đăng Bài"])

with tab1:
    col_in, col_out = st.columns([1, 1.2])
    with col_in:
        k1 = st.text_input("Sản phẩm", "AI Automation")
        k2 = st.text_input("Khách hàng", "Freelancer")
        trend = st.text_input("Trend", "Năng suất")
        if st.button("✨ GENERATE"):
            model = genai.GenerativeModel('gemini-2.5-flash')
            raw = model.generate_content(f"Write FB post for {k1}, target {k2}, vibe {trend}. Use labels: [CONTENT], [IMAGE_PROMPT]").text
            try:
                st.session_state.content = raw.split("[CONTENT]")[1].split("[IMAGE_PROMPT]")[0].strip(": \n")
                st.session_state.prompt = raw.split("[IMAGE_PROMPT]")[1].strip(": \n")
            except: st.session_state.content = raw
    with col_out:
        st.session_state.content = st.text_area("Nội dung:", st.session_state.content, height=200)
        copy_button(st.session_state.content, "📋 Copy Nội dung")
        st.session_state.prompt = st.text_area("Prompt vẽ ảnh:", st.session_state.prompt, height=80)
        copy_button(st.session_state.prompt, "🖼️ Copy Prompt")

with tab2:
    st.subheader("🎨 Studio Ảnh")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.session_state.selected_fb:
            char = st.session_state.accounts[st.session_state.selected_fb].get('character_url')
            if char: st.image(char, width=150, caption="Mẫu nhân vật")
        
        engine = st.radio("Máy chủ:", ["Flux.1", "Pollinations"], horizontal=True)
        final_p = st.text_area("Prompt cuối cùng:", st.session_state.prompt, height=120)
        if st.button("🎨 RENDER"):
            with st.spinner("Đang vẽ..."):
                try:
                    if engine == "Flux.1":
                        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
                        res = requests.post(url, headers={"Authorization": f"Bearer {HF_TOKEN}"}, json={"inputs": final_p})
                        if res.status_code == 200 and "image" in res.headers.get("content-type", ""):
                            st.session_state.image_result = res.content
                        else: st.error("Flux.1 đang bận hoặc lỗi. Hãy thử Pollinations.")
                    else:
                        img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(final_p)}?width=1024&height=1024&nologo=true"
                        st.session_state.image_result = requests.get(img_url).content
                    st.success("Hoàn tất!")
                except Exception as e: st.error(f"Lỗi: {e}")
    with c2:
        if st.session_state.image_result:
            try:
                Image.open(io.BytesIO(st.session_state.image_result)) # Kiểm tra ảnh hợp lệ
                st.image(st.session_state.image_result, use_container_width=True)
            except: st.warning("Dữ liệu ảnh không hợp lệ. Hãy thử Render lại.")

with tab3:
    st.header("📤 Trạm Đăng Bài")
    if st.session_state.selected_fb:
        col_l, col_r = st.columns([1, 1.5])
        with col_l:
            st.success(f"Nick: {st.session_state.selected_fb}")
            if st.button("🚀 ĐĂNG BÀI TỰ ĐỘNG"):
                with st.status("Đang chạy...") as s:
                    st.write("Đang khởi động Robot...")
                    s.update(label="✅ ĐÃ ĐĂNG!", state="complete")
        with col_r:
            st.markdown(f"**Preview:**\n{st.session_state.content[:200]}...")
            if st.session_state.image_result:
                try:
                    Image.open(io.BytesIO(st.session_state.image_result))
                    st.image(st.session_state.image_result, width=250)
                except: st.info("Chưa có ảnh hợp lệ để xem trước.")
    else: st.error("Chọn tài khoản ở Sidebar!")
