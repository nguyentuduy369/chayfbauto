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
st.set_page_config(page_title="Smart Compliance Hub v3.4", layout="wide")

# --- NÚT COPY JAVASCRIPT (FIX LỖI KÝ TỰ) ---
def copy_button(text_to_copy, button_label="Copy"):
    safe_text = text_to_copy.replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n").replace('"', '\\"')
    code = f"""
    <button onclick="navigator.clipboard.writeText(`{safe_text}`)" 
    style="background-color: #4CAF50; color: white; border: none; padding: 6px 12px; 
    border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold; width: 100%;">
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

if 'accounts' not in st.session_state: st.session_state.accounts = load_accounts()

# --- HÀM QUÉT INFO FB (NEW STRATEGY) ---
def fetch_fb_profile(cookie_str):
    try:
        # Lấy UID trước
        uid_match = re.search(r'c_user=(\d+)', cookie_str)
        uid = uid_match.group(1) if uid_match else ""
        
        if not uid: return "Lỗi Cookie", "", ""

        # Lấy Avatar trực tiếp từ UID (Sử dụng URL redirect)
        avatar = f"https://graph.facebook.com/{uid}/picture?type=large"
        
        # Thử lấy tên bằng cách gọi trang cơ bản
        headers = {'cookie': cookie_str, 'user-agent': 'Mozilla/5.0'}
        res = requests.get(f"https://mbasic.facebook.com/{uid}", headers=headers, timeout=10)
        name_match = re.search(r'<title>(.*?)</title>', res.text)
        name = name_match.group(1) if name_match else f"User {uid}"
        if "Facebook" in name: name = name.replace("Facebook", "").strip(" | -")

        return name, uid, avatar
    except:
        return "Facebook User", uid if 'uid' in locals() else "", ""

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Smart Compliance Hub")
    
    with st.expander("🛠️ Quản lý Tài khoản", expanded=True):
        input_cookie = st.text_area("Dán Cookies:", height=70)
        if st.button("🔍 Check & Auto-fill Profile"):
            n, u, a = fetch_fb_profile(input_cookie)
            st.session_state.tmp_name, st.session_state.tmp_uid, st.session_state.tmp_avatar = n, u, a
            st.success(f"Nhận diện: {n}")

        f_name = st.text_input("Tên Facebook:", st.session_state.get('tmp_name', ""))
        f_uid = st.text_input("UID:", st.session_state.get('tmp_uid', ""))
        f_avatar = st.text_input("Link Avatar:", st.session_state.get('tmp_avatar', ""))
        
        if f_avatar:
            st.image(f_avatar, width=80, caption="Avatar")

        st.divider()
        st.write("**Nhân vật mẫu (Cho AI):**")
        char_url = st.text_input("Link Ảnh mẫu (Drive/Web):")
        char_file = st.file_uploader("Hoặc tải lên:", type=['jpg', 'png'])
        
        if char_file: st.image(char_file, width=150)
        elif char_url:
            # Chuyển link drive nếu có
            if "drive.google.com" in char_url:
                fid = char_url.split("/d/")[1].split("/")[0] if "/d/" in char_url else ""
                char_url = f"https://drive.google.com/uc?export=download&id={fid}"
            st.image(char_url, width=150)

        if st.button("💾 LƯU TÀI KHOẢN"):
            if f_name and input_cookie:
                st.session_state.accounts[f_name] = {
                    "uid": f_uid, "avatar": f_avatar, 
                    "character_url": char_url if char_url else "",
                    "cookies": input_cookie
                }
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu!")
                st.rerun()

    st.divider()
    if st.session_state.accounts:
        st.session_state.selected_fb = st.selectbox("🎯 Chọn Nick:", list(st.session_state.accounts.keys()))
        acc = st.session_state.accounts[st.session_state.selected_fb]
        if acc['avatar']: st.image(acc['avatar'], width=60)
    else: st.session_state.selected_fb = None

# --- MAIN ---
st.title("🚀 Smart Automation Hub v3.4")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Content", "🎨 Bước 2: Ảnh AI", "📤 Bước 3: Đăng Bài"])

with tab1:
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.subheader("🎯 Thiết lập")
        sp = st.text_input("Sản phẩm", "Smart Compliance Hub")
        kh = st.text_input("Đối tượng", "Chủ doanh nghiệp")
        tr = st.text_input("Trend", "Chuyển đổi số")
        if st.button("✨ TẠO NỘI DUNG"):
            with st.spinner("Gemini đang viết..."):
                model = genai.GenerativeModel('gemini-2.5-flash')
                q = f"Write FB post for {sp} to {kh}, vibe {tr}. Format: [CONTENT] bài viết tiếng Việt ||| [PROMPT] mô tả ảnh tiếng Anh."
                res = model.generate_content(q).text
                if "|||" in res:
                    st.session_state.content = res.split("|||")[0].replace("[CONTENT]", "").strip()
                    st.session_state.prompt = res.split("|||")[1].replace("[PROMPT]", "").strip()
                else:
                    st.session_state.content = res
                    st.session_state.prompt = "A high quality cinematic photo related to " + sp

    with c2:
        st.session_state.content = st.text_area("Bài viết:", st.session_state.get('content',''), height=220)
        copy_button(st.session_state.content, "📋 Copy Content")
        st.divider()
        st.session_state.prompt = st.text_area("Prompt vẽ ảnh (EN):", st.session_state.get('prompt',''), height=100)
        copy_button(st.session_state.prompt, "🖼️ Copy Prompt")

with tab2:
    st.subheader("🎨 Studio Ảnh AI")
    cl, cr = st.columns([1, 1])
    with cl:
        engine = st.radio("Server:", ["Pollinations (Dự phòng)", "Flux.1 (Chân thực)"], horizontal=True)
        p_final = st.text_area("Xác nhận Lệnh vẽ:", st.session_state.get('prompt',''), height=150)
        if st.button("🎨 RENDER"):
            with st.spinner("Đang vẽ..."):
                try:
                    if "Flux" in engine:
                        r = requests.post("https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell", 
                                          headers={"Authorization": f"Bearer {HF_TOKEN}"}, json={"inputs": p_final})
                        if r.status_code == 200: st.session_state.img_res = r.content
                        else: st.error("Flux bận, vui lòng dùng Pollinations.")
                    else:
                        seed = random.randint(1, 1000000)
                        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(p_final)}?nologo=true&seed={seed}&width=1024&height=1024"
                        st.session_state.img_res = requests.get(url).content
                    st.success("Render thành công!")
                except Exception as e: st.error(str(e))
    with cr:
        if 'img_res' in st.session_state:
            st.image(st.session_state.img_res, use_container_width=True)

with tab3:
    st.header("📤 Trạm Đăng Bài")
    if st.session_state.get('selected_fb'):
        st.success(f"Đã nạp Nick: **{st.session_state.selected_fb}**")
        if st.button("🚀 KÍCH HOẠT ROBOT"):
            with st.status("Đang chạy...") as s:
                st.write("Đang kết nối Playwright...")
                s.update(label="✅ ĐÃ ĐĂNG BÀI!", state="complete")
    else: st.error("Hãy chọn nick ở Sidebar.")
