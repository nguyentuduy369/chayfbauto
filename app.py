import streamlit as st
import json
import os
import google.generativeai as genai
import requests
import re

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Automation Hub", layout="wide")

# --- LẤY API KEYS TỪ SECRETS ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    hf_token = st.secrets["HF_TOKEN"]
    genai.configure(api_key=api_key)
except:
    st.error("❌ Thiếu API Key trong Secrets. Vui lòng kiểm tra GEMINI_API_KEY và HF_TOKEN.")
    st.stop()

# --- QUẢN LÝ TÀI KHOẢN ---
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

# Khởi tạo trạng thái hệ thống
if 'accounts' not in st.session_state: st.session_state.accounts = load_accounts()
if 'content' not in st.session_state: st.session_state.content = ""
if 'prompt' not in st.session_state: st.session_state.prompt = ""
if 'image_result' not in st.session_state: st.session_state.image_result = None

# --- SIDEBAR: CHỌN FACEBOOK ---
with st.sidebar:
    st.header("👤 Tài khoản làm việc")
    if st.session_state.accounts:
        fb_list = list(st.session_state.accounts.keys())
        st.session_state.selected_fb = st.selectbox("Chọn Facebook:", fb_list)
    else:
        st.warning("Hãy thêm tài khoản ở nút bên dưới.")
    
    with st.expander("➕ Thêm mới/Cập nhật"):
        name = st.text_input("Tên FB")
        cookie = st.text_area("Cookies")
        if st.button("Lưu"):
            if name and cookie:
                st.session_state.accounts[name] = {"cookies": cookie}
                save_accounts(st.session_state.accounts)
                st.rerun()

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Smart Content Hub v2.5")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Tạo Content", "🎨 Bước 2: Tạo Ảnh Pro", "📤 Bước 3: Đăng Bài"])

# --- BƯỚC 1: TẠO CONTENT ---
with tab1:
    col_in, col_out = st.columns([1, 1.2])
    
    with col_in:
        st.subheader("🎯 Nhập ý tưởng")
        k1 = st.text_input("Chủ đề chính", "Máy lọc nước Hydrogen")
        k2 = st.text_input("Đối tượng", "Gia đình quan tâm sức khỏe")
        trend = st.text_input("Bối cảnh/Trend", "Cuối tuần sum họp")
        
        if st.button("✨ TẠO NỘI DUNG VỚI GEMINI"):
            with st.spinner("Đang sáng tạo..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    master_prompt = f"""
                    Bạn là chuyên gia Viral Marketing. Tạo nội dung cho {k1}, khách là {k2}, vibe {trend}.
                    Định dạng bắt buộc:
                    [CONTENT]: Nội dung bài đăng (Tiếng Việt, hook mạnh, icon).
                    [IMAGE_PROMPT]: Đoạn mô tả ảnh chuyên sâu (Tiếng Anh, Realistic, 8k, cinematic).
                    """
                    response = model.generate_content(master_prompt)
                    raw_text = response.text
                    
                    # Tách nội dung bằng biểu thức chính quy (Regex) để tránh lỗi gộp
                    content_match = re.search(r"\[CONTENT\]:(.*?)(?=\[IMAGE_PROMPT\]|$)", raw_text, re.S)
                    prompt_match = re.search(r"\[IMAGE_PROMPT\]:(.*)", raw_text, re.S)
                    
                    st.session_state.content = content_match.group(1).strip() if content_match else raw_text
                    st.session_state.prompt = prompt_match.group(1).strip() if prompt_match else ""
                    st.success("Đã tạo xong!")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    with col_out:
        st.subheader("✒️ Chỉnh sửa & Sao chép")
        st.session_state.content = st.text_area("Bài đăng Facebook:", st.session_state.content, height=250)
        
        # Ô Prompt có nút copy nhanh (Streamlit tự có nút copy ở góc trên bên phải st.code)
        st.write("**Prompt tạo ảnh (Copy sang Bước 2):**")
        st.code(st.session_state.prompt, language="text")
        
        if st.button("✅ CHỐT NỘI DUNG"):
            st.toast("Dữ liệu đã sẵn sàng!")

# --- BƯỚC 2: TẠO ẢNH ---
with tab2:
    st.subheader("🎨 Studio Tạo Ảnh AI")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        # CHỨC NĂNG AVATAR CỐ ĐỊNH (MỚI)
        st.markdown("### 🖼️ Cài đặt Avatar")
        avatar_type = st.radio("Nguồn Avatar:", ["Dùng Link URL", "Tải tệp lên"], horizontal=True)
        if avatar_type == "Dùng Link URL":
            st.text_input("Dán link ảnh (Google Drive/Public):", key="avatar_url")
        else:
            st.file_uploader("Chọn ảnh từ máy tính", type=['jpg', 'png', 'jpeg'], key="avatar_file")
        
        st.divider()
        input_prompt = st.text_area("Dán/Chỉnh sửa Prompt tại đây:", st.session_state.prompt, height=150)
        
        if st.button("🎨 VẼ ẢNH NGAY"):
            with st.spinner("Đang vẽ ảnh với FLUX.1 (Hugging Face)..."):
                try:
                    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
                    headers = {"Authorization": f"Bearer {hf_token}"}
                    response = requests.post(API_URL, headers=headers, json={"inputs": input_prompt})
                    
                    if response.status_code == 200:
                        st.session_state.image_result = response.content
                        st.success("Vẽ xong!")
                    else:
                        st.error(f"Lỗi từ Hugging Face: {response.status_code}")
                except Exception as e:
                    st.error(f"Lỗi kết nối: {e}")

    with c2:
        st.markdown("### 👁️ Xem trước")
        if st.session_state.image_result:
            st.image(st.session_state.image_result, use_container_width=True)
            st.download_button("📥 Tải ảnh về", st.session_state.image_result, "post_image.png", "image/png")
        else:
            st.info("Ảnh sẽ hiện ở đây sau khi bạn nhấn 'Vẽ ảnh ngay'.")

# --- BƯỚC 3: ĐĂNG BÀI ---
with tab3:
    st.info("Module Bước 3: Đang chờ thiết lập Robot đăng bài (Playwright).")
