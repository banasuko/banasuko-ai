import streamlit as st
import base64
import io
import os
import re
import requests
from PIL import Image
from datetime import datetime
from openai import OpenAI

import auth_utils # Import authentication utility


# Streamlit UI configuration (set page title etc. for this specific page)
st.set_page_config(layout="wide", page_title="バナスコAI - コピー生成")

# --- Login Check ---
# This is crucial! Code below this line will only execute if the user is logged in.
auth_utils.check_login()

# --- OpenAI Client Initialization ---
# Initialize OpenAI client after login check, when OpenAI API key is available from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("❌ OpenAI APIキーが見つかりませんでした。`.env` を確認してください。")
    st.stop()
client = OpenAI(api_key=openai_api_key)


st.title("📸 バナー画像からコピー案を生成")

# 1. 画像アップロード
uploaded_image = st.file_uploader("バナー画像をアップロード", type=["jpg", "png"])
if uploaded_image:
    image = Image.open(uploaded_image)
    st.image(image, caption="アップロードされた画像", use_container_width=True)

# 2. カテゴリー選択
category = st.selectbox("カテゴリーを選択", [
    "美容室", "脱毛サロン", "エステ", "ネイル・まつげ", "ホワイトニング",
    "整体・接骨院", "学習塾", "子ども写真館", "飲食店", "その他"
])

# 3. 補足情報入力
target = st.text_input("ターゲット層（例：30代女性、経営者など）")
feature = st.text_area("商品の特徴・アピールポイント")
tone = st.selectbox("トーン（雰囲気）を選択", ["親しみやすい", "高級感", "情熱的", "おもしろ系", "真面目"])

# 4. コピー生成数 (プランに応じた上限設定)
# Get current plan from session state
user_plan = st.session_state.get("plan", "Free") 

# Determine max copy count based on plan
max_copy_count = 0
if user_plan == "Light":
    max_copy_count = 3
elif user_plan == "Pro":
    max_copy_count = 5
elif user_plan in ["Team", "Enterprise"]: # Team and Enterprise
    max_copy_count = 10 # Assuming 10 for Team/Enterprise based on document
else: # Free or Guest plan
    max_copy_count = 0 # Free plan cannot generate copies

# Options for selectbox, up to max_copy_count
copy_count_options = [i for i in [2, 5, 10] if i <= max_copy_count]
if not copy_count_options and max_copy_count > 0: # If max_copy_count is not 0 but none of 2,5,10 fit
    copy_count_options = [max_copy_count] # Default to max if specific options don't fit

if not copy_count_options: # If max_copy_count is 0 (Free/Guest)
    st.warning(f"コピー生成機能は{user_plan}プランではご利用いただけません。")
    st.info("コピー生成機能はLightプラン以上でご利用可能です。")
    copy_count = 0 # Ensure copy_count is 0 to prevent generation
else:
    copy_count = st.selectbox("コピー生成数を選んでください (プラン上限: " + str(max_copy_count) + "案)", copy_count_options, index=0)


# 5. 生成ボタン
if st.button("コピーを生成する"):
    # First, check if the user can use this feature at all based on plan
    if user_plan == "Free" or max_copy_count == 0:
        st.warning("この機能はFreeプランではご利用いただけません。")
        st.info("コピー生成機能はLightプラン以上でご利用可能です。プランのアップグレードをご検討ください。")
    # Then, check remaining uses
    elif st.session_state.remaining_uses <= 0:
        st.warning(f"残り回数がありません。（{st.session_state.plan}プラン）")
        st.info("利用回数を増やすには、プランのアップグレードが必要です。")
    else:
        # If plan allows and uses are available, proceed to consume and generate
        if auth_utils.update_user_uses_in_firestore_rest(st.session_state["user"], st.session_state["id_token"]): # Consume 1 use
            with st.spinner("コピー案を生成中..."):
                # Yakujiho check required categories
                needs_yakkihou = category in ["脱毛サロン", "エステ", "ホワイトニング"]

                # Prompt construction
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
                        model="gpt-4o", # Using GPT-4o for copy generation
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
        else:
            st.error("利用回数の更新に失敗しました。コピー生成は実行されませんでした。")


