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

# --- HÀM TẢI VÀ HIỂN THỊ ẢNH AN TOÀN (VƯỢT LỖI CORS/REDIRECT) ---
def safe_display_image(url, width=None):
    if not url: return
    # Xử lý tự động link Google Drive
    if "drive.google.com" in url:
        file_id = ""
        if "/file/d/" in url: file_id = url.split("/file/d/")[1].split("/")[0]
        elif "id=" in url: file_id = url.split("id=")[1].split("&")[0]
        if file_id: url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
    try:
        # Tải ảnh về máy chủ bằng Requests với User-Agent chuẩn
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        if res.status_code == 200:
            st.image(res.content, width=width)
        else:
            st.warning(f"Bị chặn hiển thị (Mã {res.status_code})")
    except Exception:
        st.warning("Lỗi tải ảnh.")

import base64

# --- LẤY API KEYS & CẤU HÌNH ---
try:
    GEMINI_KEYS = st.secrets["GEMINI_KEYS"].split(",")
    HF_TOKEN = st.secrets["HF_TOKEN"]
except:
    st.error("❌ Thiếu GEMINI_KEYS hoặc HF_TOKEN trong thiết lập Secrets!")
    st.stop()

import io
from PIL import Image

# --- HÀM XOAY VÒNG API KEY GEMINI (NÂNG CẤP THỊ GIÁC) ---
def generate_with_key_rotation(prompt_data):
    for i, key in enumerate(GEMINI_KEYS):
        try:
            genai.configure(api_key=key.strip())
            model = genai.GenerativeModel('gemini-2.5-flash')
            # Khả năng nạp cả mảng dữ liệu (chữ + ảnh) vào Gemini
            return model.generate_content(prompt_data).text
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                if i < len(GEMINI_KEYS) - 1: continue
                else: raise Exception("Tất cả API Keys đều đã hết hạn mức. Vui lòng thêm Key mới!")
            else: raise e

# --- QUẢN LÝ DỮ LIỆU & MÃ HÓA ẢNH ---
def save_accounts(accounts):
    with open('accounts.json', 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=4)

def load_accounts():
    if os.path.exists('accounts.json'):
        try:
            with open('accounts.json', 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        return f"data:image/png;base64,{base64.b64encode(uploaded_file.getvalue()).decode()}"
    return ""

if 'accounts' not in st.session_state: st.session_state.accounts = load_accounts()

# --- SIDEBAR: TRẠM TUÂN THỦ THÔNG MINH ---
with st.sidebar:
    st.header("👤 Smart Compliance Hub")
    
    with st.expander("🛠️ Quản lý Tài khoản FB", expanded=True):
        input_cookie = st.text_area("Dán Cookies FB:", height=70)
        if st.button("🔍 Lấy UID từ Cookie"):
            uid_match = re.search(r'c_user=(\d+)', input_cookie)
            if uid_match:
                st.session_state.tmp_uid = uid_match.group(1)
                st.success(f"Đã lấy UID: {st.session_state.tmp_uid}")
            else: st.error("Cookie không hợp lệ hoặc không có UID.")

        # Nhập liệu thủ công 100% để tránh lỗi
        f_name = st.text_input("Tên FB:", placeholder="Nhập Tên Thủ Công", value=st.session_state.get('tmp_name', ""))
        f_uid = st.text_input("UID:", value=st.session_state.get('tmp_uid', ""))
        
        st.write("**Ảnh Avatar (Nhận diện nick):**")
        avt_file = st.file_uploader("Tải lên Avatar", type=['jpg', 'png'], key="avt")
        if avt_file: st.image(avt_file, width=80)

        st.divider()
        st.write("**Nhân vật mẫu (Cho AI):**")
        char_file = st.file_uploader("Tải lên Ảnh mẫu", type=['jpg', 'png'], key="char")
        if char_file: st.image(char_file, width=150)

        if st.button("💾 LƯU TÀI KHOẢN"):
            if f_name and input_cookie:
                # Mã hóa ảnh thành chuỗi để lưu thẳng vào JSON
                b64_avt = image_to_base64(avt_file) if avt_file else ""
                b64_char = image_to_base64(char_file) if char_file else ""
                
                st.session_state.accounts[f_name] = {
                    "uid": f_uid, "avatar_b64": b64_avt, 
                    "character_b64": b64_char, "cookies": input_cookie
                }
                save_accounts(st.session_state.accounts)
                st.success("Đã lưu an toàn vào hệ thống!")
                st.rerun()

    st.divider()
    if st.session_state.accounts:
        st.session_state.selected_fb = st.selectbox("🎯 Chọn Nick làm việc:", list(st.session_state.accounts.keys()))
        acc = st.session_state.accounts[st.session_state.selected_fb]
        if acc.get('avatar_b64'): 
            st.image(acc['avatar_b64'], width=60)
    else: st.session_state.selected_fb = None

# --- MAIN ---
st.title("🚀 Smart Automation Hub - Nền Tảng")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Content", "🎨 Bước 2: Ảnh AI (Imagen 3)", "📤 Bước 3: Đăng Bài"])

with tab1:
    st.subheader("🎯 Bảng Điều Khiển Nội Dung (Đa Ngành Nghề)")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        role = st.selectbox("Vai trò của bạn:", ["KOL / KOC Review", "Sale / Bán hàng", "Chuyên gia / Đào tạo", "Idol Livestream", "Chủ Doanh Nghiệp"])
    with col_f2:
        target_age = st.selectbox("Độ tuổi Khách hàng:", ["Gen Z (18-24 tuổi)", "Millennials (25-34 tuổi)", "Trung niên (35-50 tuổi)", "Mọi lứa tuổi"])
    with col_f3:
        target_region = st.selectbox("Khu vực / Văn hóa:", ["Toàn quốc (Phổ thông)", "Miền Nam (Sôi nổi, trend)", "Miền Bắc (Chỉn chu, sâu sắc)"])

    c1, c2 = st.columns([1, 1.2])
    with c1:
        if st.button("🔍 Phân tích Top Trend Hôm nay", use_container_width=True):
            with st.spinner(f"Đang phân tích thị trường cho {role}..."):
                try:
                    # PROMPT MỚI: Ép AI "tẩy não" mảng pháp lý nếu không phải Chủ Doanh Nghiệp
                    q_trend = f"""Bạn là Chuyên gia phân tích dữ liệu mạng xã hội (TikTok/Facebook Trend) xuất sắc nhất.
                    LỆNH TỐI QUAN TRỌNG: Xóa bỏ hoàn toàn bộ nhớ về "Trạm Tuân Thủ", "Pháp lý", "B2B", "Doanh nghiệp" nếu Vai trò dưới đây không phải là Chủ Doanh Nghiệp.
                    Hãy phân tích xu hướng MỚI NHẤT hôm nay cho vai trò '{role}', nhắm đến '{target_age}', tại văn hóa '{target_region}'.
                    - Nếu là Idol/KOL/Sale: Bắt buộc chọn các chủ đề B2C hot như: Mỹ phẩm, Thời trang, Ẩm thực, Đồ công nghệ, Đồ gia dụng tiện ích.
                    - Trend phải là các từ lóng (slang), câu nói viral, drama giới trẻ, hoặc phong cách sống đang thịnh hành.
                    Bắt buộc trả về đúng 3 dòng định dạng sau:
                    Sản phẩm: [Tên 1 sản phẩm/chủ đề cụ thể, VD: Son tint bóng, Áo babytee, Nồi chiên không dầu...]
                    Đối tượng: [Chi tiết tệp {target_age} tại {target_region}]
                    Trend: [1 Câu nói viral, trend TikTok, hoặc nỗi đau mua sắm đang hot]"""
                    
                    res_trend = generate_with_key_rotation([q_trend])
                    
                    import re
                    sp_match = re.search(r'Sản phẩm:\s*(.*)', res_trend)
                    dt_match = re.search(r'Đối tượng:\s*(.*)', res_trend)
                    tr_match = re.search(r'Trend:\s*(.*)', res_trend)
                    
                    if sp_match and dt_match and tr_match:
                        st.session_state.k1 = sp_match.group(1).strip()
                        st.session_state.k2 = dt_match.group(1).strip()
                        st.session_state.trend = tr_match.group(1).strip()
                        st.success("Đã rà quét và nạp Trend thành công!")
                    else:
                        st.warning("Dữ liệu trả về chưa chuẩn, vui lòng bấm lại.")
                except Exception as e: st.error(f"Lỗi lấy trend: {e}")

        st.divider()
        sp = st.text_input("Chủ đề / Sản phẩm", st.session_state.get('k1', "Review phong cách sống"))
        kh = st.text_input("Đối tượng", st.session_state.get('k2', "Giới trẻ Gen Z"))
        tr = st.text_input("Bối cảnh / Trend", st.session_state.get('trend', "Cuộc sống tự do"))
        
        if st.button("✨ TẠO NỘI DUNG VIRAL", use_container_width=True):
            with st.spinner("Đang soi kỹ ảnh mẫu và viết bài..."):
                try:
                    q_text = f"Write a viral Facebook personal post for '{sp}' targeting '{kh}' with a '{tr}' vibe, from the perspective of a '{role}'. Under 150 words. Format: [CONTENT] Vietnamese post here ||| [PROMPT] English image prompt here."
                    prompt_data = [q_text]
                    
                    if st.session_state.get('selected_fb'):
                        acc = st.session_state.accounts[st.session_state.selected_fb]
                        if acc.get('character_b64'):
                            try:
                                img_data = base64.b64decode(acc['character_b64'].split(',')[1])
                                char_img = Image.open(io.BytesIO(img_data))
                                prompt_data.append(char_img)
                                prompt_data[0] += f"\nIMPORTANT VISUAL RULE: I attached a reference image. The [PROMPT] MUST be a single cohesive English paragraph that includes: 1) EXACT facial extraction (ethnicity, face shape like oval, specific features like moles, eye shape, skin tone, exact hairstyle) from the image. 2) Place this EXACT character in a highly realistic setting interacting with '{sp}' or reflecting '{tr}'. 3) Append these mandatory photography keywords: 'shot on 35mm lens, candid street photography, highly detailed skin texture, pores visible, natural cinematic lighting, photorealistic, 8k, ultra-realistic'. DO NOT make it look plastic or 3D."
                            except: pass
                    
                    res = generate_with_key_rotation(prompt_data)
                    
                    if "|||" in res:
                        st.session_state.content, st.session_state.prompt = res.split("|||")[0].replace("[CONTENT]", "").strip(), res.split("|||")[1].replace("[PROMPT]", "").strip()
                    else:
                        st.session_state.content, st.session_state.prompt = res, f"A photorealistic candid shot about {sp}, 35mm photography"
                except Exception as e: st.error(f"Lỗi: {e}")

    with c2:
        st.session_state.content = st.text_area("Bài viết (Chuẩn cá nhân):", st.session_state.get('content',''), height=220)
        copy_button(st.session_state.content, "📋 Copy Content")
        st.session_state.prompt = st.text_area("Prompt Đạo diễn Hình ảnh (EN):", st.session_state.get('prompt',''), height=150)
        copy_button(st.session_state.prompt, "🖼️ Copy Prompt")

with tab2:
    st.subheader("🎨 Studio Ảnh (FLUX.1 Schnell)")
    cl, cr = st.columns([1, 1])
    with cl:
        p_final = st.text_area("Xác nhận Lệnh vẽ:", st.session_state.get('prompt',''), height=150)
        
        if st.button("🎨 VẼ ẢNH NGAY"):
            with st.spinner("Đang kết nối FLUX.1..."):
                try:
                    hf_headers = {"Authorization": f"Bearer {HF_TOKEN}"}
                    model_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
                    res = requests.post(model_url, headers=hf_headers, json={"inputs": p_final}, timeout=40)
                    if res.status_code == 200:
                        st.session_state.img_res = res.content
                        st.success("Tạo ảnh thành công!")
                    else: 
                        st.error(f"HF lỗi {res.status_code}")
                except Exception as e: st.error(f"Lỗi: {e}")
                
    with cr:
        if 'img_res' in st.session_state:
            st.image(st.session_state.img_res, use_container_width=True)

with tab3:
    st.header("📤 Trạm Đăng Bài (Meta Graph API - Tuân Thủ 100%)")
    st.info("💡 Ngã rẽ 1: Đăng tự động lên Fanpage bằng API chính thức. Không cần giả lập trình duyệt, không rủi ro Checkpoint.")
    
    # Cấu hình API Fanpage
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        page_id = st.text_input("Nhập Page ID (Của Fanpage):", placeholder="VD: 123456789012345")
    with col_cfg2:
        page_token = st.text_input("Nhập Page Access Token:", type="password", placeholder="EAAI...")

    col_l, col_r = st.columns([1, 1.5])
    with col_l:
        if st.button("🚀 BẮN DỮ LIỆU LÊN FANPAGE"):
            if not st.session_state.get('content') or not st.session_state.get('img_res'):
                st.error("❌ Vui lòng tạo Bài viết và Hình ảnh trước!")
            elif not page_id or not page_token:
                st.error("❌ Vui lòng nhập Page ID và Token của Fanpage!")
            else:
                with st.spinner("Đang truyền dữ liệu qua máy chủ Meta..."):
                    try:
                        url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
                        payload = {'message': st.session_state.content, 'access_token': page_token}
                        files = {'source': ('image.png', st.session_state.img_res, 'image/png')}
                        
                        res = requests.post(url, data=payload, files=files)
                        data = res.json()
                        
                        if 'id' in data:
                            st.success(f"✅ BÙM! Đã đăng thành công lên Fanpage. Post ID: {data['id']}")
                            st.balloons()
                        else:
                            err_msg = data.get('error', {}).get('message', 'Lỗi không xác định')
                            st.error(f"❌ Meta từ chối: {err_msg}")
                    except Exception as e:
                        st.error(f"Lỗi hệ thống: {e}")
                        
    with col_r:
        st.markdown("**Bản xem trước Nội dung:**")
        st.info(st.session_state.get('content', 'Chưa có bài viết...'))
        if st.session_state.get('img_res'):
            st.image(st.session_state.img_res, width=250)
