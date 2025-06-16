import streamlit as st

st.title("バナスコAI 採点ツール")
st.write("バナー画像をアップすると、AIが採点＆改善コメントを表示します。")
import streamlit as st
from PIL import Image

st.title("バナスコAI 採点ツール")
st.write("バナー画像をアップすると、AIが採点＆改善コメントを表示します。")

# ① 画像アップロード欄
uploaded_file = st.file_uploader("▶︎ バナー画像をアップロード", type=["png", "jpg", "jpeg"])

# ② アップロードされた画像を表示
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_column_width=True)

    # ③ 仮スコア＆コメント（ここは後でAI連携と差し替え）
    st.subheader("🧠 AIの採点結果（仮）")
    st.write("📊 スコア：**A評価**")
    st.write("💬 コメント：`文字の視認性が良く、パッと目を引きます！`")
