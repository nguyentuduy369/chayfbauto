import streamlit as st
import json
import os
import google.generativeai as genai
import requests
import re
import io
import base64
from PIL import Image
import streamlit.components.v1 as components

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Compliance Hub - Auto", layout="wide")

# --- NÚT COPY JAVASCRIPT ---
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

# --- HÀM XỬ LÝ LINK ẢNH (Google Drive & Trực tiếp) ---
def get_direct_img_url(url):
    if not url: return ""
    if "drive.google.com" in url:
        file_id = ""
        if "/file/d/" in url: file_id = url.split("/file/d/")[1].split("/")[0]
        elif "id=" in url: file_id = url.split("id=")[1].split("&")[0]
        if file_id: return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

# --- LẤY API KEYS ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except:
    st.error("❌ Thiếu GEMINI_API_KEY trong Secrets!")
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

# --- HÀM QUÉT INFO FB ---
def fetch_fb_profile(cookie_str):
    try:
        uid_match = re.search(r'c_user=(\d+)', cookie_str)
        uid = uid_match.group(1) if uid_match else ""
        if not uid: return "Lỗi Cookie (Không thấy UID)", "", ""

        avatar = f"https://graph.facebook.com/{uid}/picture?type=large"
        
        headers = {'cookie': cookie_str, 'user-agent': 'Mozilla/5.0'}
        res = requests.get(f"https://mbasic.facebook.com/{uid}", headers=headers, timeout=10)
        name_match = re.search(r'<title>(.*?)</title>', res.text)
        name = name_match.group(1) if name_match else f"User {uid}"
        if "Facebook" in name: name = name.replace("Facebook", "").strip(" | -")

        return name, uid, avatar
    except Exception as e:
        return f"Lỗi quét: {e}", uid if 'uid' in locals() else "", ""

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Smart Compliance Hub")
    
    with st.expander("🛠️ Quản lý Tài khoản", expanded=True):
        input_cookie = st.text_area("Dán Cookies FB:", height=70)
        if st.button("🔍 Check & Auto-fill Profile"):
            n, u, a = fetch_fb_profile(input_cookie)
            st.session_state.tmp_name, st.session_state.tmp_uid, st.session_state.tmp_avatar = n, u, a
            st.success(f"Nhận diện: {n}")

        f_name = st.text_input("Tên FB:", st.session_state.get('tmp_name', ""))
        f_uid = st.text_input("UID:", st.session_state.get('tmp_uid', ""))
        f_avatar = st.text_input("Link Avatar:", st.session_state.get('tmp_avatar', ""))
        
        if f_avatar: st.image(get_direct_img_url(f_avatar), width=80)

        st.divider()
        st.write("**Nhân vật mẫu (Cho AI):**")
        char_url = st.text_input("Link Ảnh mẫu (Drive/Web):")
        char_file = st.file_uploader("Hoặc tải lên:", type=['jpg', 'png'])
        
        if char_file: 
            st.image(char_file, width=150)
        elif char_url:
            st.image(get_direct_img_url(char_url), width=150)

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
        st.session_state.selected_fb = st.selectbox("🎯 Chọn Nick làm việc:", list(st.session_state.accounts.keys()))
        acc = st.session_state.accounts[st.session_state.selected_fb]
        if acc['avatar']: st.image(get_direct_img_url(acc['avatar']), width=60)
    else: st.session_state.selected_fb = None

# --- MAIN ---
st.title("🚀 Smart Automation Hub - Nền Tảng")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Content", "🎨 Bước 2: Ảnh AI (Imagen 3)", "📤 Bước 3: Đăng Bài"])

with tab1:
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.subheader("🎯 Thiết lập")
        sp = st.text_input("Sản phẩm", "Dịch vụ Tuân thủ")
        kh = st.text_input("Đối tượng", "Chủ doanh nghiệp")
        tr = st.text_input("Trend", "Tự động hóa")
        if st.button("✨ TẠO NỘI DUNG"):
            with st.spinner("Gemini đang viết..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    q = f"Write FB post for {sp} to {kh}, vibe {tr}. Format strictly: [CONTENT] Vietnamese post here ||| [PROMPT] English image prompt here."
                    res = model.generate_content(q).text
                    if "|||" in res:
                        st.session_state.content = res.split("|||")[0].replace("[CONTENT]", "").strip()
                        st.session_state.prompt = res.split("|||")[1].replace("[PROMPT]", "").strip()
                    else:
                        st.session_state.content = res
                        st.session_state.prompt = f"A professional realistic photo about {sp}"
                except Exception as e:
                    st.error(f"Lỗi tạo nội dung: {e}")

    with c2:
        st.session_state.content = st.text_area("Bài viết:", st.session_state.get('content',''), height=220)
        copy_button(st.session_state.content, "📋 Copy Content")
        st.divider()
        st.session_state.prompt = st.text_area("Prompt vẽ ảnh (EN):", st.session_state.get('prompt',''), height=100)
        copy_button(st.session_state.prompt, "🖼️ Copy Prompt")

with tab2:
    st.subheader("🎨 Studio Ảnh (Pollinations - Miễn phí)")
    cl, cr = st.columns([1, 1])
    with cl:
        p_final = st.text_area("Xác nhận Lệnh vẽ (Tiếng Anh):", st.session_state.get('prompt',''), height=150)
        if st.button("🎨 VẼ ẢNH VỚI POLLINATIONS"):
            with st.spinner("Trạm Tuân Thủ Thông Minh đang kết nối máy chủ Pollinations..."):
                try:
                    import random
                    # Tạo seed ngẫu nhiên để tránh máy chủ trả về ảnh cũ (cache)
                    seed = random.randint(1, 1000000)
                    
                    # Thêm enhance=true để tối ưu chi tiết ảnh, nologo=true để xóa watermark
                    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(p_final)}?width=1024&height=1024&nologo=true&seed={seed}&enhance=true"
                    
                    res = requests.get(url, timeout=30)
                    
                    # Kiểm tra nghiêm ngặt: Chỉ nhận nếu dữ liệu trả về thực sự là ảnh
                    if res.status_code == 200 and 'image' in res.headers.get('content-type', ''):
                        st.session_state.img_res = res.content
                        st.success("Tuyệt vời! Ảnh đã được tạo thành công.")
                    else:
                        st.error("Máy chủ Pollinations đang quá tải hoặc trả về dữ liệu lỗi. Vui lòng bấm thử lại.")
                        
                except Exception as e: 
                    st.error(f"Lỗi kết nối hệ thống: {e}")
                
    with cr:
        if 'img_res' in st.session_state:
            try:
                st.image(st.session_state.img_res, use_container_width=True)
                st.download_button("📥 Tải ảnh về", st.session_state.img_res, "pollinations_post.png", "image/png")
            except Exception as e:
                st.warning("Lỗi hiển thị dữ liệu ảnh. Vui lòng bấm vẽ lại.")
with tab3:
    st.header("📤 Trạm Đăng Bài")
    if st.session_state.get('selected_fb'):
        st.success(f"Đã nạp Nick: **{st.session_state.selected_fb}**")
        if st.button("🚀 KÍCH HOẠT ROBOT"):
            st.info("Module Playwright đang chờ cập nhật...")
    else: st.error("Hãy chọn nick ở Sidebar.")
