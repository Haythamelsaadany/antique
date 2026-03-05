import streamlit as st
import os, sqlite3, pandas as pd, urllib.parse, datetime
from PIL import Image
import qrcode
from io import BytesIO

# --- الإعدادات والتنسيق ---
st.set_page_config(page_title="جاليري النخبة V21", layout="wide")

DB_NAME = 'gallery_v3.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

# دالة ذكاء اصطناعي (بسيطة) للتسعير
def ai_price_suggest(current_price, country):
    multiplier = 1.2 if country.lower() in ['france', 'italy', 'egypt'] else 1.1
    return round(current_price * multiplier, 2)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                     price REAL, image_path TEXT, country TEXT, date_added TEXT)''')
init_db()

def save_img(file, id):
    img = Image.open(file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    path = os.path.join(IMG_FOLDER, f"{id}.jpg")
    img.save(path, "JPEG", quality=75)
    return path

def get_qr(data):
    qr = qrcode.make(data)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# --- واجهة البرنامج ---
if "auth" not in st.session_state: st.session_state["auth"] = False

if not st.session_state["auth"]:
    st.title("🏛️ دخول النظام الملكي")
    u = st.text_input("المستخدم")
    p = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if u == "admin" and p == "1234":
            st.session_state["auth"] = True
            st.rerun()
else:
    menu = st.sidebar.radio("القائمة الرئيسية", ["المعرض 🖼️", "إضافة صنف ✨", "إدارة البيانات 📂"])

    if menu == "المعرض 🖼️":
        st.header("🖼️ معرض المقتنيات")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        
        if df.empty: st.info("المعرض فارغ")
        else:
            cols = st.columns(3)
            for idx, row in df.iterrows():
                with cols[idx % 3]:
                    with st.container(border=True):
                        if row['image_path'] and os.path.exists(row['image_path']):
                            st.image(row['image_path'], use_container_width=True)
                        st.subheader(row['name'])
                        st.write(f"💰 السعر: {row['price']}$ | 🌍 {row['country']}")
                        
                        # روابط البحث المزدوج (جوجل وإيباي)
                        q = urllib.parse.quote_plus(str(row['name']))
                        c1, c2 = st.columns(2)
                        c1.link_button("Google 🔍", f"https://www.google.com/search?q={q}")
                        c2.link_button("eBay 🛒", f"https://www.ebay.com/sch/i.html?_nkw={q}")
                        
                        with st.expander("🛠️ تعديل / QR / ذكاء اصطناعي"):
                            st.image(get_qr(f"ID:{row['id']}"), width=100)
                            with st.form(f"f_{row['id']}"):
                                new_p = st.number_input("السعر", value=float(row['price']))
                                new_i = st.file_uploader("تغيير الصورة", type=['jpg','png'])
                                
                                if st.form_submit_button("🤖 اقتراح سعر AI"):
                                    suggested = ai_price_suggest(new_p, str(row['country']))
                                    st.info(f"السعر المقترح: {suggested}$")
                                
                                if st.form_submit_button("💾 حفظ"):
                                    path = row['image_path']
                                    if new_i: path = save_img(new_i, row['id'])
                                    with sqlite3.connect(DB_NAME) as conn:
                                        conn.execute("UPDATE antiques SET price=?, image_path=? WHERE id=?", (new_p, path, row['id']))
                                    st.rerun()

    elif menu == "إدارة البيانات 📂":
        st.header("📂 إدارة البيانات والاستيراد")
        # --- ميزة الاستيراد التي طلبتها ---
        st.subheader("📥 استيراد من إكسيل")
        file = st.file_uploader("ارفع ملف Excel", type=['xlsx'])
        if st.button("🚀 تنفيذ الاستيراد"):
            if file:
                df_excel = pd.read_excel(file)
                with sqlite3.connect(DB_NAME) as conn:
                    df_excel.to_sql('antiques', conn, if_exists='append', index=False)
                st.success("تم الاستيراد بنجاح!")
        
        st.divider()
        if st.button("📤 تصدير إكسيل"):
            with sqlite3.connect(DB_NAME) as conn:
                pd.read_sql("SELECT * FROM antiques", conn).to_excel("inventory.xlsx", index=False)
            st.success("تم الحفظ في inventory.xlsx")

    elif menu == "إضافة صنف ✨":
        with st.form("add"):
            st.subheader("إضافة يدوي")
            f_id = st.text_input("ID")
            f_n = st.text_input("الاسم")
            f_p = st.number_input("السعر")
            f_c = st.text_input("البلد")
            f_i = st.file_uploader("صورة")
            if st.form_submit_button("حفظ"):
                if f_id and f_n:
                    img = save_img(f_i, f_id) if f_i else ""
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT INTO antiques (id, name, price, image_path, country) VALUES (?,?,?,?,?)", (f_id, f_n, f_p, img, f_c))
                    st.success("تم!")