import streamlit as st
import json
import os

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Facebook Automation Hub", layout="wide")

# --- QUẢN LÝ DỮ LIỆU (Lưu tài khoản Facebook) ---
# Hàm này giúp lưu thông tin ID/Cookies vào một file nhỏ để dùng lại
def save_accounts(accounts):
    with open('accounts.json', 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=4)

def load_accounts():
    if os.path.exists('accounts.json'):
        with open('accounts.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Khởi tạo dữ liệu trong bộ nhớ tạm của Web
if 'accounts' not in st.session_state:
    st.session_state.accounts = load_accounts()
if 'selected_fb' not in st.session_state:
    st.session_state.selected_fb = None
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = ""
if 'generated_prompt' not in st.session_state:
    st.session_state.generated_prompt = ""

# --- SIDEBAR: QUẢN LÝ TÀI KHOẢN FACEBOOK ---
with st.sidebar:
    st.header("👤 Quản lý Facebook")
    
    # Khu vực thêm tài khoản mới
    with st.expander("Thêm Facebook mới"):
        new_name = st.text_input("Tên gợi nhớ (VD: FB Cá nhân 1)")
        new_id = st.text_input("Mã số ID (Nếu có)")
        new_cookies = st.text_area("Dán Cookies vào đây")
        if st.button("Lưu tài khoản"):
            if new_name and new_cookies:
                st.session_state.accounts[new_name] = {"id": new_id, "cookies": new_cookies}
                save_accounts(st.session_state.accounts)
                st.success(f"Đã lưu {new_name}")
            else:
                st.error("Vui lòng nhập Tên và Cookies")

    st.divider()
    
    # Khu vực chọn tài khoản để làm việc
    if st.session_state.accounts:
        fb_list = list(st.session_state.accounts.keys())
        st.session_state.selected_fb = st.selectbox("Chọn Facebook làm việc:", fb_list)
        
        # Hiển thị thông tin nhanh
        current_fb = st.session_state.accounts[st.session_state.selected_fb]
        st.info(f"Đang chọn: {st.session_state.selected_fb}\n\nID: {current_fb['id']}")
    else:
        st.warning("Chưa có tài khoản nào được lưu.")

# --- GIAO DIỆN CHÍNH (MAIN DASHBOARD) ---
st.title("🚀 Hệ thống Tự động hóa Nội dung Facebook")

# Chia Tab để làm việc theo Workflow
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Nội dung & Prompt", "🎨 Bước 2: Tạo ảnh AI Pro", "📤 Bước 3: Đăng bài tự động"])

# --- MODULE 1: NỘI DUNG & PROMPT ---
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Cài đặt từ khóa")
        key1 = st.text_input("Từ khóa 1 (Chủ đề chính)", placeholder="Ví dụ: Máy lọc nước")
        key2 = st.text_input("Từ khóa 2 (Đối tượng)", placeholder="Ví dụ: Nội trợ gia đình")
        key3 = st.text_input("Từ khóa 3 (Phong cách)", placeholder="Ví dụ: Chuyên nghiệp, tin cậy")
        
        if st.button("✨ TẠO NỘI DUNG (GEMINI)"):
            # Chỗ này sau này sẽ lắp API Gemini vào
            st.session_state.generated_content = f"Bài viết mẫu về {key1} dành cho {key2}..."
            st.session_state.generated_prompt = f"Realistic photo of a person using {key1} in a kitchen..."
            st.toast("Đang gọi Gemini xử lý...")

    with col2:
        st.subheader("Kiểm tra & Chỉnh sửa")
        content_edit = st.text_area("Nội dung bài đăng Facebook:", st.session_state.generated_content, height=150)
        prompt_edit = st.text_area("Prompt tạo ảnh (Tiếng Anh):", st.session_state.generated_prompt, height=100)
        
        if st.button("Xác nhận nội dung & Sang bước 2"):
            st.session_state.generated_content = content_edit
            st.session_state.generated_prompt = prompt_edit
            st.success("Đã chốt nội dung!")

# --- MODULE 2: TẠO ẢNH AI PRO ---
with tab2:
    st.subheader("Tạo hình ảnh phối hợp Avatar cố định")
    
    col_img_1, col_img_2 = st.columns([1, 1])
    
    with col_img_1:
        st.write("**Thông tin đầu vào:**")
        st.code(st.session_state.generated_prompt if st.session_state.generated_prompt else "Chưa có prompt từ Bước 1")
        st.write(f"**Link Avatar gốc:** (Đã cấu hình sẵn trong hệ thống)")
        
        if st.button("🎨 VẼ ẢNH NGAY (NANA PRO)"):
            # Chỗ này sau này sẽ lắp API Tạo ảnh vào
            st.warning("Chờ lắp API ở Giai đoạn 2...")

    with col_img_2:
        st.write("**Kết quả hình ảnh:**")
        # Hiển thị ảnh mẫu
        st.image("https://via.placeholder.com/500x500.png?text=Preview+Image+AI", use_container_width=True)
        if st.button("Sử dụng ảnh này & Chuyển sang Đăng bài"):
            st.success("Ảnh đã sẵn sàng!")

# --- MODULE 3: ĐĂNG BÀI TỰ ĐỘNG ---
with tab3:
    st.subheader("Thực thi đăng bài qua Chromium")
    
    if st.session_state.selected_fb:
        st.write(f"Tài khoản thực hiện: **{st.session_state.selected_fb}**")
        st.write(f"Nội dung: *{st.session_state.generated_content[:50]}...*")
        
        if st.button("🚀 BẮT ĐẦU ĐĂNG BÀI"):
            with st.status("Đang chạy robot tự động...") as status:
                st.write("Mở trình duyệt ảo...")
                st.write(f"Nạp Cookies cho {st.session_state.selected_fb}...")
                st.write("Đang tải ảnh và dán nội dung...")
                # Chỗ này sau này sẽ lắp Playwright vào
                status.update(label="Đã đăng thành công!", state="complete")
                st.balloons()
    else:
        st.error("Vui lòng chọn một tài khoản Facebook ở thanh bên trái trước!")

# --- HƯỚNG DẪN SỬ DỤNG ---
with st.expander("ℹ️ Hướng dẫn Workflow thủ công (10%)"):
    st.write("""
    1. **Bước 1:** Nhập từ khóa tại Tab 1, bấm nút tạo để lấy chữ. Bạn có thể sửa chữ trực tiếp.
    2. **Bước 2:** Sang Tab 2, bấm tạo ảnh. Hệ thống sẽ dùng Prompt từ bước 1.
    3. **Bước 3:** Kiểm tra lại tài khoản FB đang chọn ở bên trái, rồi bấm Đăng bài tại Tab 3.
    """)
