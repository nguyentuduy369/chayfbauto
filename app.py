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
import json
import os

def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        return f"data:image/png;base64,{base64.b64encode(uploaded_file.getvalue()).decode()}"
    return ""

if 'accounts' not in st.session_state: st.session_state.accounts = load_json('accounts.json')
if 'fanpages' not in st.session_state: st.session_state.fanpages = load_json('fanpages.json')

import urllib.parse
import requests

# --- SIDEBAR: GIAO DIỆN VIRALSYNC PRO ---
with st.sidebar:
    # --- TÊN ỨNG DỤNG & LOGO ---
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #6C63FF; margin-bottom: 0;">🚀 ViralSync Pro</h1>
            <p style="color: #888; font-size: 14px; margin-top: 5px;">All-in-One Content & SEO Assistant</p>
        </div>
    """, unsafe_allow_html=True)
    
    # --- 1. BỘ ĐẾM TRUY CẬP ---
    stats_file = 'stats.json'
    if not os.path.exists(stats_file): save_json({"visitors": 300}, stats_file)
    stats = load_json(stats_file)
    
    if stats.get("visitors", 0) < 300: stats["visitors"] = 300
    if 'visited' not in st.session_state:
        stats['visitors'] += 1
        save_json(stats, stats_file)
        st.session_state.visited = True
        
    st.markdown(f"**👁️ Lượt truy cập:** `{stats['visitors']:,}`")
    st.divider()

    # --- 2. Ý TƯỞNG MINH HỌA (Có hiệu ứng thu hút) ---
    st.subheader("📸 Ý Tưởng Minh Họa")
    
    # CSS Hiệu ứng nhấp nháy thu hút sự chú ý
    st.markdown("""
        <div style="animation: pulse 1.5s infinite; color: #ff4b4b; font-size: 13px; font-weight: bold; margin-bottom: 8px;">
            👇 Bấm vào khung dưới đây để nạp ảnh cho AI
        </div>
        <style>
        @keyframes pulse {
            0% { opacity: 1; transform: translateY(0); }
            50% { opacity: 0.5; transform: translateY(3px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.expander("🧠 NẠP TRI THỨC & ẢNH MẪU (Click Mở)", expanded=False):
        st.session_state.char1_b64 = image_to_base64(st.file_uploader("Nhân vật 1 (Chính):", type=['jpg', 'png'], key="c1"))
        st.session_state.char2_b64 = image_to_base64(st.file_uploader("Nhân vật 2 (Phụ):", type=['jpg', 'png'], key="c2"))
        st.session_state.pet_b64 = image_to_base64(st.file_uploader("Thú cưng:", type=['jpg', 'png'], key="pet"))
        st.session_state.bg_b64 = image_to_base64(st.file_uploader("Bối cảnh mẫu:", type=['jpg', 'png'], key="bg"))

    st.divider()
    
    # --- 3. LIÊN KẾT ĐA NỀN TẢNG (Đã fix lỗi Icon Shopee) ---
    st.subheader("🌐 Liên Kết Đa Nền Tảng")
    
    marquee_html = """
    <style>
    .marquee-container {
        width: 100%; overflow: hidden; white-space: nowrap; box-sizing: border-box; 
        background: #f0f2f6; padding: 10px 0; border-radius: 10px; margin-bottom: 15px;
    }
    .marquee-content {
        display: inline-block; animation: marquee 12s linear infinite;
    }
    .marquee-content:hover { animation-play-state: paused; }
    .marquee-content img { width: 32px; margin: 0 8px; border-radius: 8px; transition: transform 0.2s; cursor: pointer; }
    .marquee-content img:hover { transform: scale(1.2); }
    @keyframes marquee { 0% { transform: translate(0, 0); } 100% { transform: translate(-50%, 0); } }
    </style>
    <div class="marquee-container">
        <div class="marquee-content">
            <a href="https://facebook.com" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/124/124010.png" title="Facebook"></a>
            <a href="https://tiktok.com" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/3046/3046121.png" title="TikTok"></a>
            <a href="https://youtube.com" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/1384/1384060.png" title="YouTube"></a>
            <a href="https://instagram.com" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/2111/2111463.png" title="Instagram"></a>
            <a href="https://shopee.vn" target="_blank"><img src="https://img.icons8.com/color/48/shopee.png" title="Shopee"></a>
            <a href="https://threads.net" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/11820/11820089.png" title="Threads"></a>
            <a href="https://facebook.com" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/124/124010.png" title="Facebook"></a>
            <a href="https://tiktok.com" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/3046/3046121.png" title="TikTok"></a>
            <a href="https://youtube.com" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/1384/1384060.png" title="YouTube"></a>
            <a href="https://instagram.com" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/2111/2111463.png" title="Instagram"></a>
            <a href="https://shopee.vn" target="_blank"><img src="https://img.icons8.com/color/48/shopee.png" title="Shopee"></a>
            <a href="https://threads.net" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/11820/11820089.png" title="Threads"></a>
        </div>
    </div>
    """
    st.markdown(marquee_html, unsafe_allow_html=True)
    st.divider()

    # --- 4. HỖ TRỢ KỸ THUẬT 24/24 (Đã thêm Hotline) ---
    st.subheader("🛠️ Hỗ Trợ Kỹ Thuật 24/24")
    
    # Nút Hotline
    st.markdown('<div style="background:#2ecc71; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold; font-size:16px; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">📞 Hotline: 1900 8xxx</div>', unsafe_allow_html=True)
    
    btn_style = "display:block; width:100%; border-radius:5px; color:white; border:none; padding:8px; text-align:center; font-weight:bold; text-decoration:none; margin-bottom:10px; font-size:14px; display:flex; align-items:center; justify-content:center; gap:8px;"
    c_zl, c_tl = st.columns(2)
    with c_zl: st.markdown(f'<a href="https://zalo.me/0586999991" target="_blank" style="{btn_style} background:#0068FF;"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Icon_of_Zalo.svg/1200px-Icon_of_Zalo.svg.png" width="16"> Zalo</a>', unsafe_allow_html=True)
    with c_tl: st.markdown(f'<a href="https://t.me/ntd934924200" target="_blank" style="{btn_style} background:#24A1DE;"><img src="https://cdn-icons-png.flaticon.com/512/2111/2111646.png" width="16"> Telegram</a>', unsafe_allow_html=True)
    st.divider()
    
    # --- 5. MONG LỜI BÌNH ĐÁNH GIÁ ---
    st.subheader("⭐ Mong Lời Bình Đánh Giá")
    st.caption("Hãy gửi đánh giá, đóng góp, ý kiến của bạn vào hộp thoại bên dưới để chúng tôi hoàn thiện ViralSync Pro tốt hơn.")
    
    rating_val = st.feedback("stars")
    feedback_text = st.text_area("Ý kiến của bạn:", placeholder="Gõ góp ý vào đây...", height=80, label_visibility="collapsed")
    
    if st.button("🚀 Gửi Đánh Giá", use_container_width=True):
        if feedback_text.strip():
            with st.spinner("Đang truyền tín hiệu..."):
                try:
                    bot_token = "8681696911:AAHiyQUGMzWRkOuOVtiXsu-2VYegfzP0_og"
                    chat_id = "7823053892"
                    
                    star_text = "Chưa chọn sao" if rating_val is None else "⭐" * (rating_val + 1)
                    msg = f"🌟 ĐÁNH GIÁ VIRALSYNC PRO:\n- Mức độ: {star_text}\n- Ý kiến: {feedback_text}"
                    safe_msg = urllib.parse.quote(msg)
                    
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={safe_msg}"
                    res = requests.get(url, timeout=10)
                    
                    if res.status_code == 200:
                        st.success("Cảm ơn bạn! Đánh giá đã được gửi trực tiếp đến Admin.")
                    else:
                        st.error(f"Telegram API từ chối: Cấu hình Bot Token hoặc Chat ID chưa đúng.")
                except Exception as e:
                    st.error(f"Có lỗi đường truyền: {e}")
        else:
            st.warning("Vui lòng nhập nội dung ý kiến trước khi gửi nhé!")

    st.divider()

    # --- 6. DONATE / ỦNG HỘ ---
    donate_html = """
    <div style="background: linear-gradient(135deg, #f6d365 0%, #fda085 100%); padding: 15px; border-radius: 10px; text-align: center; color: #333; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 10px 0; color: #c0392b;">💖 Tiếp Lửa Cho Dự Án</h4>
        <p style="font-size: 13px; margin-bottom: 10px; font-weight: 500;">Mỗi cốc trà sữa đều là động lực cho Teams</p>
        <div style="background: white; padding: 10px; border-radius: 8px; display: inline-block;">
            <img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-ACB.png" width="60" style="vertical-align: middle; margin-right: 8px;">
            <span style="font-size: 18px; font-weight: 900; letter-spacing: 1px; vertical-align: middle;">555868686</span>
        </div>
    </div>
    """
    st.markdown(donate_html, unsafe_allow_html=True)
# --- MAIN ---
st.title("🚀 Smart Automation Hub - Nền Tảng")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Content", "🎨 Bước 2: Ảnh AI (Imagen 3)", "📤 Bước 3: Đăng Bài"])

with tab1:
    # --- CSS ANIMATION CHO MŨI TÊN CHỈ DẪN ---
    st.markdown("""
        <style>
        @keyframes slide-right {
            0% { transform: translateX(0); opacity: 1; }
            50% { transform: translateX(5px); opacity: 0.5; }
            100% { transform: translateX(0); opacity: 1; }
        }
        .arrow-anim { display: inline-block; animation: slide-right 1s ease-in-out infinite; color: #ff4b4b; font-weight: 900; margin-right: 5px; }
        .step-title { font-size: 22px; font-weight: 800; color: #2c3e50; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px; }
        .block-title { font-size: 16px; font-weight: 700; color: #6C63FF; margin-top: 15px; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="step-title"><span class="arrow-anim">>></span> BƯỚC 1: NGHIÊN CỨU & SÁNG TẠO NỘI DUNG VIRAL</div>', unsafe_allow_html=True)
    
    # --- KHỐI 1: THIẾT LẬP CHIẾN DỊCH (CAMPAIGN SETUP) ---
    st.markdown('<div class="block-title">📊 1. Cấu Hình Tệp Khách Hàng Mục Tiêu (Targeting)</div>', unsafe_allow_html=True)
    
    col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
    with col_t1:
        platform = st.selectbox("Nền tảng:", ["Facebook Post", "TikTok Video", "Instagram Reels", "YouTube Shorts", "Threads", "Zalo OA"])
    with col_t2:
        role = st.selectbox("Vai trò của bạn:", ["Chuyên gia / Cố vấn", "KOL / KOC Review", "Chủ Doanh Nghiệp / Brand", "Sale / Affiliate", "Idol Livestream"])
    with col_t3:
        target_age = st.selectbox("Độ tuổi KH:", ["Gen Z (18-24)", "Millennials (25-34)", "Gen X (35-50)", "Đa thế hệ"])
    with col_t4:
        target_region = st.selectbox("Văn hóa Vùng:", ["Toàn quốc", "Miền Nam (Phóng khoáng)", "Miền Bắc (Chỉn chu)", "Miền Trung"])
    with col_t5:
        target_city = st.selectbox("Đô thị:", ["Đô thị lớn (Hà Nội, TP.HCM)", "Tỉnh lẻ / Nông thôn", "Không phân biệt"])

    # --- KHỐI NÚT TÌM TREND (AI MARKETER) ---
    if st.button("🔍 AI RÀ QUÉT XU HƯỚNG THỊ TRƯỜNG (TRENDING)", use_container_width=True):
        with st.spinner(f"Giám đốc Marketing AI đang phân tích dữ liệu {platform} tại {target_region}..."):
            try:
                q_trend = f"""Bạn là Giám đốc Marketing (CMO) xuất sắc nhất Việt Nam.
                Hãy phân tích xu hướng MỚI NHẤT hôm nay cho chiến dịch trên '{platform}', với tư cách là '{role}'.
                Tệp khách hàng mục tiêu: '{target_age}', sống tại '{target_city}', văn hóa '{target_region}'.
                Hãy tìm ra 1 góc nhìn (Angle) hoặc nỗi đau (Pain-point) đang cực kỳ viral phù hợp với tệp này.
                Bắt buộc trả về đúng 3 dòng định dạng sau (Tuyệt đối không giải thích thêm):
                Sản phẩm: [Ngách hoặc sản phẩm cụ thể đang hot, VD: Thời trang công sở, Skincare thuần chay...]
                Chân dung: [Phân tích tâm lý/nhu cầu của tệp {target_age} tại {target_region}]
                Angle: [Góc nhìn tiếp cận hoặc Câu nói viral, trend giật gân, nỗi đau thầm kín]"""
                
                res_trend = generate_with_key_rotation([q_trend])
                import re
                sp_match = re.search(r'Sản phẩm:\s*(.*)', res_trend)
                dt_match = re.search(r'Chân dung:\s*(.*)', res_trend)
                tr_match = re.search(r'Angle:\s*(.*)', res_trend)
                
                if sp_match and dt_match and tr_match:
                    st.session_state.k1, st.session_state.k2, st.session_state.trend = sp_match.group(1).strip(), dt_match.group(1).strip(), tr_match.group(1).strip()
                    st.success("✅ Đã bắt mạch thị trường thành công! Dữ liệu đã được điền vào các ô bên dưới.")
                else: st.warning("Mạng lưới đang nghẽn, vui lòng thử lại.")
            except Exception as e: st.error(f"Lỗi phân tích: {e}")

    # --- KHỐI 2: TINH CHỈNH ĐIỂM CHẠM (TOUCHPOINTS) ---
    st.markdown('<div class="block-title">🎯 2. Tinh Chỉnh Thông Điệp Cốt Lõi (Core Message)</div>', unsafe_allow_html=True)
    c_in1, c_in2, c_in3 = st.columns(3)
    with c_in1: sp = st.text_input("Ngách / Sản phẩm (Product)", st.session_state.get('k1', "Phong cách sống tối giản"))
    with c_in2: kh = st.text_input("Chân dung Tâm lý (Persona)", st.session_state.get('k2', "Gen Z thích tự do tài chính"))
    with c_in3: tr = st.text_input("Góc nhìn / Nỗi đau (Angle)", st.session_state.get('trend', "Áp lực đồng trang lứa (Peer pressure)"))
    
    # --- KHỐI 3: NÚT KÍCH HOẠT SẢN XUẤT ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⏩ XUẤT BẢN NỘI DUNG & LỆNH ĐẠO DIỄN ẢNH", type="primary", use_container_width=True):
        with st.spinner("AI Copywriter & AI Art Director đang làm việc..."):
            try:
                q_text = f"Write a highly engaging and viral post for {platform} about '{sp}'. The target audience is '{kh}' located in '{target_city}'. Approach this from the angle of '{tr}'. Tone of voice: {role}. Keep it under 200 words, highly conversational, and format it for high conversion. Format: [CONTENT] Vietnamese text here ||| [PROMPT] English image prompt here."
                prompt_data = [q_text]
                
                # --- XỬ LÝ ĐA ẢNH TỪ SIDEBAR ---
                img_instructions = []
                # Đọc ảnh 1 (Nhân vật chính)
                if st.session_state.get('char1_b64'):
                    try:
                        prompt_data.append(Image.open(io.BytesIO(base64.b64decode(st.session_state.char1_b64.split(',')[1]))))
                        img_instructions.append("Image 1 is the MAIN CHARACTER. Extract their exact facial features, ethnicity, and hairstyle.")
                    except: pass
                # Đọc ảnh 2 (Nhân vật phụ)
                if st.session_state.get('char2_b64'):
                    try:
                        prompt_data.append(Image.open(io.BytesIO(base64.b64decode(st.session_state.char2_b64.split(',')[1]))))
                        img_instructions.append("Image 2 is the SECONDARY CHARACTER. Extract their exact facial features. Place them interacting with the Main Character.")
                    except: pass
                # Đọc ảnh Thú cưng
                if st.session_state.get('pet_b64'):
                    try:
                        prompt_data.append(Image.open(io.BytesIO(base64.b64decode(st.session_state.pet_b64.split(',')[1]))))
                        img_instructions.append("Image 3 is a PET. Include this exact animal species and fur pattern in the scene.")
                    except: pass
                # Đọc ảnh Bối cảnh
                if st.session_state.get('bg_b64'):
                    try:
                        prompt_data.append(Image.open(io.BytesIO(base64.b64decode(st.session_state.bg_b64.split(',')[1]))))
                        img_instructions.append("Image 4 is the REFERENCE BACKGROUND. The environment MUST perfectly match the architectural style, lighting, and mood of this image.")
                    except: pass

                # Xây dựng luật Hình ảnh (Visual Rule)
                if img_instructions:
                    prompt_data[0] += f"\n\nIMPORTANT VISUAL RULE: I attached reference images. {' '.join(img_instructions)} The [PROMPT] MUST be a cohesive English paragraph placing these specific elements into a realistic scene related to '{sp}' and '{tr}'. STRICT composition: medium environmental shot, 9:16 ratio. STRICTLY NO background blur (Deep Depth of Field). Append: 'photojournalism style, wide angle lens (20mm), highly detailed textures, photorealistic, 8k, natural daylight'."
                else:
                    prompt_data[0] += f"\n\nIMPORTANT VISUAL RULE: Create a highly detailed English image generation prompt describing a realistic scene related to '{sp}' and '{tr}'. STRICT composition: medium environmental shot, 9:16 ratio. STRICTLY NO background blur. Append keywords: 'photojournalism style, wide angle lens (20mm), highly detailed textures, photorealistic, 8k, natural daylight'."

                res = generate_with_key_rotation(prompt_data)
                
                if "|||" in res:
                    st.session_state.content, st.session_state.prompt = res.split("|||")[0].replace("[CONTENT]", "").strip(), res.split("|||")[1].replace("[PROMPT]", "").strip()
                else: 
                    st.session_state.content, st.session_state.prompt = res, f"A photojournalistic environmental shot about {sp}, sharp background focus, 9:16 ratio"
            except Exception as e: st.error(f"Lỗi: {e}")

    # --- KHỐI 4: GIAO DIỆN HIỂN THỊ KẾT QUẢ ---
    st.markdown('<div class="block-title">📝 3. Tài Sản Chuyển Đổi (Assets)</div>', unsafe_allow_html=True)
    c_out1, c_out2 = st.columns([1, 1.2])
    with c_out1:
        st.info("💡 Lệnh Đạo diễn (Prompt) đã được AI tối ưu hóa tỷ lệ 9:16, độ nét 8K và cấu trúc không xóa phông. Bạn có thể chỉnh sửa thêm tiếng Anh tại đây trước khi chuyển sang Bước 2.")
        st.session_state.prompt = st.text_area("Đạo diễn Hình ảnh / AI Prompt (EN):", st.session_state.get('prompt',''), height=200)
        copy_button(st.session_state.prompt, "🖼️ Copy Prompt")
    with c_out2:
        st.success(f"📌 Bài viết đã được tối ưu chuẩn văn phong của {st.session_state.get('platform_selected', 'nền tảng')}.")
        st.session_state.content = st.text_area("Bản thảo Content (VN):", st.session_state.get('content',''), height=200)
        copy_button(st.session_state.content, "📋 Copy Content")

with tab2:
    st.subheader("🎨 Studio Ảnh (FLUX.1 Schnell)")
    cl, cr = st.columns([1, 1])
    with cl:
        p_final = st.text_area("Xác nhận Lệnh vẽ:", st.session_state.get('prompt',''), height=150)
        
        if st.button("🎨 VẼ ẢNH NGAY"):
            with st.spinner("Đang kết nối FLUX.1 (Cấu hình 9:16)..."):
                try:
                    hf_headers = {"Authorization": f"Bearer {HF_TOKEN}"}
                    model_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
                    
                    # CẤU HÌNH API MỚI: Ép tỷ lệ 9:16 chính xác bằng cách xác định width/height
                    # Tương đương: 1024x1820 pixels
                    payload = {
                        "inputs": p_final,
                        "parameters": {
                            "width": 1024,
                            "height": 1820
                        }
                    }
                    
                    res = requests.post(model_url, headers=hf_headers, json=payload, timeout=40)
                    
                    if res.status_code == 200:
                        st.session_state.img_res = res.content
                        st.success("Tạo ảnh thành công (9:16 chính xác)!")
                    elif res.status_code == 503: 
                        st.error("Máy chủ HF đang khởi động model. Vui lòng đợi 20 giây và bấm lại.")
                    else: 
                        st.error(f"HF lỗi {res.status_code}")
                except Exception as e: st.error(f"Lỗi: {e}")
                
    with cr:
        if 'img_res' in st.session_state:
            st.image(st.session_state.img_res, use_container_width=True)
            # Thêm nút tải xuống ảnh chuẩn
            st.download_button("📥 Tải ảnh chuẩn (9:16)", st.session_state.img_res, "viral_post_9_16.png", "image/png")

with tab3:
    st.header("📤 Trạm Xuất Bản Nội Dung (Smart Compliance Hub)")
    
    # Lời khuyên tuân thủ pháp lý / An toàn tài khoản
    st.info("""
    **💡 KHUYẾN CÁO TỪ TRẠM TUÂN THỦ THÔNG MINH:**
    Nền tảng Meta (Facebook) có hệ thống AI quét hành vi rất khắt khe. 
    - **Nick Cá Nhân:** Việc dùng Bot giả lập đăng bài sẽ bị AI quét là "Hành vi bất thường/Bị hack", dẫn đến khóa Checkpoint vĩnh viễn. Để bảo vệ tài sản số của bạn, hãy dùng **Phương án 1 (Đăng thủ công)**.
    - **Fanpage Doanh Nghiệp:** Được Meta cấp phép tự động hóa 100% qua cổng Graph API. Không rủi ro, tốc độ tính bằng mili-giây. Hãy dùng **Phương án 2 (Auto Đăng hàng loạt)**.
    """)
    
    col_l, col_r = st.columns([1.2, 1])
    
    with col_r:
        st.subheader("📱 Bản xem trước & Tải xuống")
        st.markdown("**Nội dung bài viết:**")
        st.info(st.session_state.get('content', 'Chưa có bài viết...'))
        
        if st.session_state.get('img_res'):
            st.image(st.session_state.img_res, use_container_width=True)
            # Nút tải ảnh dời sang đây cho tiện lợi
            st.download_button("📥 Tải Hình Ảnh (Chuẩn 9:16)", st.session_state.img_res, "smart_compliance_post.png", "image/png", use_container_width=True)
        else:
            st.warning("Chưa có hình ảnh...")

    with col_l:
        # PHƯƠNG ÁN 1: ĐĂNG THỦ CÔNG
        st.subheader("🛡️ Phương án 1: Đăng Nick Cá Nhân")
        st.success("Tải hình ảnh bên cạnh và copy nội dung để đăng lên trang cá nhân của bạn. Mất 10 giây nhưng An toàn tuyệt đối 100%.")
        
        st.divider()
        
        # PHƯƠNG ÁN 2: AUTO ĐĂNG FANPAGE
        st.subheader("🚀 Phương án 2: Auto Đăng Fanpage (Meta API)")
        
        # Quản lý thêm Fanpage mới
        with st.expander("➕ Quản lý / Thêm Fanpage Mới"):
            p_name = st.text_input("Tên Fanpage (Gợi nhớ):", placeholder="VD: Trạm Tuân Thủ - Chi nhánh 1")
            p_id = st.text_input("Page ID (Dãy số):", placeholder="VD: 123456789012345")
            p_token = st.text_input("Page Access Token:", type="password", placeholder="EAAI...")
            
            if st.button("💾 Lưu Fanpage vào Hệ thống"):
                if p_name and p_id and p_token:
                    st.session_state.fanpages[p_name] = {"id": p_id.strip(), "token": p_token.strip()}
                    save_json(st.session_state.fanpages, 'fanpages.json')
                    st.success(f"Đã lưu Fanpage '{p_name}' thành công!")
                    st.rerun()
                else:
                    st.error("Vui lòng điền đầy đủ Tên, ID và Token!")
        
        # Giao diện Chọn & Đăng hàng loạt
        if st.session_state.fanpages:
            selected_pages = st.multiselect(
                "🎯 Chọn các Fanpage muốn bắn bài viết (Có thể chọn nhiều):", 
                list(st.session_state.fanpages.keys())
            )
            
            if st.button("🔥 AUTO ĐĂNG LÊN CÁC FANPAGE ĐÃ CHỌN", use_container_width=True):
                if not st.session_state.get('content') or not st.session_state.get('img_res'):
                    st.error("❌ Vui lòng tạo Bài viết và Hình ảnh trước khi đăng!")
                elif not selected_pages:
                    st.error("❌ Vui lòng tick chọn ít nhất 1 Fanpage để đăng!")
                else:
                    with st.status("Đang thực thi chiến dịch tự động hóa...", expanded=True) as status:
                        success_count = 0
                        for page in selected_pages:
                            page_info = st.session_state.fanpages[page]
                            st.write(f"🔄 Đang đẩy dữ liệu lên: **{page}**...")
                            try:
                                url = f"https://graph.facebook.com/v19.0/{page_info['id']}/photos"
                                payload = {'message': st.session_state.content, 'access_token': page_info['token']}
                                files = {'source': ('image.png', st.session_state.img_res, 'image/png')}
                                
                                res = requests.post(url, data=payload, files=files)
                                data = res.json()
                                
                                if 'id' in data:
                                    st.write(f"✅ Thành công: {page} (Post ID: {data['id']})")
                                    success_count += 1
                                else:
                                    err_msg = data.get('error', {}).get('message', 'Lỗi không xác định')
                                    st.write(f"❌ Thất bại: {page} - {err_msg}")
                            except Exception as e:
                                st.write(f"❌ Lỗi kết nối {page}: {e}")
                        
                        if success_count == len(selected_pages):
                            status.update(label=f"🎉 Hoàn tất! Đã đăng thành công lên {success_count}/{len(selected_pages)} Fanpage.", state="complete")
                            st.balloons()
                        elif success_count > 0:
                            status.update(label=f"⚠️ Hoàn tất một phần. Đã đăng {success_count}/{len(selected_pages)} Fanpage.", state="warning")
                        else:
                            status.update(label="❌ Chiến dịch thất bại. Không thể đăng lên Fanpage nào.", state="error")
        else:
            st.warning("Chưa có Fanpage nào trong hệ thống. Vui lòng thêm Fanpage ở mục trên.")
