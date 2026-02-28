import streamlit as st
import json
import os
import google.generativeai as genai
import requests
import re
import io
from PIL import Image
import streamlit.components.v1 as components
import random

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Automation Hub v3.3", layout="wide")

# --- NÚT COPY JAVASCRIPT ---
def copy_button(text_to_copy, button_label="Copy"):
    safe_text = text_to_copy.replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n")
    code = f"""
    <button onclick="navigator.clipboard.writeText(`{safe_text}`)" 
    style="background-color: #4CAF50; color: white; border: none; padding: 6px 12px; 
    border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold;">
    {button_label}
    </button>
    """
    return components.html(code, height=45)

# --- HÀM TẢI ẢNH AN TOÀN (Vượt lỗi Preview) ---
def load_image_from_url(url):
    if not url: return None
    try:
        # Xử lý link Google Drive
        if "drive.google.com" in url:
            file_id = ""
            if "/file/d/" in url: file_id = url.split("/file/d/")[1].split("/")[0]
            elif "id=" in url: file_id = url.split("id=")[1].split("&")[0]
            if file_id: url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
    except: return None
    return None

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

if 'accounts' not in st.session_state: st.session_state.accounts = load_accounts()
if 'image_result' not in st.session_state: st.session_state.image_result = None

# --- HÀM QUÉT INFO FB ---
def fetch_fb_profile(cookie_str):
    try:
        headers = {
            'cookie': cookie_str,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # Thử lấy ID người dùng
        uid_match = re.search(r'c_user=(\d+)', cookie_str)
        uid = uid_match.group(1) if uid_match else ""
        
        # Thử lấy tên từ trang m.facebook.com (thay vì mbasic)
        res = requests.get("https://m.facebook.com/me", headers=headers, timeout=10)
        name = "Tài khoản Facebook"
        name_match = re.search(r'<title>(.*?)</title>', res.text)
        if name_match:
            name = name_match.group(1).replace(" - Facebook", "").strip()
        
        avatar = f"https://graph.facebook.com/{uid}/picture?type=large" if uid else ""
        return name, uid, avatar
    except:
        return "Lỗi quét", "", ""

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Smart Compliance Hub") # Sử dụng định vị của bạn
    
    with st.expander("🛠️ Quản lý Tài khoản", expanded=True):
        input_cookie = st.text_area("Dán Cookies:", height=70)
        if st.button("🔍 Kiểm tra Cookies"):
            n, u, a = fetch_fb_profile(input_cookie)
            st.session_state.tmp_name, st.session_state.tmp_uid, st.session_state.tmp_avatar = n, u, a
            if u: st.success(f"Live: {n}")
            else: st.error("Cookie Die hoặc không hợp lệ")

        f_name = st.text_input("Tên hiển thị:", st.session_state.get('tmp_name', ""))
        f_uid = st.text_input("UID:", st.session_state.get('tmp_uid', ""))
        f_avatar_url = st.text_input("Link Avatar:", st.session_state.get('tmp_avatar', ""))
        
        # Preview Avatar an toàn
        if f_avatar_url:
            img_avt = load_image_from_url(f_avatar_url)
            if img_avt: st.image(img_avt, width=80)

        st.divider()
        st.write("**Nhân vật mẫu (Cho AI):**")
        char_url = st.text_input("Dán Link Ảnh (Drive/Web):")
        char_file = st.file_uploader("Tải lên từ máy:", type=['jpg', 'png'])
        
        # Preview Ảnh mẫu an toàn
        if char_file: st.image(char_file, width=150)
        elif char_url:
            img_char = load_image_from_url(char_url)
            if img_char: st.image(img_char, width=150)

        if st.button("💾 LƯU VÀO KHO"):
            if f_name and input_cookie:
                st.session_state.accounts[f_name] = {
                    "uid": f_uid, "avatar": f_avatar_url, 
                    "character_url": char_url if char_url else "",
                    "cookies": input_cookie
                }
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu!")
                st.rerun()

    st.divider()
    if st.session_state.accounts:
        st.session_state.selected_fb = st.selectbox("🎯 Chọn tài khoản:", list(st.session_state.accounts.keys()))
        acc = st.session_state.accounts[st.session_state.selected_fb]
        img_side = load_image_from_url(acc['avatar'])
        if img_side: st.image(img_side, width=60)
    else: st.session_state.selected_fb = None

# --- MAIN ---
st.title("🚀 Smart Automation Hub v3.3")
tab1, tab2, tab3 = st.tabs(["📝 Tạo Content", "🎨 Tạo Ảnh AI", "📤 Trạm Đăng Bài"])

with tab1:
    c1, c2 = st.columns([1, 1.2])
    with c1:
        sp = st.text_input("Sản phẩm", "Smart Compliance Hub")
        kh = st.text_input("Đối tượng", "Doanh nghiệp")
        tr = st.text_input("Trend", "Tự động hóa")
        if st.button("✨ VIẾT BÀI"):
            model = genai.GenerativeModel('gemini-2.5-flash')
            res = model.generate_content(f"Write FB post for {sp}, target {kh}. [CONTENT] in Vietnamese, [IMAGE_PROMPT] in English description.").text
            try:
                st.session_state.content = res.split("[CONTENT]")[1].split("[IMAGE_PROMPT]")[0].strip(": \n")
                st.session_state.prompt = res.split("[IMAGE_PROMPT]")[1].strip(": \n")
            except: st.session_state.content = res
    with c2:
        st.session_state.content = st.text_area("Bài viết:", st.session_state.get('content',''), height=200)
        copy_button(st.session_state.content, "📋 Copy Content")
        st.session_state.prompt = st.text_area("Prompt (EN):", st.session_state.get('prompt',''), height=80)
        copy_button(st.session_state.prompt, "🖼️ Copy Prompt")

with tab2:
    st.subheader("🎨 Studio Ảnh")
    cl, cr = st.columns([1, 1])
    with cl:
        engine = st.radio("Chọn Server:", ["Pollinations (Ổn định)", "Flux.1 (Sắc nét)"], horizontal=True)
        p_final = st.text_area("Lệnh vẽ:", st.session_state.get('prompt',''), height=120)
        if st.button("🎨 VẼ ẢNH NGAY"):
            with st.spinner("Đang render..."):
                try:
                    if "Flux" in engine:
                        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
                        r = requests.post(url, headers={"Authorization": f"Bearer {HF_TOKEN}"}, json={"inputs": p_final})
                        if r.status_code == 200: st.session_state.image_result = r.content
                        else: st.error("Flux đang bận.")
                    else:
                        seed = random.randint(1, 99999)
                        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(p_final)}?width=1024&height=1024&nologo=true&seed={seed}"
                        st.session_state.image_result = requests.get(url).content
                        st.success("Đã tải xong!")
                except Exception as e: st.error(f"Lỗi: {e}")
    with cr:
        if st.session_state.image_result:
            try:
                st.image(st.session_state.image_result, use_container_width=True)
            except: st.warning("Dữ liệu ảnh lỗi, hãy thử lại.")

with tab3:
    if st.session_state.selected_fb:
        st.success(f"Sẵn sàng đăng bài bằng nick: **{st.session_state.selected_fb}**")
        if st.button("🚀 BẮT ĐẦU ĐĂNG BÀI"):
            st.info("Chức năng Robot Playwright đang được cấu hình...")
    else: st.error("Hãy chọn tài khoản ở Sidebar.")
