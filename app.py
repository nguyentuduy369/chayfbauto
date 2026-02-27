import streamlit as st
import json
import os
import google.generativeai as genai

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Automation Hub", layout="wide")

# --- LẤY API KEY TỪ SECRETS (BẢO MẬT) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("❌ Chưa tìm thấy API Key trong Secrets. Vui lòng vào Settings -> Secrets và thêm GEMINI_API_KEY.")
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
        new_name = st.text_input("Tên Facebook (Gợi nhớ)")
        new_id = st.text_input("ID/Mã số")
        new_cookies = st.text_area("Cookies Facebook")
        if st.button("Lưu tài khoản"):
            if new_name and new_cookies:
                st.session_state.accounts[new_name] = {"id": new_id, "cookies": new_cookies}
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu!")
                st.rerun()
            else: st.error("Điền thiếu thông tin!")

    st.divider()
    if st.session_state.accounts:
        fb_list = list(st.session_state.accounts.keys())
        selected = st.selectbox("Chọn tài khoản làm việc:", fb_list)
        st.session_state.selected_fb = selected
    else: st.warning("Vui lòng thêm tài khoản.")

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Smart Content Hub v2.5")

tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Tạo Content Viral", "🎨 Bước 2: Tạo Ảnh AI Pro", "📤 Bước 3: Đăng Bài"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🎯 Đầu vào thông minh")
        k1 = st.text_input("Sản phẩm / Dịch vụ của bạn", placeholder="Ví dụ: Khóa học AI cho người không biết code")
        k2 = st.text_input("Đối tượng khách hàng cụ thể", placeholder="Ví dụ: Chủ doanh nghiệp nhỏ, Freelancer")
        trend = st.text_input("Bối cảnh / Trend hôm nay", placeholder="Ví dụ: Đầu tuần bận rộn, trời se lạnh...")
        
        # --- MASTER PROMPT VẠN NĂNG (Đã tối ưu cho Gemini 2.5 Flash) ---
        master_prompt = f"""
        Bạn là một Giám đốc Sáng tạo (Creative Director) và chuyên gia Viral Marketing xuất sắc trên Facebook. 
        Hãy tạo nội dung dựa trên:
        - Chủ đề: {k1}
        - Đối tượng: {k2}
        - Bối cảnh: {trend}

        NHIỆM VỤ 1: [CONTENT] (Tiếng Việt)
        - Cấu trúc bài viết chuẩn AIDA (Attention, Interest, Desire, Action).
        - Câu mở đầu (Hook): Phải cực kỳ thu hút, đánh vào nỗi đau (Pain point) hoặc sự tò mò của {k2}.
        - Thân bài: Ngắn gọn, súc tích, sử dụng các gạch đầu dòng và icon sinh động.
        - Giọng văn: Gần gũi, đáng tin cậy nhưng vẫn chuyên nghiệp.
        - Kết luận: Một lời kêu gọi hành động (CTA) mạnh mẽ và 1 câu hỏi để tăng comment tương tác.
        - Hashtag: 5 hashtag (3 hashtag ngách, 2 hashtag xu hướng).

        NHIỆM VỤ 2: [IMAGE_PROMPT] (Tiếng Anh)
        - Tạo 1 câu lệnh vẽ ảnh chi tiết cho AI (như Midjourney/DALL-E).
        - Phong cách: Photorealistic, Cinematic Lighting, 8k resolution.
        - Nội dung ảnh: Phải có sự xuất hiện của nhân vật đại diện cho {k2} trong bối cảnh liên quan đến {k1}. 
        - Mô tả rõ: Góc máy (Wide shot/Medium shot), cảm xúc khuôn mặt, màu sắc chủ đạo (Warm/Cool/Vibrant).

        Yêu cầu tách biệt 2 phần rõ ràng bằng nhãn [CONTENT] và [IMAGE_PROMPT].
        """

        if st.button("✨ TẠO NỘI DUNG VỚI GEMINI 2.5"):
            with st.spinner("Gemini 2.5 đang phân tích dữ liệu..."):
                try:
                    # Sử dụng model gemini-2.5-flash
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(master_prompt)
                    res_text = response.text
                    
                    # Logic tách nội dung
                    if "[IMAGE_PROMPT]" in res_text:
                        parts = res_text.split("[IMAGE_PROMPT]")
                        st.session_state.generated_content = parts[0].replace("[CONTENT]", "").strip()
                        st.session_state.generated_prompt = parts[1].strip()
                    else:
                        st.session_state.generated_content = res_text
                    st.success("Đã tạo nội dung Viral thành công!")
                except Exception as e:
                    st.error(f"Lỗi: {e}. Kiểm tra lại tên Model hoặc API Key.")

    with col2:
        st.subheader("🖋️ Kiểm duyệt & Chỉnh sửa")
        st.session_state.generated_content = st.text_area("Nội dung bài đăng:", st.session_state.generated_content, height=350)
        st.session_state.generated_prompt = st.text_area("Prompt cho AI vẽ ảnh:", st.session_state.generated_prompt, height=150)
        if st.button("✅ CHỐT NỘI DUNG"):
            st.toast("Dữ liệu đã sẵn sàng cho bước tiếp theo!")

with tab2:
    st.info("Module Bước 2: Tạo ảnh AI phối hợp Avatar cố định (Đang chờ cài đặt API vẽ ảnh).")

with tab3:
    st.info("Module Bước 3: Đăng bài tự động qua trình duyệt (Đang chờ cài đặt robot Playwright).")
