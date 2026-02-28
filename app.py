import streamlit as st
import json
import os
import google.generativeai as genai
import requests
import re

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Automation Hub", layout="wide")

# --- LẤY API KEYS ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    HF_TOKEN = st.secrets["HF_TOKEN"]
    genai.configure(api_key=GEMINI_API_KEY)
except:
    st.error("❌ Thiếu API Key trong Secrets!")
    st.stop()

# --- HÀM LẤY THÔNG TIN FB TỪ COOKIE ---
def get_fb_info(cookie_str):
    try:
        headers = {
            'cookie': cookie_str,
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1'
        }
        # Lấy UID từ cookie (thường là c_user)
        uid = re.search(r'c_user=(\d+)', cookie_str)
        uid = uid.group(1) if uid else "Không tìm thấy UID"
        
        # Gọi mbasic để lấy tên và avatar
        res = requests.get("https://mbasic.facebook.com/profile.php", headers=headers, timeout=10)
        name = re.search(r'<title>(.*?)</title>', res.text)
        name = name.group(1) if name else "Facebook User"
        
        # Link avatar mặc định từ UID
        avatar = f"https://graph.facebook.com/{uid}/picture?type=large" if uid.isdigit() else ""
        
        return {"name": name, "uid": uid, "avatar": avatar, "status": "Live ✅"}
    except:
        return {"name": "", "uid": "", "avatar": "", "status": "Die/Error ❌"}

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
if 'content' not in st.session_state: st.session_state.content = ""
if 'prompt' not in st.session_state: st.session_state.prompt = ""
if 'image_result' not in st.session_state: st.session_state.image_result = None

# --- SIDEBAR: QUẢN LÝ TỰ ĐỘNG ---
with st.sidebar:
    st.header("👤 Hệ thống Tài khoản")
    
    with st.expander("🛠️ Kiểm tra & Thêm nhanh", expanded=True):
        input_cookie = st.text_area("1. Dán Cookies vào đây:", height=100)
        
        # Khởi tạo thông tin tạm
        if 'tmp_info' not in st.session_state:
            st.session_state.tmp_info = {"name": "", "uid": "", "avatar": "", "status": ""}

        if st.button("🔍 Kiểm tra & Lấy thông tin"):
            with st.spinner("Đang quét..."):
                st.session_state.tmp_info = get_fb_info(input_cookie)
        
        st.write(f"Trạng thái: **{st.session_state.tmp_info['status']}**")
        
        # Form xác nhận thông tin (Tự động điền)
        final_name = st.text_input("Tên hiển thị:", st.session_state.tmp_info['name'])
        final_uid = st.text_input("UID Facebook:", st.session_state.tmp_info['uid'])
        
        st.write("Link Avatar (Tự động lấy):")
        final_avatar = st.text_input("URL Avatar:", st.session_state.tmp_info['avatar'], label_visibility="collapsed")
        
        uploaded_file = st.file_uploader("Hoặc tải ảnh từ máy tính", type=['jpg','png'])
        
        if st.button("💾 LƯU VÀO KHO"):
            if final_name and input_cookie:
                # Ưu tiên ảnh upload
                avatar_to_save = final_avatar
                st.session_state.accounts[final_name] = {
                    "id": final_uid,
                    "avatar": avatar_to_save,
                    "cookies": input_cookie
                }
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu!")
                st.rerun()

    st.divider()
    if st.session_state.accounts:
        selected = st.selectbox("🎯 Chọn Nick đang chạy:", list(st.session_state.accounts.keys()))
        st.session_state.selected_fb = selected
        acc = st.session_state.accounts[selected]
        if acc['avatar']: st.image(acc['avatar'], width=100)

# --- MÀN HÌNH CHÍNH ---
st.title("🚀 Smart Content Hub v2.8")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Tạo Content", "🎨 Bước 2: Tạo Ảnh AI", "📤 Bước 3: Đăng Bài"])

# --- TAB 1: CONTENT (UI TIN GỌN) ---
with tab1:
    col_in, col_out = st.columns([1, 1.2])
    with col_in:
        st.subheader("🎯 Ý tưởng")
        k1 = st.text_input("Chủ đề", "Máy lọc nước")
        k2 = st.text_input("Đối tượng", "Gia đình")
        trend = st.text_input("Trend", "Sống sạch")
        if st.button("✨ TẠO MỚI"):
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"Marketing. Subject: {k1}, Target: {k2}, Vibe: {trend}. [CONTENT]: VNese, viral. [IMAGE_PROMPT]: English, realistic 8k."
            res = model.generate_content(prompt).text
            c_part = re.search(r"\[CONTENT\](.*?)(?=\[IMAGE_PROMPT\]|$)", res, re.S | re.I)
            p_part = re.search(r"\[IMAGE_PROMPT\](.*)", res, re.S | re.I)
            st.session_state.content = c_part.group(1).strip(": \n") if c_part else res
            st.session_state.prompt = p_part.group(1).strip(": \n") if p_part else ""

    with col_out:
        st.subheader("🖋️ Kết quả")
        st.session_state.content = st.text_area("Bài viết:", st.session_state.content, height=200)
        # Nút copy tinh gọn bằng st.code (có biểu tượng copy sẵn)
        st.code(st.session_state.content, language="text") 
        
        st.divider()
        st.session_state.prompt = st.text_area("Prompt ảnh:", st.session_state.prompt, height=80)
        st.code(st.session_state.prompt, language="text")

# --- TAB 2: TẠO ẢNH (BỔ SUNG MÁY CHỦ DỰ PHÒNG) ---
with tab2:
    st.subheader("🎨 Studio Tạo Ảnh AI")
    c1, c2 = st.columns([1, 1])
    with c1:
        engine = st.radio("Chọn máy chủ vẽ ảnh:", ["Pollinations (Nhanh/Miễn phí)", "Flux.1 (Chân thật/Hay bận)"], horizontal=True)
        final_p = st.text_area("Xác nhận lệnh vẽ:", st.session_state.prompt, height=150)
        
        if st.button("🎨 BẮT ĐẦU VẼ"):
            with st.spinner("Đang xử lý ảnh..."):
                try:
                    if engine == "Pollinations (Nhanh/Miễn phí)":
                        # Pollinations API cực kỳ bền và nhanh
                        img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(final_p)}?width=1024&height=1024&nologo=true"
                        st.session_state.image_result = requests.get(img_url).content
                    else:
                        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
                        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
                        response = requests.post(url, headers=headers, json={"inputs": final_p})
                        if response.status_code == 200:
                            st.session_state.image_result = response.content
                        else: st.error("Flux.1 đang quá tải, hãy chọn Pollinations!")
                    st.success("Vẽ xong!")
                except Exception as e: st.error(f"Lỗi: {e}")

    with c2:
        if st.session_state.image_result:
            st.image(st.session_state.image_result, use_container_width=True)
            st.download_button("📥 Tải ảnh", st.session_state.image_result, "post.png", "image/png")

with tab3:
    st.info("Sẵn sàng cho Bước 3: Robot Playwright đăng bài tự động.")
