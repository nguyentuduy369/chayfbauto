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
    api_key = st.secrets["GEMINI_API_KEY"]
    hf_token = st.secrets["HF_TOKEN"]
    genai.configure(api_key=api_key)
except:
    st.error("❌ Thiếu API Key! Vui lòng kiểm tra GEMINI_API_KEY và HF_TOKEN trong Secrets.")
    st.stop()

# --- QUẢN LÝ TÀI KHOẢN (JSON) ---
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

# Khởi tạo Session State
if 'accounts' not in st.session_state: st.session_state.accounts = load_accounts()
if 'content' not in st.session_state: st.session_state.content = ""
if 'prompt' not in st.session_state: st.session_state.prompt = ""
if 'image_result' not in st.session_state: st.session_state.image_result = None

# --- SIDEBAR: QUẢN LÝ TÀI KHOẢN & AVATAR ---
with st.sidebar:
    st.header("👤 Hệ thống Tài khoản")
    
    # 1. Thêm mới tài khoản
    with st.expander("➕ Thêm/Sửa Facebook", expanded=not st.session_state.accounts):
        name = st.text_input("Tên Facebook (VD: Nick Chinh)")
        fb_id = st.text_input("ID Facebook")
        avatar_url = st.text_input("URL Avatar mẫu (Drive/Web)")
        cookie = st.text_area("Cookies")
        if st.button("Lưu vào hệ thống"):
            if name and cookie:
                st.session_state.accounts[name] = {
                    "id": fb_id,
                    "avatar": avatar_url,
                    "cookies": cookie
                }
                save_accounts(st.session_state.accounts)
                st.success(f"Đã lưu {name}!")
                st.rerun()
            else: st.error("Thiếu tên hoặc cookies!")

    st.divider()

    # 2. Chọn tài khoản làm việc
    if st.session_state.accounts:
        fb_list = list(st.session_state.accounts.keys())
        selected = st.selectbox("🎯 Chọn tài khoản đang chạy:", fb_list)
        st.session_state.selected_fb = selected
        
        # Hiển thị thông tin nhanh của tài khoản đang chọn
        acc = st.session_state.accounts[selected]
        st.info(f"ID: {acc['id']}")
        if acc['avatar']:
            st.image(acc['avatar'], caption="Avatar chuẩn nhận diện", width=100)
    else:
        st.warning("Chưa có dữ liệu tài khoản.")

# --- MÀN HÌNH CHÍNH ---
st.title("🚀 Smart Content Hub v2.6")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Tạo Content", "🎨 Bước 2: Tạo Ảnh AI", "📤 Bước 3: Đăng Bài"])

# --- TAB 1: CONTENT ---
with tab1:
    col_in, col_out = st.columns([1, 1.2])
    
    with col_in:
        st.subheader("🎯 Ý tưởng hôm nay")
        k1 = st.text_input("Chủ đề bài đăng", "Giải pháp AI cá nhân")
        k2 = st.text_input("Khách hàng mục tiêu", "Người kinh doanh online")
        trend = st.text_input("Trend/Bối cảnh", "Công nghệ 2026")
        
        if st.button("✨ TẠO NỘI DUNG VẠN NĂNG"):
            with st.spinner("Gemini 2.5 Flash đang xử lý..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    master_prompt = f"""
                    Bạn là chuyên gia Viral Marketing. Tạo nội dung cho {k1}, khách là {k2}, vibe {trend}.
                    Yêu cầu tách biệt 2 phần bằng nhãn chính xác:
                    [CONTENT]: Nội dung bài đăng (Tiếng Việt, ngắn gọn, icon, hashtag).
                    [IMAGE_PROMPT]: Đoạn mô tả ảnh (Tiếng Anh, Realistic, 8k, cinematic).
                    """
                    response = model.generate_content(master_prompt)
                    raw = response.text
                    
                    # Logic tách nội dung cải tiến (Tìm kiếm linh hoạt)
                    c_part = re.search(r"\[CONTENT\](.*?)(?=\[IMAGE_PROMPT\]|$)", raw, re.S | re.I)
                    p_part = re.search(r"\[IMAGE_PROMPT\](.*)", raw, re.S | re.I)
                    
                    st.session_state.content = c_part.group(1).strip(": \n") if c_part else raw
                    st.session_state.prompt = p_part.group(1).strip(": \n") if p_part else ""
                    st.success("Tách dữ liệu thành công!")
                except Exception as e:
                    st.error(f"Lỗi API: {e}")

    with col_out:
        st.subheader("🖋️ Kiểm tra & Copy")
        # Ô nội dung bài viết
        st.session_state.content = st.text_area("Nội dung bài đăng:", st.session_state.content, height=250)
        st.write("*(Di chuột vào khung dưới, bấm nút Copy ở góc phải)*")
        st.code(st.session_state.content, language="text")
        
        st.divider()
        
        # Ô Prompt ảnh
        st.write("**Prompt tạo ảnh (Sẽ tự động chuyển sang Bước 2):**")
        st.session_state.prompt = st.text_area("Chỉnh sửa Prompt nếu cần:", st.session_state.prompt, height=100)
        st.code(st.session_state.prompt, language="text")

# --- TAB 2: TẠO ẢNH ---
with tab2:
    st.subheader("🎨 Studio Tạo Ảnh AI")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        # Tự động lấy Avatar từ Sidebar
        if 'selected_fb' in st.session_state and st.session_state.accounts[st.session_state.selected_fb]['avatar']:
            current_avatar = st.session_state.accounts[st.session_state.selected_fb]['avatar']
            st.success(f"✅ Đang sử dụng Avatar của: {st.session_state.selected_fb}")
            st.image(current_avatar, width=150)
        else:
            st.warning("⚠️ Tài khoản này chưa có URL Avatar trong Sidebar.")
        
        st.divider()
        # Lấy prompt từ bước 1 sang
        final_prompt = st.text_area("Xác nhận Prompt vẽ ảnh:", st.session_state.prompt, height=150)
        
        if st.button("🎨 VẼ ẢNH VỚI FLUX.1"):
            with st.spinner("Hugging Face đang vẽ..."):
                try:
                    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
                    headers = {"Authorization": f"Bearer {hf_token}"}
                    response = requests.post(API_URL, headers=headers, json={"inputs": final_prompt})
                    if response.status_code == 200:
                        st.session_state.image_result = response.content
                        st.success("Vẽ xong!")
                    else: st.error("Server AI đang bận, thử lại sau vài giây.")
                except Exception as e: st.error(f"Lỗi: {e}")

    with c2:
        if st.session_state.image_result:
            st.image(st.session_state.image_result, caption="Ảnh AI đã tạo", use_container_width=True)
            st.download_button("📥 Tải ảnh về", st.session_state.image_result, "post.png", "image/png")

# --- TAB 3: ĐĂNG BÀI ---
with tab3:
    st.info("Chuẩn bị tích hợp Robot đăng bài tự động...")
