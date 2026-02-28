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
    HF_TOKEN = st.secrets["HF_TOKEN"]
    genai.configure(api_key=GEMINI_API_KEY)
except:
    st.error("❌ Thiếu GEMINI_API_KEY hoặc HF_TOKEN trong thiết lập Secrets!")
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
        st.subheader("🎯 Cập nhật Trend Thời Gian Thực")
        
        # Nút gọi Gemini phân tích Trend mạng xã hội hôm nay
        if st.button("🔍 Phân tích Top Trend Hôm nay (Bởi Gemini)"):
            with st.spinner("Đang quét dữ liệu mạng xã hội hôm nay..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    prompt_trend = """Hôm nay là ngày hiện tại. Bạn là Giám đốc Sáng tạo (Creative Director) tại Việt Nam. 
                    Hãy phân tích xu hướng mạng xã hội hôm nay và đưa ra 1 ý tưởng viết bài viral cho thương hiệu 'Trạm Tuân Thủ Thông Minh' (Smart Compliance Hub).
                    Bắt buộc trả về đúng 3 dòng định dạng sau (Tuyệt đối không giải thích thêm):
                    Sản phẩm: [1 Dịch vụ cụ thể của Trạm Tuân Thủ Thông Minh phù hợp với trend]
                    Đối tượng: [1 Tệp khách hàng cụ thể nhất]
                    Trend: [1 Xu hướng, sự kiện, hoặc nỗi đau (pain point) đang được quan tâm nhất hôm nay]"""
                    
                    res_trend = model.generate_content(prompt_trend).text
                    
                    # Tự động bóc tách dữ liệu và điền vào ô
                    import re
                    sp_match = re.search(r'Sản phẩm:\s*(.*)', res_trend)
                    dt_match = re.search(r'Đối tượng:\s*(.*)', res_trend)
                    tr_match = re.search(r'Trend:\s*(.*)', res_trend)
                    
                    if sp_match and dt_match and tr_match:
                        st.session_state.k1 = sp_match.group(1).strip()
                        st.session_state.k2 = dt_match.group(1).strip()
                        st.session_state.trend = tr_match.group(1).strip()
                        st.success("Đã cập nhật bộ từ khóa Hot nhất hôm nay!")
                    else:
                        st.warning("Gemini đang bận. Vui lòng bấm thử lại.")
                except Exception as e:
                    st.error(f"Lỗi lấy trend: {e}")

        st.divider()
        sp = st.text_input("Sản phẩm / Dịch vụ", st.session_state.get('k1', "Trạm Tuân Thủ Thông Minh"))
        kh = st.text_input("Đối tượng", st.session_state.get('k2', "Chủ doanh nghiệp SME"))
        tr = st.text_input("Trend / Bối cảnh", st.session_state.get('trend', "Tối ưu vận hành"))
        
        if st.button("✨ TẠO NỘI DUNG VIRAL"):
            with st.spinner("Gemini đang viết bài..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    q = f"""Write a viral Facebook personal profile post for {sp} targeting {kh} with a {tr} vibe.
                    CRITICAL RULES FOR [CONTENT]:
                    - Extremely short and punchy (under 150 words).
                    - Conversational, personal storytelling style (NOT a sales fanpage).
                    - Start with a strong hook/question.
                    - End with an open question to drive comments.
                    - NO hard selling.
                    Format strictly: [CONTENT] Vietnamese post here ||| [PROMPT] English image prompt here."""
                    
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
        st.session_state.content = st.text_area("Bài viết (Chuẩn viral cá nhân):", st.session_state.get('content',''), height=220)
        copy_button(st.session_state.content, "📋 Copy Content")
        st.divider()
        st.session_state.prompt = st.text_area("Prompt vẽ ảnh (EN):", st.session_state.get('prompt',''), height=100)
        copy_button(st.session_state.prompt, "🖼️ Copy Prompt")

with tab2:
    st.subheader("🎨 Studio Ảnh (Smart Compliance Hub - 2 Server Tốt Nhất)")
    cl, cr = st.columns([1, 1])
    with cl:
        engine = st.selectbox("Lựa chọn Máy chủ (Đã kiểm chứng):", [
            "1. FLUX.1 Schnell (Máy chủ Hugging Face - Đã test Tốt)",
            "2. Stable Diffusion XL (Máy chủ Together AI - Cực Nhanh)"
        ])
        p_final = st.text_area("Xác nhận Lệnh vẽ (Tiếng Anh):", st.session_state.get('prompt',''), height=150)
        
        if st.button("🎨 VẼ ẢNH NGAY"):
            with st.spinner(f"Đang kết nối {engine.split('(')[0].strip()}..."):
                try:
                    if "Together AI" in engine:
                        # ---------------------------------------------------------
                        # MÁY CHỦ 2: TOGETHER AI (ỔN ĐỊNH, DÙNG API KEY MỚI)
                        # ---------------------------------------------------------
                        together_key = st.secrets.get("TOGETHER_API_KEY")
                        if not together_key:
                            st.error("❌ Chưa có TOGETHER_API_KEY trong Secrets. Vui lòng cài đặt!")
                            st.stop()
                            
                        url = "https://api.together.xyz/v1/images/generations"
                        headers = {
                            "Authorization": f"Bearer {together_key}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "model": "stabilityai/stable-diffusion-xl-base-1.0",
                            "prompt": p_final,
                            "n": 1,
                            "steps": 20,
                            "response_format": "b64_json"
                        }
                        res = requests.post(url, headers=headers, json=payload, timeout=40)
                        data = res.json()
                        
                        if "data" in data and len(data["data"]) > 0:
                            import base64
                            b64_img = data["data"][0]["b64_json"]
                            st.session_state.img_res = base64.b64decode(b64_img)
                            st.success("Tuyệt vời! Together AI đã tạo ảnh thành công.")
                        elif "error" in data:
                            st.error(f"Lỗi Together AI: {data['error']['message']}")
                        else:
                            st.error(f"Lỗi API: {data}")
                            
                    else:
                        # ---------------------------------------------------------
                        # MÁY CHỦ 1: HUGGING FACE (FLUX.1 SCHNELL)
                        # ---------------------------------------------------------
                        hf_headers = {"Authorization": f"Bearer {HF_TOKEN}"}
                        model_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

                        res = requests.post(model_url, headers=hf_headers, json={"inputs": p_final}, timeout=40)
                        
                        if res.status_code == 200 and 'image' in res.headers.get('content-type', ''):
                            st.session_state.img_res = res.content
                            st.success("Tuyệt vời! Hugging Face đã tạo ảnh thành công.")
                        elif res.status_code == 503:
                            st.error("Máy chủ đang tải model (Mã 503). Vui lòng đợi khoảng 20 giây và bấm nút vẽ lại.")
                        else:
                            err_msg = res.json().get('error', 'Không rõ lỗi') if 'application/json' in res.headers.get('content-type', '') else res.text
                            st.error(f"HF báo lỗi {res.status_code}: {err_msg}")

                except Exception as e:
                    st.error(f"Lỗi kết nối hệ thống: {e}")
                
    with cr:
        if 'img_res' in st.session_state:
            try:
                st.image(st.session_state.img_res, use_container_width=True)
                st.download_button("📥 Tải ảnh về", st.session_state.img_res, "smart_compliance_hub_post.png", "image/png")
            except Exception as e:
                st.warning("Lỗi hiển thị dữ liệu ảnh. Vui lòng bấm vẽ lại.")
with tab3:
    st.header("📤 Trạm Đăng Bài")
    if st.session_state.get('selected_fb'):
        st.success(f"Đã nạp Nick: **{st.session_state.selected_fb}**")
        if st.button("🚀 KÍCH HOẠT ROBOT"):
            st.info("Module Playwright đang chờ cập nhật...")
    else: st.error("Hãy chọn nick ở Sidebar.")
