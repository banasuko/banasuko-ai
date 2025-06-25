import streamlit as st
from PIL import Image
from openai import OpenAI
import io

# OpenAIクライアント初期化（.streamlit/secrets.toml で設定済みを想定）
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("📸 バナー画像からコピー案を生成")

# 1. 画像アップロード
uploaded_image = st.file_uploader("バナー画像をアップロード", type=["jpg", "png"])
if uploaded_image:
    image = Image.open(uploaded_image)
    st.image(image, caption="アップロードされた画像", use_column_width=True)

# 2. カテゴリー選択
category = st.selectbox("カテゴリーを選択", [
    "美容室", "脱毛サロン", "エステ", "ネイル・まつげ", "ホワイトニング",
    "整体・接骨院", "学習塾", "子ども写真館", "飲食店", "その他"
])

# 3. 補足情報入力
target = st.text_input("ターゲット層（例：30代女性、経営者など）")
feature = st.text_area("商品の特徴・アピールポイント")
tone = st.selectbox("トーン（雰囲気）を選択", ["親しみやすい", "高級感", "情熱的", "おもしろ系", "真面目"])

# 4. コピー生成数
copy_count = st.selectbox("コピー生成数を選んでください", [2, 5, 10], index=1)

# 5. 生成ボタン
if st.button("コピーを生成する"):

    with st.spinner("コピー案を生成中..."):

        # 薬機法チェックが必要なカテゴリ
        needs_yakkihou = category in ["脱毛サロン", "エステ", "ホワイトニング"]

        # プロンプト構成
        system_prompt = "あなたは優秀な広告コピーライターです。"
        user_prompt = f"""
以下の情報をもとに、バナー広告に使えるキャッチコピーを{copy_count}案提案してください。
【業種】{category}
【ターゲット層】{target}
【特徴・アピールポイント】{feature}
【トーン】{tone}
- 各コピーは30文字以内に収めてください。
- 同じ方向性のコピーは避け、バリエーションを持たせてください。
{ '・薬機法に配慮し、「治る」「即効」「永久」「医療行為的表現」などは避けてください。' if needs_yakkihou else '' }
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            output = response.choices[0].message.content.strip()

            st.subheader("✍️ コピー案")
            st.markdown(output)

            if needs_yakkihou:
                st.subheader("🔍 薬機法チェック")
                st.info("※ このカテゴリーでは薬機法に配慮した表現になっているか注意してください。\nNGワード例：「即効」「治る」「永久」など")

        except Exception as e:
            st.error(f"コピー生成中にエラーが発生しました：{e}")
