import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import os
from datetime import datetime
import json

# CSS読み込み
with open("src/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# データベース初期化
if not os.path.exists("data/uploads"):
    os.makedirs("data/uploads")
conn = sqlite3.connect("data/plants.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, user TEXT, plant TEXT, date TEXT, image_path TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS likes (image_path TEXT PRIMARY KEY, likes INTEGER)''')
conn.commit()

# サイドバーメニュー
st.sidebar.title("MyGarden")
page = st.sidebar.radio("メニュー", ["ホーム", "成長記録", "栽培ガイド", "シェア・コンテスト", "データ分析"])

# ホーム画面
if page == "ホーム":
    st.title("🌱 MyGarden")
    st.write("家庭菜園を楽しみましょう！")
    st.button("今すぐ記録する", key="cta", on_click=lambda: st.session_state.update({"page": "成長記録"}))
    
    st.subheader("最近の投稿")
    records = c.execute("SELECT plant, date, image_path FROM records ORDER BY date DESC LIMIT 3").fetchall()
    cols = st.columns(3)
    # for i, (plant, date, path) in enumerate(records):
    #     with cols[i]:
    #         st.markdown(f"<div class='card'><img src='{path}' width='100%'><p>{plant} ({date})</p></div>", unsafe_allow_html=True)
    for i, (plant, date, path) in enumerate(records):
        with cols[i]:
            st.image(path, use_container_width=True)
            st.caption(f"{plant} ({date})")
            
# 成長記録画面
elif page == "成長記録":
    st.title("📸 成長記録")
    
    # 入力フォーム
    with st.form("record_form"):
        user = st.text_input("ユーザー名", "Guest")
        plant = st.selectbox("植物", ["トマト", "バジル", "レタス"])
        uploaded_file = st.file_uploader("写真をアップロード", type=["jpg", "png"])
        submitted = st.form_submit_button("記録する")
        
        if submitted and uploaded_file:
            image = Image.open(uploaded_file)
#            image_path = f"data/uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            ext = os.path.splitext(uploaded_file.name)[1]  # ".jpg" や ".png" を取得
            image_path = f"data/uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            image.save(image_path)
            c.execute("INSERT INTO records (user, plant, date, image_path) VALUES (?, ?, ?, ?)",
                      (user, plant, datetime.now().strftime("%Y-%m-%d"), image_path))
            conn.commit()
            st.success("記録しました！")
    
    # 記録表示
    st.subheader("これまでの記録")
    records = c.execute("SELECT plant, date, image_path FROM records WHERE user = ?", (user,)).fetchall()
    for plant, date, path in records:
            st.image(path, width=200)
            st.write(f"{plant} — {date}")
    
    # 簡易グラフ
    if records:
        df = pd.DataFrame(records, columns=["plant", "date", "image_path"])
        df["date"] = pd.to_datetime(df["date"])
        counts = df.groupby("date").size()
        st.line_chart(counts)

# 栽培ガイド画面
elif page == "栽培ガイド":
    st.title("📖 栽培ガイド")
    
    guides = {
        "トマト": {"水やり": "週2回", "日光": "6時間以上", "注意": "支柱を立てる"},
        "バジル": {"水やり": "週3回", "日光": "4時間以上", "注意": "葉をこまめに摘む"}
    }
    
    plant = st.selectbox("植物を選択", list(guides.keys()))
    region = st.selectbox("地域", ["北海道", "関東", "九州"])
    
    if st.button("ガイドを表示"):
        guide = guides[plant]
        st.markdown(f"""
        <div class='card'>
            <h3>{plant}</h3>
            <p>水やり: {guide['水やり']}</p>
            <p>日光: {guide['日光']}</p>
            <p>注意: {guide['注意']}</p>
        </div>
        """, unsafe_allow_html=True)
        if region == "北海道":
            st.write("※寒冷地では室内栽培を推奨")

# シェア・コンテスト画面
elif page == "シェア・コンテスト":
    st.title("📷 みんなの菜園")
    
    records = c.execute("SELECT plant, date, image_path FROM records").fetchall()
    cols = st.columns(3)
    for i, (plant, date, path) in enumerate(records):
        with cols[i % 3]:
            likes = c.execute("SELECT likes FROM likes WHERE image_path = ?", (path,)).fetchone()
            likes = likes[0] if likes else 0
            # st.markdown(f"<div class='card'><img src='{path}' width='100%'><p>{plant} ({date})</p><p>いいね: {likes}</p></div>", unsafe_allow_html=True)
            st.image(path, use_container_width=True)
            st.write(f"{plant} ({date}) — いいね: {likes}")            
            if st.button("♥", key=path):
                c.execute("INSERT OR REPLACE INTO likes (image_path, likes) VALUES (?, ?)", (path, likes + 1))
                conn.commit()
    
    # ランキング
    st.subheader("ランキング")
    likes_data = c.execute("SELECT image_path, likes FROM likes ORDER BY likes DESC LIMIT 3").fetchall()
    for i, (path, likes) in enumerate(likes_data):
        record = c.execute("SELECT plant, date FROM records WHERE image_path = ?", (path,)).fetchone()
#        st.markdown(f"<div class='card'><p>{i+1}位: {record[0]} ({record[1]}) - いいね: {likes}</p><img src='{path}' width='200'></div>", unsafe_allow_html=True)
        st.image(path, use_container_width=True)
        st.write(f"{plant} ({date}) — いいね: {likes}")       

# データ分析画面
elif page == "データ分析":
    st.title("📊 データ分析")
    
    df = pd.read_sql_query("SELECT plant, date, user FROM records", conn)
    
    if not df.empty:
        # 植物分布
        plant_counts = df["plant"].value_counts()
        fig, ax = plt.subplots()
        ax.pie(plant_counts, labels=plant_counts.index, autopct="%1.1f%%", colors=["#4CAF50", "#8B4513", "#FFD700"])
        st.pyplot(fig)
        
        # 投稿頻度
        df["date"] = pd.to_datetime(df["date"])
        counts = df.groupby("date").size()
        st.bar_chart(counts)
        
        # レコメンド
        st.subheader("おすすめ")
        plant_history = df["plant"].unique()
        if "トマト" in plant_history:
            st.markdown("<div class='card'><p>次におすすめ: バジル</p><p>必要な用具: 支柱</p></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='card'><p>次におすすめ: レタス</p><p>必要な用具: ジョウロ</p></div>", unsafe_allow_html=True)
    else:
        st.write("データがまだありません。")

conn.close()