import streamlit as st
import base64
import io
import os
import re
import requests
from PIL import Image
from datetime import datetime
from openai import OpenAI

import auth_utils # ✅ auth_utils.py をインポート


# GASとGoogle Driveの情報
GAS_URL = "https://script.google.com/macros/s/AKfycbzcrcsOUGxabxaIJ-Dhh__tfbeELmVuIH_E7U3h_riDoRZirjC563MxZdzWsQkzhVbG/exec"

# Helper function to sanitize values
def sanitize(value):
    """Replaces None or specific strings with 'エラー' (Error)"""
    if value is None or value == "取得できず":
        return "エラー"
    return value

# Google Drive upload functionality is removed in this version


# Streamlit UI configuration
st.set_page_config(layout="wide", page_title="バナスコAI")

# --- ロゴの表示 ---
logo_path = "banasuko_logo_icon.png"

try:
    logo_image = Image.open(logo_path)
    st.sidebar.image(logo_image, use_container_width=True) # サイドバーの幅に合わせて表示
except FileNotFoundError:
    st.sidebar.error(f"ロゴ画像 '{logo_path}' が見つかりません。ファイルが正しく配置されているか確認してください。")

# --- ログインチェックを実行 ---
# これが最も重要！この行より下は、ログイン済みの場合にのみ実行されます
auth_utils.check_login()

# --- OpenAIクライアントの初期化 ---
# ログインチェック後に、OpenAI APIキーが環境変数から利用可能になった状態で初期化
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("❌ OpenAI APIキーが見つかりませんでした。`.env` を確認してください。")
    st.stop()
client = OpenAI(api_key=openai_api_key) # ✅ OpenAIクライアントをここで初期化


# --- カスタムCSSの追加 (背景色を完全に白に固定 & Newpeace デザインに合わせた明るいテーマ) ---
st.markdown(
    """
    <style>
    /* 全体の背景色を強制的に白に設定 */
    body {
        background-color: #FFFFFF !important;
        background-image: none !important; /* 念のため、背景画像も無効化 */
    }

    /* Streamlitのメインコンテナ */
    .main .block-container {
        background-color: #FFFFFF; /* メインコンテナの背景も白 */
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
        border-radius: 12px;
        box-shadow: 0px 8px 20px rgba(0, 0, 0, 0.08);
    }

    /* サイドバー */
    .stSidebar {
        background-color: #F8F8F8; /* 少し明るいグレー */
        border-right: none;
        box-shadow: 2px 0px 10px rgba(0, 0, 0, 0.05);
    }

    /* ボタン */
    .stButton > button {
        background-color: #0000FF; /* primaryColor (鮮やかな青) */
        color: white;
        border-radius: 8px;
        border: none;
        box-shadow: 0px 4px 10px rgba(0, 0, 255, 0.2);
        transition: background-color 0.2s, box-shadow 0.2s;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #3333FF;
        box-shadow: 0px 6px 15px rgba(0, 0, 255, 0.3);
    }
    .stButton > button:active {
        background-color: #0000CC;
        box-shadow: none;
    }

    /* Expander */
    .stExpander {
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        background-color: #FFFFFF;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    .stExpander > div > div {
        background-color: #F8F8F8;
        border-bottom: 1px solid #E0E0E0;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }
    .stExpanderDetails {
        background-color: #FFFFFF;
    }

    /* テキスト入力、セレクトボックスなど */
    div[data-baseweb="input"] input,
    div[data-baseweb="select"] span,
    div[data-baseweb="textarea"] textarea,
    .stSelectbox .st-bv, /* Selectbox display value */
    .stTextInput .st-eb, /* Text input display */
    .stTextArea .st-eb /* Textarea display */
    {
        background-color: #FFFFFF !important;
        color: #333333 !important;
        border-radius: 8px;
        border: 1px solid #E0E0E0;
        box-shadow: inset 0px 1px 3px rgba(0,0,0,0.05);
    }
    /* フォーカス時のスタイル */
    div[data-baseweb="input"] input:focus,
    div[data-baseweb="select"] span:focus,
    div[data-baseweb="textarea"] textarea:focus,
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"]:focus-within,
    div[data-baseweb="textarea"]:focus-within {
        border-color: #0000FF;
        box-shadow: 0 0 0 2px rgba(0, 0, 255, 0.3);
    }

    /* メトリック */
    [data-testid="stMetricValue"] {
        color: #FFD700; /* 鮮やかな黄色 (Newpeaceの黄色をイメージ) */
        font-size: 2.5rem;
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #666666;
        font-size: 0.9rem;
    }
    [data-testid="stMetricDelta"] {
        color: #333333;
    }

    /* Info, Success, Warning, Errorボックス */
    .stAlert {
        color: #333333;
    }
    .stAlert.stAlert-info {
        background-color: #E0EFFF;
        border-left-color: #0000FF;
    }
    .stAlert.stAlert-success {
        background-color: #E0FFE0;
        border-left-color: #00AA00;
    }
    .stAlert.stAlert-warning {
        background-color: #FFFBE0;
        border-left-color: #FFD700;
    }
    .stAlert.stAlert-error {
        background-color: #FFE0E0;
        border-left-color: #FF0000;
    }

    /* コードブロック */
    code {
        background-color: #F0F0F0 !important;
        color: #000080 !important;
        border-radius: 5px;
        padding: 0.2em 0.4em;
    }
    pre code {
        background-color: #F0F0F0 !important;
        padding: 1em !important;
        overflow-x: auto;
    }

    /* サイドバーのテキスト色を調整 */
    .stSidebar [data-testid="stText"],
    .stSidebar [data-testid="stMarkdownContainer"],
    .stSidebar .st-emotion-cache-1jm692h {
        color: #333333;
    }

    /* セレクトボックスのドロップダウンリストの背景色 */
    div[data-baseweb="popover"] > div {
        background-color: #FFFFFF !important;
        color: #333333 !important;
    }
    /* セレクトボックスのドロップダウンリストのアイテムのテキスト色 */
    div[data-baseweb="popover"] > div > ul > li {
        color: #333333 !important;
    }
    /* セレクトボックスのドロップダウンリストのホバー色 */
    div[data-baseweb="popover"] > div > ul > li[data-mouse-entered="true"] {
        background-color: #E0EFFF !important; /* 薄い青 */
        color: #0000FF !important; /* アクセントの青 */
    }


    </style>
    """,
    unsafe_allow_html=True
)
# --- カスタムCSSの終わり ---

# --- アプリケーション本体（ログイン済みの場合のみ実行） ---
st.title("🧠 バナー広告 採点AI - バナスコ")
st.subheader("〜もう、無駄打ちしない。広告を“武器”に変えるAIツール〜")

col1, col2 = st.columns([2, 1])

with col1:
    with st.container(border=True):
        st.subheader("📝 バナー情報入力フォーム")

        with st.expander("👤 基本情報", expanded=True):
            user_name = st.text_input("ユーザー名", key="user_name_input")
            age_group = st.selectbox(
                "ターゲット年代",
                ["指定なし", "10代", "20代", "30代", "40代", "50代", "60代以上"],
                key="age_group_select"
            )
            platform = st.selectbox("媒体", ["Instagram", "GDN", "YDN"], key="platform_select")
            category = st.selectbox("カテゴリ", ["広告", "投稿"] if platform == "Instagram" else ["広告"], key="category_select")
            has_ad_budget = st.selectbox("広告予算", ["あり", "なし"], key="budget_budget_select")
            
            purpose = st.selectbox(
                "目的",
                ["プロフィール誘導", "リンククリック", "保存数増加", "インプレッション増加"],
                key="purpose_select"
            )

        with st.expander("🎯 詳細設定", expanded=True):
            industry = st.selectbox("業種", ["美容", "飲食", "不動産", "子ども写真館", "その他"], key="industry_select")
            genre = st.selectbox("ジャンル", ["お客様の声", "商品紹介", "ノウハウ", "世界観", "キャンペーン"], key="genre_select")
            score_format = st.radio("スコア形式", ["A/B/C", "100点満点"], horizontal=True, key="score_format_radio")
            ab_pattern = st.radio("ABテストパターン", ["Aパターン", "Bパターン", "該当なし"], horizontal=True, key="ab_pattern_radio")
            banner_name = st.text_input("バナー名", key="banner_name_input")

        with st.expander("📌 任意項目", expanded=False):
            result_input = st.text_input("AI評価結果（任意）", help="AIが生成した評価結果を記録したい場合に入力します。", key="result_input_text")
            follower_gain_input = st.text_input("フォロワー増加数（任意）", help="Instagramなどのフォロワー増加数があれば入力します。", key="follower_gain_input_text")
            memo_input = st.text_area("メモ（任意）", help="その他、特記事項があれば入力してください。", key="memo_input_area")

        st.markdown("---")
        st.subheader("🖼️ バナー画像アップロードと診断")

        uploaded_file_a = st.file_uploader("Aパターン画像をアップロード", type=["png", "jpg", "jpeg"], key="a_upload")
        uploaded_file_b = st.file_uploader("Bパターン画像をアップロード", type=["png", "jpg", "jpeg"], key="b_upload")

        # Initialize session state for results
        if 'score_a' not in st.session_state: st.session_state.score_a = None
        if 'comment_a' not in st.session_state: st.session_state.comment_a = None
        if 'yakujihou_a' not in st.session_state: st.session_state.yakujihou_a = None
        if 'score_b' not in st.session_state: st.session_state.score_b = None
        if 'comment_b' not in st.session_state: st.session_state.comment_b = None
        if 'yakujihou_b' not in st.session_state: st.session_state.yakujihou_b = None

        # --- A Pattern Processing ---
        if uploaded_file_a:
            img_col_a, result_col_a = st.columns([1, 2])

            with img_col_a:
                st.image(Image.open(uploaded_file_a), caption="Aパターン画像", use_container_width=True)
                if st.button("🚀 Aパターンを採点", key="score_a_btn"):
                    if st.session_state.remaining_uses <= 0:
                        st.warning(f"残り回数がありません。（{st.session_state.plan}プラン）")
                        st.info("利用回数を増やすには、プランのアップグレードが必要です。")
                    else:
                        # ✅ 利用回数消費の呼び出しを auth_utils.update_user_uses_in_firestore_rest に変更
                        if auth_utils.update_user_uses_in_firestore_rest(st.session_state["user"], st.session_state["id_token"]): 
                            image_a = Image.open(uploaded_file_a)
                            buf_a = io.BytesIO()
                            image_a.save(buf_a, format="PNG")
                            img_str_a = base64.b64encode(buf_a.getvalue()).decode()

                            with st.spinner("AIがAパターンを採点中です..."):
                                try:
                                    ai_prompt_text = f"""
以下のバナー画像をプロ視点で採点してください。
この広告のターゲット年代は「{age_group}」で、主な目的は「{purpose}」です。

【評価基準】
1. 内容が一瞬で伝わるか
2. コピーの見やすさ
3. 行動喚起
4. 写真とテキストの整合性
5. 情報量のバランス

【ターゲット年代「{age_group}」と目的「{purpose}」を考慮した具体的なフィードバックをお願いします。】

【出力形式】
---
スコア：{score_format}
改善コメント：2～3行でお願いします
---"""
                                    response_a = client.chat.completions.create(
                                        model="gpt-4o",
                                        messages=[
                                            {"role": "system", "content": "あなたは広告のプロです。"},
                                            {"role": "user", "content": [
                                                {"type": "text", "text": ai_prompt_text},
                                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str_a}"}}
                                            ]}
                                        ],
                                        max_tokens=600
                                    )
                                    content_a = response_a.choices[0].message.content
                                    st.session_state.ai_response_a = content_a

                                    score_match_a = re.search(r"スコア[:：]\s*(.+)", content_a)
                                    comment_match_a = re.search(r"改善コメント[:：]\s*(.+)", content_a)
                                    st.session_state.score_a = score_match_a.group(1).strip() if score_match_a else "取得できず"
                                    st.session_state.comment_a = comment_match_a.group(1).strip() if comment_match_a else "取得できず"

                                    data_a = {
                                        "sheet_name": "record_log",
                                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "platform": sanitize(platform),
                                        "category": sanitize(category),
                                        "industry": sanitize(industry),
                                        "age_group": sanitize(age_group),
                                        "purpose": sanitize(purpose),
                                        "score": sanitize(st.session_state.score_a),
                                        "comment": sanitize(st.session_state.comment_a),
                                        "result": sanitize(result_input),
                                        "follower_gain": sanitize(follower_gain_input),
                                        "memo": sanitize(memo_input),
                                    }
                                    try:
                                        response_gas_a = requests.post(GAS_URL, json=data_a)
                                        if response_gas_a.status_code == 200:
                                            pass
                                        else:
                                            st.error(f"❌ スプレッドシート送信エラー（Aパターン）: ステータスコード {response_gas_a.status_code}, 応答: {response_gas_a.text}")
                                    except requests.exceptions.RequestException as e:
                                        st.error(f"GASへのデータ送信中にネットワークエラーが発生しました（Aパターン）: {str(e)}")
                                    except Exception as e:
                                        st.error(f"GASへのデータ送信中に予期せぬエラーが発生しました（Aパターン）: {str(e)}")

                                except Exception as e:
                                    st.error(f"AI採点中にエラーが発生しました（Aパターン）: {str(e)}")
                                    st.session_state.score_a = "エラー"
                                    st.session_state.comment_a = "AI応答エラー"
                        else:
                            st.error("利用回数の更新に失敗しました。")
                    st.success("Aパターンの診断が完了しました！")
            
            with result_col_a:
                if st.session_state.score_a:
                    st.markdown("### ✨ Aパターン診断結果")
                    st.metric("総合スコア", st.session_state.score_a)
                    st.info(f"**改善コメント:** {st.session_state.comment_a}")
                    
                    if industry in ["美容", "健康", "医療"]:
                        with st.spinner("⚖️ 薬機法チェックを実行中（Aパターン）..."):
                            yakujihou_prompt_a = f"""
以下の広告文（改善コメント）が薬機法に違反していないかをチェックしてください。
※これはバナー画像の内容に対するAIの改善コメントであり、実際の広告文ではありません。

---
{st.session_state.comment_a}
---

違反の可能性がある場合は、その理由も具体的に教えてください。
「OK」「注意あり」どちらかで評価を返してください。
"""
                            try:
                                yakujihou_response_a = client.chat.completions.create(
                                    model="gpt-4o",
                                    messages=[
                                        {"role": "system", "content": "あなたは広告表現の専門家です。"},
                                        {"role": "user", "content": yakujihou_prompt_a}
                                    ],
                                    max_tokens=500,
                                    temperature=0.3,
                                )
                                st.session_state.yakujihou_a = yakujihou_response_a.choices[0].message.content.strip() if yakujihou_response_a.choices else "薬機法チェックの結果を取得できませんでした。"
                                if "OK" in st.session_state.yakujihou_a:
                                    st.success(f"薬機法チェック：{st.session_state.yakujihou_a}")
                                else:
                                    st.warning(f"薬機法チェック：{st.session_state.yakujihou_a}")
                            except Exception as e:
                                st.error(f"薬機法チェック中にエラーが発生しました（Aパターン）: {str(e)}")
                                st.session_state.yakujihou_a = "エラー"

        st.markdown("---")

        # --- B Pattern Processing ---
        if uploaded_file_b:
            img_col_b, result_col_b = st.columns([1, 2])

            with img_col_b:
                st.image(Image.open(uploaded_file_b), caption="Bパターン画像", use_container_width=True)
                if st.button("🚀 Bパターンを採点", key="score_b_btn"):
                    if st.session_state.remaining_uses <= 0:
                        st.warning(f"残り回数がありません。（{st.session_state.plan}プラン）")
                        st.info("利用回数を増やすには、プランのアップグレードが必要です。")
                    else:
                        if auth_utils.update_user_uses_in_firestore(st.session_state["user"]): # ✅ update_user_uses_in_firestore_rest に修正
                            image_b = Image.open(uploaded_file_b)
                            buf_b = io.BytesIO()
                            image_b.save(buf_b, format="PNG")
                            img_str_b = base64.b64encode(buf_b.getvalue()).decode()

                            with st.spinner("AIがBパターンを採点中です..."):
                                try:
                                    ai_prompt_text = f"""
以下のバナー画像をプロ視点で採点してください。
この広告のターゲット年代は「{age_group}」で、主な目的は「{purpose}」です。

【評価基準】
1. 内容が一瞬で伝わるか
2. コピーの見やすさ
3. 行動喚起
4. 写真とテキストの整合性
5. 情報量のバランス

【ターゲット年代「{age_group}」と目的「{purpose}」を考慮した具体的なフィードバックをお願いします。】

【出力形式】
---
スコア：{score_format}
改善コメント：2～3行でお願いします
---"""
                                    response_b = client.chat.completions.create(
                                        model="gpt-4o",
                                        messages=[
                                            {"role": "system", "content": "あなたは広告のプロです。"},
                                            {"role": "user", "content": [
                                                {"type": "text", "text": ai_prompt_text},
                                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str_b}"}}
                                            ]}
                                        ],
                                        max_tokens=600
                                    )
                                    content_b = response_b.choices[0].message.content
                                    st.session_state.ai_response_b = content_b

                                    score_match_b = re.search(r"スコア[:：]\s*(.+)", content_b)
                                    comment_match_b = re.search(r"改善コメント[:：]\s*(.+)", content_b)
                                    st.session_state.score_b = score_match_b.group(1).strip() if score_match_b else "取得できず"
                                    st.session_state.comment_b = comment_match_b.group(1).strip() if comment_match_b else "取得できず"

                                    data_b = {
                                        "sheet_name": "record_log",
                                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "platform": sanitize(platform),
                                        "category": sanitize(category),
                                        "industry": sanitize(industry),
                                        "age_group": sanitize(age_group),
                                        "purpose": sanitize(purpose),
                                        "score": sanitize(st.session_state.score_b),
                                        "comment": sanitize(st.session_state.comment_b),
                                        "result": sanitize(result_input),
                                        "follower_gain": sanitize(follower_gain_input),
                                        "memo": sanitize(memo_input),
                                    }
                                    try:
                                        response_gas_b = requests.post(GAS_URL, json=data_b)
                                        if response_gas_b.status_code == 200:
                                            pass
                                        else:
                                            st.error(f"❌ スプレッドシート送信エラー（Bパターン）: ステータスコード {response_gas_b.status_code}, 応答: {response_gas_b.text}")
                                    except requests.exceptions.RequestException as e:
                                        st.error(f"GASへのデータ送信中にネットワークエラーが発生しました（Bパターン）: {str(e)}")
                                    except Exception as e:
                                        st.error(f"GASへのデータ送信中に予期せぬエラーが発生しました（Bパターン）: {str(e)}")

                                except Exception as e:
                                    st.error(f"AI採点中にエラーが発生しました（Bパターン）: {str(e)}")
                                    st.session_state.score_b = "エラー"
                                    st.session_state.comment_b = "AI応答エラー"
                        else:
                            st.error("利用回数の更新に失敗しました。")
                    st.success("Bパターンの診断が完了しました！")

            with result_col_b:
                if st.session_state.score_b:
                    st.markdown("### ✨ Bパターン診断結果")
                    st.metric("総合スコア", st.session_state.score_b)
                    st.info(f"**改善コメント:** {st.session_state.comment_b}")

                    if industry in ["美容", "健康", "医療"]:
                        with st.spinner("⚖️ 薬機法チェックを実行中（Bパターン）..."):
                            yakujihou_prompt_b = f"""
以下の広告文（改善コメント）が薬機法に違反していないかをチェックしてください。
※これはバナー画像の内容に対するAIの改善コメントであり、実際の広告文ではありません。

---
{st.session_state.comment_b}
---

違反の可能性がある場合は、その理由も具体的に教えてください。
「OK」「注意あり」どちらかで評価を返してください。
"""
                            try:
                                yakujihou_response_b = client.chat.completions.create(
                                    model="gpt-4o",
                                    messages=[
                                        {"role": "system", "content": "あなたは広告表現の専門家です。"},
                                        {"role": "user", "content": yakujihou_prompt_b}
                                    ],
                                    max_tokens=500,
                                    temperature=0.3,
                                )
                                st.session_state.yakujihou_b = yakujihou_response_b.choices[0].message.content.strip() if yakujihou_response_b.choices else "薬機法チェックの結果を取得できませんでした。"
                                if "OK" in st.session_state.yakujihou_b:
                                    st.success(f"薬機法チェック：{st.session_state.yakujihou_b}")
                                else:
                                    st.warning(f"薬機法チェック：{st.session_state.yakujihou_b}")
                            except Exception as e:
                                st.error(f"薬機法チェック中にエラーが発生しました（Bパターン）: {str(e)}")
                                st.session_state.yakujihou_b = "エラー"

        st.markdown("---")
        # AB Test Comparison Function (displayed if both scores are available)
        if st.session_state.score_a and st.session_state.score_b and \
           st.session_state.score_a != "エラー" and st.session_state.score_b != "エラー":
            if st.button("📊 A/Bテスト比較を実行", key="ab_compare_final_btn"):
                with st.spinner("AIがA/Bパターンを比較しています..."):
                    ab_compare_prompt = f"""
以下のAパターンとBパターンの広告診断結果を比較し、総合的にどちらが優れているか、その理由と具体的な改善点を提案してください。

---
Aパターン診断結果:
スコア: {st.session_state.score_a}
改善コメント: {st.session_state.comment_a}
薬機法チェック: {st.session_state.yakujihou_a}

Bパターン診断結果:
スコア: {st.session_state.score_b}
改善コメント: {st.session_state.comment_b}
薬機法チェック: {st.session_state.yakujihou_b}
---

【出力形式】
---
総合評価: Aパターンが優れている / Bパターンが優れている / どちらも改善が必要
理由: (2〜3行で簡潔に)
今後の改善提案: (具体的なアクションを1〜2点)
---
"""
                    try:
                        ab_compare_response = client.chat.completions.create(
                            model="gpt-4o", # A/B comparison also uses GPT-4o
                            messages=[
                                {"role": "system", "content": "あなたは広告のプロであり、A/Bテストのスペシャリストです。"},
                                {"role": "user", "content": ab_compare_prompt}
                            ],
                            max_tokens=700,
                            temperature=0.5,
                        )
                        ab_compare_content = ab_compare_response.choices[0].message.content.strip()
                        st.markdown("### 📈 A/Bテスト比較結果")
                        st.write(ab_compare_content)
                    except Exception as e:
                        st.error(f"A/Bテスト比較中にエラーが発生しました: {str(e)}")

with col2:
    with st.expander("📌 採点基準はこちら", expanded=True): # Expand by default
        st.markdown("バナスコAIは以下の観点に基づいて広告画像を評価します。")
        st.markdown(
            """
        - **1. 内容が一瞬で伝わるか**
            - 伝えたいことが最初の1秒でターゲットに伝わるか。
        - **2. コピーの見やすさ**
            - 文字が読みやすいか、サイズや配色が適切か。
        - **3. 行動喚起の明確さ**
            - 『今すぐ予約』『LINE登録』などの行動喚起が明確で、ユーザーを誘導できているか。
        - **4. 写真とテキストの整合性**
            - 背景画像と文字内容が一致し、全体として違和感がないか。
        - **5. 情報量のバランス**
            - 文字が多すぎず、視線誘導が自然で、情報が過負荷にならないか。
        """
        )

    st.markdown("---")
    st.info(
        "💡 **ヒント:** スコアやコメントは、広告改善のヒントとしてご活用ください。AIの提案は参考情報であり、最終的な判断は人間が行う必要があります。"
    )
