import streamlit as st
import json
import os
import google.generativeai as genai

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Facebook Automation Hub", layout="wide")

# --- LẤY API KEY TỪ SECRETS (BẢO MẬT) ---
# Code sẽ tự tìm GEMINI_API_KEY bạn đã dán trong phần Settings của Streamlit
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("❌ Chưa tìm thấy API Key trong Secrets. Vui lòng kiểm tra lại cài đặt Streamlit.")
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
if 'generated_content' not in st.session_state: st.session_state.generated_content = ""
if 'generated_prompt' not in st.session_state: st.session_state.generated_prompt = ""

# --- SIDEBAR: QUẢN LÝ TÀI KHOẢN ---
with st.sidebar:
    st.header("👤 Quản lý Facebook")
    with st.expander("➕ Thêm Facebook mới"):
        new_name = st.text_input("Tên Facebook")
        new_id = st.text_input("ID/Số hiệu")
        new_cookies = st.text_area("Cookies")
        if st.button("Lưu tài khoản"):
            if new_name and new_cookies:
                st.session_state.accounts[new_name] = {"id": new_id, "cookies": new_cookies}
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu thành công!")
                st.rerun()
            else: st.error("Vui lòng điền đủ Tên và Cookies")

    st.divider()
    if st.session_state.accounts:
        fb_list = list(st.session_state.accounts.keys())
        selected = st.selectbox("Chọn Facebook làm việc:", fb_list)
        st.session_state.selected_fb = selected
    else: st.warning("Hãy thêm tài khoản ở trên.")

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Smart Content Hub")



tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Tạo Content Trend", "🎨 Bước 2: Tạo Ảnh AI Pro", "📤 Bước 3: Đăng Bài"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🎯 Thiết lập mục tiêu")
        k1 = st.text_input("Sản phẩm/Chủ đề chính", placeholder="Ví dụ: Mỹ phẩm thuần chay")
        k2 = st.text_input("Đối tượng mục tiêu", placeholder="Ví dụ: Phụ nữ công sở 25-35 tuổi")
        trend = st.text_input("Trend/Vibe hôm nay (Tùy chọn)", placeholder="Ví dụ: Cuối tuần chill...")
        
        master_prompt = f"""
        Bạn là chuyên gia Viral Marketing. Tạo nội dung:
        - Chủ đề: {k1}, Đối tượng: {k2}, Trend: {trend}
        
        ĐỊNH DẠNG TRẢ VỀ:
        [CONTENT]: Nội dung bài đăng (Hook mạnh, icon, hashtag).
        [IMAGE_PROMPT]: Đoạn prompt tiếng Anh chi tiết để AI vẽ ảnh (Realistic, 8k, cinematic).
        """

        if st.button("✨ TẠO NỘI DUNG MỚI"):
            with st.spinner("Đang kết nối Gemini qua Secrets..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(master_prompt)
                    res_text = response.text
                    
                    if "[IMAGE_PROMPT]" in res_text:
                        parts = res_text.split("[IMAGE_PROMPT]")
                        st.session_state.generated_content = parts[0].replace("[CONTENT]", "").strip()
                        st.session_state.generated_prompt = parts[1].strip()
                    else:
                        st.session_state.generated_content = res_text
                    st.success("Cập nhật thành công!")
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")

    with col2:
        st.subheader("🖋️ Tinh chỉnh thủ công")
        st.session_state.generated_content = st.text_area("Nội dung bài đăng:", st.session_state.generated_content, height=300)
        st.session_state.generated_prompt = st.text_area("Prompt cho AI vẽ ảnh:", st.session_state.generated_prompt, height=150)
        if st.button("✅ Chốt nội dung này"):
            st.toast("Đã lưu!")

with tab2:
    st.info("Module Bước 2 đang chờ API tạo ảnh (NaNa Pro).")

with tab3:
    st.info("Module Bước 3 đang chờ robot đăng bài.")
