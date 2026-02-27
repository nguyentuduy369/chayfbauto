import streamlit as st
import json
import os
import google.generativeai as genai
import requests
import io
from PIL import Image

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Automation Hub", layout="wide")

# --- LẤY API KEYS TỪ SECRETS ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    HF_TOKEN = st.secrets["HF_TOKEN"]
    genai.configure(api_key=GEMINI_API_KEY)
except:
    st.error("❌ Thiếu GEMINI_API_KEY hoặc HF_TOKEN trong Secrets!")
    st.stop()

# --- HÀM TẠO ẢNH TỪ HUGGING FACE (FLUX.1) ---
def generate_image(prompt):
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    return response.content

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
if 'generated_content' not in st.session_state: st.session_state.generated_content = ""
if 'generated_prompt' not in st.session_state: st.session_state.generated_prompt = ""
if 'final_image' not in st.session_state: st.session_state.final_image = None

# --- SIDEBAR: QUẢN LÝ TÀI KHOẢN ---
with st.sidebar:
    st.header("👤 Quản lý Facebook")
    with st.expander("➕ Thêm Facebook mới"):
        new_name = st.text_input("Tên Facebook")
        new_cookies = st.text_area("Cookies")
        if st.button("Lưu tài khoản"):
            if new_name and new_cookies:
                st.session_state.accounts[new_name] = {"cookies": new_cookies}
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu!")
                st.rerun()

    st.divider()
    # CHỨC NĂNG AVATAR CỐ ĐỊNH
    st.header("🖼️ Avatar Cố Định")
    avatar_method = st.radio("Cách cung cấp Avatar:", ["Link URL", "Tải tệp lên"])
    avatar_data = None
    if avatar_method == "Link URL":
        avatar_data = st.text_input("Dán link ảnh Avatar (Google Drive/Direct link):")
    else:
        avatar_data = st.file_uploader("Chọn ảnh từ máy tính", type=['jpg', 'png', 'jpeg'])

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Smart Content Hub v2.5")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Tạo Content", "🎨 Bước 2: Tạo Ảnh Pro", "📤 Bước 3: Đăng Bài"])

# --- TAB 1: CONTENT ---
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🎯 Thiết lập")
        k1 = st.text_input("Sản phẩm/Dịch vụ", "Khóa học AI")
        k2 = st.text_input("Đối tượng", "Freelancer")
        trend = st.text_input("Trend hôm nay", "Năng lượng tích cực")
        
        if st.button("✨ TẠO NỘI DUNG"):
            with st.spinner("Gemini đang sáng tạo..."):
                model = genai.GenerativeModel('gemini-2.5-flash')
                # Master Prompt vạn năng
                prompt = f"Bạn là chuyên gia Marketing. Tạo bài đăng FB về {k1} cho {k2}, vibe {trend}. [CONTENT]: Tiếng Việt, Hook mạnh, CTA. [IMAGE_PROMPT]: Tiếng Anh, mô tả ảnh Realistic, Cinematic, 8k, phù hợp bài viết."
                response = model.generate_content(prompt)
                res = response.text
                if "[IMAGE_PROMPT]" in res:
                    parts = res.split("[IMAGE_PROMPT]")
                    st.session_state.generated_content = parts[0].replace("[CONTENT]", "").strip()
                    st.session_state.generated_prompt = parts[1].strip()
                else: st.session_state.generated_content = res

    with col2:
        st.session_state.generated_content = st.text_area("Bài đăng:", st.session_state.generated_content, height=250)
        st.session_state.generated_prompt = st.text_area("Prompt vẽ ảnh:", st.session_state.generated_prompt, height=100)

# --- TAB 2: TẠO ẢNH ---
with tab2:
    st.subheader("🎨 Studio Tạo Ảnh AI")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.write("Cấu hình ảnh dựa trên Avatar của bạn:")
        if avatar_data:
            st.success("✅ Đã nhận diện Avatar cố định")
        else:
            st.warning("⚠️ Bạn chưa cung cấp Avatar ở Sidebar (nhưng vẫn có thể tạo ảnh minh họa chung).")
        
        # Tối ưu hóa prompt một lần nữa trước khi vẽ
        final_prompt = st.text_area("Prompt cuối cùng (Có thể chỉnh sửa):", st.session_state.generated_prompt)
        
        if st.button("🎨 VẼ ẢNH NGAY"):
            with st.spinner("Đang vẽ ảnh (Mất khoảng 10-20 giây)..."):
                try:
                    img_bytes = generate_image(final_prompt)
                    st.session_state.final_image = img_bytes
                    st.success("Vẽ xong!")
                except Exception as e:
                    st.error(f"Lỗi khi vẽ ảnh: {e}")

    with c2:
        if st.session_state.final_image:
            st.image(st.session_state.final_image, caption="Ảnh đã tạo", use_container_width=True)
            # Nút tải ảnh về để kiểm tra thủ công
            st.download_button("📥 Tải ảnh về máy", data=st.session_state.final_image, file_name="facebook_post.png", mime="image/png")

# --- TAB 3: ĐĂNG BÀI ---
with tab3:
    st.info("Đang chờ robot Playwright để đăng bài tự động.")
