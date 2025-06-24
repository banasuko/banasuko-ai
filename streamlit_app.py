import streamlit as st
import base64
import io
import os
import requests
from PIL import Image
from datetime import datetime
from openai import OpenAI
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# --- 設定 ---
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)
GAS_URL = "https://script.google.com/macros/s/AKfycbyRt9iAJZAjr4yKj_O0BxdyT-GGV8vT6ogJaS_xI6LcW8FV7oE-gRkpVaGzl8D59-5x/exec"
FOLDER_ID = "1oRyCu2sU9idRrj5tq5foQXp3ArtCW7rP"

# --- Google Drive アップロード関数 ---
def upload_image_to_drive_get_url(pil_image, filename):
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("credentials.json")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("credentials.json")
    drive = GoogleDrive(gauth)

    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    buf.seek(0)

    file_drive = drive.CreateFile({
        'title': filename,
        'mimeType': 'image/png',
        'parents': [{'id': FOLDER_ID}]
    })
    file_drive.SetContentString(base64.b64encode(buf.read()).decode(), encoding='base64')
    file_drive.Upload()
    file_drive.InsertPermission({'type': 'anyone', 'role': 'reader'})
    return f"https://drive.google.com/uc?export=view&id={file_drive['id']}"

# --- UI ---
st.set_page_config(layout="centered", page_title="バナスコAI")
st.title("🧠 バナー広告 採点AI - バナスコ")

user_name = st.text_input("ユーザー名")
platform = st.selectbox("媒体", ["Instagram", "GDN", "YDN"])
category = st.selectbox("カテゴリ", ["広告", "投稿"] if platform == "Instagram" else ["広告"])
has_ad_budget = st.selectbox("広告予算", ["あり", "なし"])
purpose = st.selectbox("目的", ["プロフィール誘導", "リンククリック", "保存数増加"])
industry = st.selectbox("業種", ["美容", "飲食", "教育", "不動産", "その他"])
post_genre = st.selectbox("ジャンル", ["ノウハウ系", "共感・ストーリー系", "キャンペーン紹介", "商品紹介"])
score_type = st.radio("スコア方式", ["A/B/C", "100点満点"])
banner_name = st.text_input("バナー名（任意）")
result = st.text_input("実績（任意）")
follower_gain = st.text_input("フォロワー増加（任意）")
memo = st.text_area("メモ（任意）")
ab_test = st.radio("ABテスト用画像？", ["Aパターン", "Bパターン", "該当なし"])
uploaded_file = st.file_uploader("バナー画像をアップロード", type=["png", "jpg", "jpeg"])

# --- メイン処理 ---
if uploaded_file and st.button("🚀 採点＋保存"):
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロード画像", use_column_width=True)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    img_str = base64.b64encode(buf.getvalue()).decode()

    with st.spinner("AIが採点中です..."):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは広告のプロです。"},
                {"role": "user", "content": [
                    {"type": "text", "text":
                        "以下の広告バナーをプロ視点で採点してください：\n"
                        "【評価基準】\n"
                        "1. 内容が一瞬で伝わるか\n"
                        "2. コピーの見やすさ\n"
                        "3. 行動喚起\n"
                        "4. 写真とテキストの整合性\n"
                        "5. 情報量のバランス\n"
                        f"【出力形式】\nスコア：{'A/B/C' if score_type == 'A/B/C' else '100点満点'}\n改善コメント：2～3行"
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
                ]}
            ],
            max_tokens=600
        )
        content = response.choices[0].message.content
        score = next((l.replace("スコア：", "").strip() for l in content.splitlines() if "スコア" in l), "")
        comment = next((l.replace("改善コメント：", "").strip() for l in content.splitlines() if "改善コメント" in l), "")

    st.success(f"スコア：{score}")
    st.markdown(f"**改善コメント：** {comment}")

    image_url = upload_image_to_drive_get_url(image, uploaded_file.name)

    data = {
        "用途種別": category,
        "提案日": datetime.today().strftime("%Y-%m-%d"),
        "画像URL": image_url,
        "採点日": datetime.today().strftime("%Y-%m-%d"),
        "業種": industry,
        "投稿or広告": category,
        "媒体": platform,
        "ジャンル": post_genre,
        "点数": score,
        "コメント": comment,
        "修正案あり": "あり" if comment else "なし",
        "実施状況": "未実施",
        "クリック率": "",
        "CPC": "",
        "フォロワー増加数": follower_gain,
        "保存数": "",
        "ABテスト": ab_test,
        "備考": memo
    }

    response = requests.post(GAS_URL, json=data)
    st.write("📡 GAS応答ステータスコード:", response.status_code)
    st.write("📄 GAS応答本文:", response.text)

    if response.status_code == 200:
        st.success("📊 スプレッドシートに記録しました！")
    else:
        st.error("❌ スプレッドシート送信エラー")
