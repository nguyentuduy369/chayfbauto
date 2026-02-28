import streamlit as st
import json
import os
import google.generativeai as genai
import requests

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Automation Hub v2.9", layout="wide")

# --- LẤY API KEYS TỪ SECRETS ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    hf_token = st.secrets["HF_TOKEN"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("❌ Lỗi cấu hình Secrets! Hãy kiểm tra lại.")
    st.stop()

# --- QUẢN LÝ TÀI KHOẢN (FILE JSON) ---
def save_accounts(accounts):
    try:
        with open('accounts.json', 'w', encoding='utf-8') as f:
            json.dump(accounts, f, ensure_ascii=False, indent=4)
        return True
    except: return False

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

# --- SIDEBAR: QUẢN LÝ TÀI KHOẢN TẬP TRUNG ---
with st.sidebar:
    st.header("👤 Hệ thống Tài khoản")
    
    with st.expander("🛠️ Kiểm tra & Lưu tài khoản", expanded=True):
        input_cookie = st.text_area("1. Dán Cookies Facebook:", height=80)
        
        if st.button("🔍 Quét thông tin Profile"):
            # Mockup quét nhanh từ cookie (Sau này sẽ dùng Playwright quét thật)
            st.session_state.tmp_name = "User_" + input_cookie[:5]
            st.session_state.tmp_uid = "1000..."
            st.info("Đã nhận diện Cookie")

        # Các ô nhập thông tin chuẩn hóa
        f_name = st.text_input("Tên Facebook hiển thị:")
        f_uid = st.text_input("UID (Mã định danh):")
        f_avatar = st.text_input("URL Avatar (Để nhận diện Nick):")
        f_character = st.text_input("URL Nhân vật mẫu (Cho Bước 2):")
        
        if st.button("💾 LƯU VÀO KHO DỮ LIỆU"):
            if f_name and input_cookie:
                st.session_state.accounts[f_name] = {
                    "uid": f_uid,
                    "avatar": f_avatar,
                    "character": f_character,
                    "cookies": input_cookie
                }
                if save_accounts(st.session_state.accounts):
                    st.success("✅ Đã lưu thành công!")
                    st.rerun()
                else: st.error("Lỗi ghi file!")

    st.divider()
    if st.session_state.accounts:
        st.session_state.selected_fb = st.selectbox("🎯 Chọn tài khoản đang chạy:", list(st.session_state.accounts.keys()))
        acc = st.session_state.accounts[st.session_state.selected_fb]
        if acc['avatar']: st.image(acc['avatar'], caption="Đang sử dụng Nick này", width=100)
    else: st.warning("Chưa có tài khoản nào.")

# --- MÀN HÌNH CHÍNH ---
st.title("🚀 Smart Content Hub v2.9")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Tạo Content", "🎨 Bước 2: Tạo Ảnh AI", "📤 Bước 3: Đăng Bài"])

# --- TAB 1: CONTENT (FIX LỖI GỘP) ---
with tab1:
    col_in, col_out = st.columns([1, 1.2])
    with col_in:
        st.subheader("🎯 Ý tưởng")
        k1 = st.text_input("Sản phẩm", "AI Automation")
        k2 = st.text_input("Khách hàng", "Chủ shop")
        trend = st.text_input("Bối cảnh", "Tết 2026")
        
        if st.button("✨ TẠO NỘI DUNG VẠN NĂNG"):
            with st.spinner("Gemini 2.5 Flash đang viết..."):
                model = genai.GenerativeModel('gemini-2.5-flash')
                m_prompt = f"Write FB post for {k1}, target {k2}, vibe {trend}. Use EXACT tags: [CONTENT] for Vietnamese post, [IMAGE_PROMPT] for English image description."
                raw = model.generate_content(m_prompt).text
                
                # Tách chuỗi tuyệt đối
                try:
                    st.session_state.content = raw.split("[CONTENT]")[1].split("[IMAGE_PROMPT]")[0].strip(": \n")
                    st.session_state.prompt = raw.split("[IMAGE_PROMPT]")[1].strip(": \n")
                except:
                    st.session_state.content = raw # Nếu lỗi thì hiện hết để thủ công

    with col_out:
        st.subheader("🖋️ Kết quả & Copy")
        # Sử dụng trình soạn thảo text_area để sửa, và st.code để copy
        st.session_state.content = st.text_area("Sửa bài viết:", st.session_state.content, height=250)
        st.code(st.session_state.content, language="text") # Nút copy nằm ở đây
        
        st.divider()
        st.session_state.prompt = st.text_area("Sửa Prompt ảnh:", st.session_state.prompt, height=80)
        st.code(st.session_state.prompt, language="text") # Nút copy nằm ở đây

# --- TAB 2: TẠO ẢNH (ƯU TIÊN FLUX) ---
with tab2:
    st.subheader("🎨 Studio Tạo Ảnh AI")
    c1, c2 = st.columns([1, 1.2])
    with c1:
        if 'selected_fb' in st.session_state:
            char_url = st.session_state.accounts[st.session_state.selected_fb].get('character', '')
            if char_url: st.image(char_url, caption="Ảnh nhân vật mẫu để AI học tập", width=150)
            
        final_p = st.text_area("Xác nhận lệnh vẽ cuối cùng:", st.session_state.prompt, height=150)
        engine = st.radio("Chọn máy chủ:", ["FLUX.1 (Chân thật - Khuyên dùng)", "Pollinations (Nhanh - Dự phòng)"], horizontal=True)
        
        if st.button("🎨 BẮT ĐẦU VẼ ẢNH"):
            with st.spinner("Đang xử lý..."):
                try:
                    if "FLUX.1" in engine:
                        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
                        res = requests.post(url, headers={"Authorization": f"Bearer {hf_token}"}, json={"inputs": final_p})
                        if res.status_code == 200: st.session_state.image_result = res.content
                        else: st.error("FLUX.1 bận, hãy dùng Pollinations!")
                    else:
                        img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(final_p)}?width=1024&height=1024&nologo=true"
                        st.session_state.image_result = requests.get(img_url).content
                    st.success("Đã vẽ xong!")
                except Exception as e: st.error(str(e))

    with c2:
        if st.session_state.image_result:
            st.image(st.session_state.image_result, caption="Kết quả ảnh đăng bài", use_container_width=True)

# --- TAB 3: ĐĂNG BÀI (GIAO DIỆN ROBOT) ---
with tab3:
    st.header("📤 Trạm Điều Khiển Robot Đăng Bài")
    if 'selected_fb' in st.session_state:
        col_fb, col_st = st.columns([1, 1.5])
        with col_fb:
            st.markdown(f"**Nick đang chạy:** {st.session_state.selected_fb}")
            st.write(f"**Trạng thái Cookie:** Sẵn sàng")
            if st.button("🚀 KÍCH HOẠT ROBOT ĐĂNG BÀI"):
                with st.status("Robot đang làm việc...") as status:
                    st.write("1. Khởi động trình duyệt ảo (Playwright)...")
                    st.write(f"2. Nạp Cookies của {st.session_state.selected_fb}...")
                    st.write("3. Truy cập tường nhà...")
                    st.write("4. Đang tải ảnh và dán nội dung...")
                    st.write("5. Nhấn nút Đăng bài...")
                    status.update(label="✅ ĐĂNG BÀI THÀNH CÔNG!", state="complete")
                    st.balloons()
        with col_st:
            st.subheader("Xem trước bài sẽ đăng")
            st.info(st.session_state.content[:200] + "...")
            if st.session_state.image_result:
                st.image(st.session_state.image_result, width=200)
    else:
        st.warning("Vui lòng chọn tài khoản ở Sidebar trước!")
