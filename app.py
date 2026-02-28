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
            
     # TÍNH NĂNG MỚI: LOGIN NHANH QUA JAVASCRIPT (ĐÃ TỐI ƯU GIAO DIỆN)
        st.divider()
        clean_cookie = acc.get('cookies', '').replace('\n', '').replace('\r', '').replace('`', '').replace('"', "'").strip()
        js_code = f"""let c = "{clean_cookie}";\nc.split(';').forEach(i => {{ if(i.trim()) document.cookie = i.trim() + "; domain=.facebook.com; path=/"; }});\nwindow.location.href="https://www.facebook.com";"""

        with st.expander("🔑 Lấy Mã Login Siêu Tốc (Chống Checkpoint)", expanded=False):
            st.caption("Copy mã dưới đây để đăng nhập tự động, phục vụ Bước 3 (Phương án 1).")
            st.code(js_code, language="javascript")
            st.info("👉 **HDSD:** Mở Tab Ẩn Danh (Incognito) vào facebook.com ➔ Bấm **F12** ➔ Chọn **Console** ➔ Dán mã trên ➔ Enter.")
            
    else: 
        st.session_state.selected_fb = None
        st.warning("Chưa có Nick FB. Vui lòng thêm ở trên.")

# --- MAIN ---
st.title("🚀 Smart Automation Hub - Nền Tảng")
tab1, tab2, tab3 = st.tabs(["📝 Bước 1: Content", "🎨 Bước 2: Ảnh AI (Imagen 3)", "📤 Bước 3: Đăng Bài"])

with tab1:
    st.subheader("🎯 Bảng Điều Khiển Nội Dung (Bản Thương Mại)")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        role = st.selectbox("Vai trò:", ["KOL / KOC Review", "Sale / Bán hàng", "Chuyên gia / Đào tạo", "Idol Livestream", "Chủ Doanh Nghiệp"])
    with col_f2:
        target_age = st.selectbox("Độ tuổi Khách hàng:", ["Gen Z (18-24 tuổi)", "Millennials (25-34 tuổi)", "Trung niên (35-50 tuổi)", "Mọi lứa tuổi"])
    with col_f3:
        target_region = st.selectbox("Khu vực / Văn hóa:", ["Toàn quốc (Phổ thông)", "Miền Nam (Sôi nổi, trend)", "Miền Bắc (Chỉn chu, sâu sắc)"])

    c1, c2 = st.columns([1, 1.2])
    with c1:
        if st.button("🔍 Phân tích Top Trend Hôm nay", use_container_width=True):
            with st.spinner(f"Đang phân tích dữ liệu mạng xã hội cho {role}..."):
                try:
                    q_trend = f"""Bạn là Chuyên gia phân tích dữ liệu mạng xã hội hot trend hàng đầu Việt Nam.
                    LỆNH TỐI QUAN TRỌNG: Bạn KHÔNG ĐƯỢC PHÉP dùng các từ khóa như 'Tuân Thủ', 'Pháp lý', 'Hệ thống tự động', 'Hỗ trợ tự động', 'B2B', 'Quản lý doanh nghiệp' trong chủ đề hoặc trend, TRỪ KHI vai trò người dùng chọn dưới đây là 'Chủ Doanh Nghiệp'.
                    Hãy phân tích xu hướng MỚI NHẤT hôm nay cho vai trò '{role}', nhắm đến '{target_age}', tại văn hóa '{target_region}'.
                    - Nếu là Idol/KOL/Sale: Bắt buộc chọn các chủ đề B2C hot (Mỹ phẩm, Thời trang, Ẩm thực, Đồ công nghệ...).
                    - Trend phải là các câu nói viral, lóng giới trẻ (slang), drama hot, sự kiện mua sắm, hoặc nỗi đau (pain point) đang được quan tâm nhất hôm nay.
                    Bắt buộc trả về đúng 3 dòng định dạng sau (Tuyệt đối không giải thích thêm):
                    Sản phẩm: [Tên 1 chủ đề/sản phẩm cụ thể phù hợp trend]
                    Đối tượng: [Chi tiết tệp {target_age} tại {target_region}]
                    Trend: [1 Câu nói viral, nỗi đau mua sắm, hoặc phong cách sống đang hot]"""
                    
                    res_trend = generate_with_key_rotation([q_trend])
                    
                    import re
                    sp_match = re.search(r'Sản phẩm:\s*(.*)', res_trend)
                    dt_match = re.search(r'Đối tượng:\s*(.*)', res_trend)
                    tr_match = re.search(r'Trend:\s*(.*)', res_trend)
                    
                    if sp_match and dt_match and tr_match:
                        st.session_state.k1, st.session_state.k2, st.session_state.trend = sp_match.group(1).strip(), dt_match.group(1).strip(), tr_match.group(1).strip()
                        st.success("Đã rà quét và nạp Trend thành công!")
                    else: st.warning("Gemini đang bận, vui lòng bấm lại.")
                except Exception as e: st.error(f"Lỗi lấy trend: {e}")

        st.divider()
        sp = st.text_input("Chủ đề / Sản phẩm", st.session_state.get('k1', "Review phong cách sống"))
        kh = st.text_input("Đối tượng", st.session_state.get('k2', "Giới trẻ Gen Z"))
        tr = st.text_input("Bối cảnh / Trend", st.session_state.get('trend', "Cuộc sống tự do"))
        
        if st.button("✨ TẠO NỘI DUNG VIRAL", use_container_width=True):
            with st.spinner("Đang xử lý dữ liệu và viết bài..."):
                try:
                    q_text = f"Write a viral Facebook personal post for '{sp}' targeting '{kh}' with a '{tr}' vibe, from the perspective of a '{role}'. Under 150 words. Format: [CONTENT] Vietnamese post here ||| [PROMPT] English image prompt here."
                    prompt_data = [q_text]
                    
                    has_image = False
                    if st.session_state.get('selected_fb'):
                        acc = st.session_state.accounts[st.session_state.selected_fb]
                        if acc.get('character_b64'):
                            try:
                                img_data = base64.b64decode(acc['character_b64'].split(',')[1])
                                char_img = Image.open(io.BytesIO(img_data))
                                prompt_data.append(char_img)
                                prompt_data[0] += f"\nIMPORTANT VISUAL RULE: I attached a reference image. The [PROMPT] MUST include: 1) EXACT facial extraction (face shape, features, ethnicity) from the image. 2) Place this EXACT character in a realistic environmental setting relevant to '{sp}' and '{tr}'. 3) STRICT composition: medium environmental portrait shot, 9:16 ratio. STRICTLY NO background blur. 4) Append: 'photojournalism style, wide angle lens (20mm), deep depth of field, sharp background, highly detailed textures, photorealistic, 8k, natural daylight'."
                                has_image = True
                            except: pass
                    
                    if not has_image:
                        prompt_data[0] += f"\nIMPORTANT VISUAL RULE: Create a highly detailed English image generation prompt describing a realistic scene related to '{sp}' and '{tr}'. The [PROMPT] MUST include: 1) A realistic human character relevant to the topic. 2) STRICT composition: medium environmental portrait shot, 9:16 ratio. STRICTLY NO background blur (Deep Depth of Field). The background MUST tell a story. 3) Append keywords: 'photojournalism style, wide angle lens (20mm), deep depth of field, sharp background, environmental portrait, highly detailed textures, photorealistic, 8k, natural daylight'."

                    res = generate_with_key_rotation(prompt_data)
                    
                    if "|||" in res:
                        st.session_state.content, st.session_state.prompt = res.split("|||")[0].replace("[CONTENT]", "").strip(), res.split("|||")[1].replace("[PROMPT]", "").strip()
                    else: 
                        st.session_state.content, st.session_state.prompt = res, f"A photojournalistic environmental shot about {sp}, sharp background focus, 9:16 ratio"
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
