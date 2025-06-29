-----

承知いたしました。ご提示いただいたコードを、ご要望に基づき、Streamlit UIの改善（入力フォームのセクション化、画像アップロード・処理・結果表示の明確化）を施した上で、全文を以下に示します。

```python
import streamlit as st
import base64
import io
import os
import re
import requests
from PIL import Image
from datetime import datetime
from openai import OpenAI
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# OpenAI APIキーの読み込み
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("❌ OpenAI APIキーが見つかりませんでした。`.env` を確認してください。")
    st.stop()
client = OpenAI(api_key=openai_api_key)

# GASとGoogle Driveの情報
GAS_URL = "https://script.google.com/macros/s/AKfycbzQadO4iuzhETiiDZb2ZQ7et_Rgjb_kR7OIUyL0mK2wqU2-FB2UeN4FVtdyK3Xod3Tm/exec"
FOLDER_ID = "1oRyCu2sU9idRrj5tq5foQX3ArtCW7rP" # FOLDER_IDを修正しました。

def upload_image_to_drive_get_url(pil_image, filename):
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("credentials.json")
    try:
        if gauth.credentials is None:
            gauth.CommandLineAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()
    except Exception as e:
        # Streamlit環境での認証に関する注意点をユーザーに伝える
        st.error(f"Google Drive認証エラー: {str(e)}。Streamlit Cloudのような環境では、サービスアカウントやOAuth2.0の利用を検討してください。")
        gauth.CommandLineAuth() # ローカルテスト用
    gauth.SaveCredentialsFile("credentials.json")

    drive = GoogleDrive(gauth)
    temp_path = f"/tmp/{filename}"
    pil_image.save(temp_path, format="PNG")
    file_drive = drive.CreateFile({
        'title': filename,
        'mimeType': 'image/png',
        'parents': [{'id': FOLDER_ID}]
    })
    file_drive.SetContentFile(temp_path)
    file_drive.Upload()
    file_drive.InsertPermission({'type': 'anyone', 'role': 'reader'})
    return f"https://drive.google.com/uc?export=view&id={file_drive['id']}"

# Streamlit UI設定
st.set_page_config(layout="wide", page_title="バナスコAI")
st.title("🧠 バナー広告 採点AI - バナスコ")
st.subheader("〜もう、無駄打ちしない。広告を“武器”に変えるAIツール〜")

col1, col2 = st.columns([2, 1])

with col1:
    with st.container(border=True):
        st.subheader("📝 バナー情報入力フォーム")

        with st.expander("👤 基本情報", expanded=True):
            user_name = st.text_input("ユーザー名", key="user_name_input")
            platform = st.selectbox("媒体", ["Instagram", "GDN", "YDN"], key="platform_select")
            category = st.selectbox("カテゴリ", ["広告", "投稿"] if platform == "Instagram" else ["広告"], key="category_select")
            has_ad_budget = st.selectbox("広告予算", ["あり", "なし"], key="budget_select")
            purpose = st.selectbox("目的", ["プロフィール誘導", "リンククリック", "保存数増加"], key="purpose_select")

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

        # 結果をセッションステートで保持するための初期化
        if 'score_a' not in st.session_state: st.session_state.score_a = None
        if 'comment_a' not in st.session_state: st.session_state.comment_a = None
        if 'yakujihou_a' not in st.session_state: st.session_state.yakujihou_a = None
        if 'score_b' not in st.session_state: st.session_state.score_b = None
        if 'comment_b' not in st.session_state: st.session_state.comment_b = None
        if 'yakujihou_b' not in st.session_state: st.session_state.yakujihou_b = None

        # --- Aパターン処理 ---
        if uploaded_file_a:
            st.image(Image.open(uploaded_file_a), caption="Aパターン画像", use_container_width=True)
            if st.button("🚀 Aパターンを採点＋保存", key="score_save_a_btn"):
                image_a = Image.open(uploaded_file_a)
                buf_a = io.BytesIO()
                image_a.save(buf_a, format="PNG")
                img_str_a = base64.b64encode(buf_a.getvalue()).decode()

                with st.spinner("AIがAパターンを採点中です..."):
                    try:
                        response_a = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "あなたは広告のプロです。"},
                                {"role": "user", "content": [
                                    {"type": "text", "text":
                                        f"以下のバナー画像をプロ視点で採点してください。\n\n【評価基準】\n1. 内容が一瞬で伝わるか\n2. コピーの見やすさ\n3. 行動喚起\n4. 写真とテキストの整合性\n5. 情報量のバランス\n\n【出力形式】\n---\nスコア：{score_format}\n改善コメント：2～3行でお願いします\n---"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str_a}"}}
                                ]}
                            ],
                            max_tokens=600
                        )
                        content_a = response_a.choices[0].message.content
                        st.session_state.ai_response_a = content_a # AIの生レスポンスも保存

                        score_match_a = re.search(r"スコア[:：]\s*(.+)", content_a)
                        comment_match_a = re.search(r"改善コメント[:：]\s*(.+)", content_a)
                        st.session_state.score_a = score_match_a.group(1).strip() if score_match_a else "取得できず"
                        st.session_state.comment_a = comment_match_a.group(1).strip() if comment_match_a else "取得できず"
                    except Exception as e:
                        st.error(f"AI採点中にエラーが発生しました（Aパターン）: {str(e)}")
                        st.session_state.score_a = "エラー"
                        st.session_state.comment_a = "AI応答エラー"

                st.success("Aパターンの診断が完了しました！")
                st.markdown("### ✨ Aパターン診断結果")
                col_a_score, col_a_comment = st.columns([1, 2])
                with col_a_score:
                    st.metric("総合スコア", st.session_state.score_a)
                with col_a_comment:
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
                                    {"role": "system", "content": "あなたは広告表現の薬機法チェックを行う専門家です。"},
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

                data_a = {
                    "sheet_name": "record_log",
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "platform": platform,
                    "category": category,
                    "industry": industry,
                    "score": st.session_state.score_a,
                    "comment": st.session_state.comment_a,
                    "result": result_input,
                    "follower_gain": follower_gain_input,
                    "memo": memo_input,
                }
                
                try:
                    # Google Driveへのアップロードはここで実行
                    if uploaded_file_a:
                        image_a_pil = Image.open(uploaded_file_a)
                        image_filename_a = f"Banasuko_A_Pattern_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                        google_drive_url_a = upload_image_to_drive_get_url(image_a_pil, image_filename_a)
                        data_a["image_url"] = google_drive_url_a # スプレッドシートにURLを追加
                        st.success(f"Google Driveに画像をアップロードしました: [リンク]({google_drive_url_a})")
                except Exception as e:
                    st.error(f"Google Driveへの画像アップロード中にエラーが発生しました（Aパターン）: {str(e)}")
                    data_a["image_url"] = "アップロード失敗"

                st.write("🖋 送信データ（Aパターン）:", data_a)
                try:
                    response_gas_a = requests.post(GAS_URL, json=data_a)
                    if response_gas_a.status_code == 200:
                        st.success("📊 スプレッドシートに記録しました！（Aパターン）")
                    else:
                        st.error(f"❌ スプレッドシート送信エラー（Aパターン）: {response_gas_a.status_code} - {response_gas_a.text}")
                except Exception as e:
                    st.error(f"GASへのデータ送信中にエラーが発生しました（Aパターン）: {str(e)}")
        
        st.markdown("---")

        # --- Bパターン処理 ---
        if uploaded_file_b:
            st.image(Image.open(uploaded_file_b), caption="Bパターン画像", use_container_width=True)
            if st.button("🚀 Bパターンを採点＋保存", key="score_save_b_btn"):
                image_b = Image.open(uploaded_file_b)
                buf_b = io.BytesIO()
                image_b.save(buf_b, format="PNG")
                img_str_b = base64.b64encode(buf_b.getvalue()).decode()

                with st.spinner("AIがBパターンを採点中です..."):
                    try:
                        response_b = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "あなたは広告のプロです。"},
                                {"role": "user", "content": [
                                    {"type": "text", "text":
                                        f"以下のバナー画像をプロ視点で採点してください。\n\n【評価基準】\n1. 内容が一瞬で伝わるか\n2. コピーの見やすさ\n3. 行動喚起\n4. 写真とテキストの整合性\n5. 情報量のバランス\n\n【出力形式】\n---\nスコア：{score_format}\n改善コメント：2～3行でお願いします\n---"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str_b}"}}
                                ]}
                            ],
                            max_tokens=600
                        )
                        content_b = response_b.choices[0].message.content
                        st.session_state.ai_response_b = content_b # AIの生レスポンスも保存

                        score_match_b = re.search(r"スコア[:：]\s*(.+)", content_b)
                        comment_match_b = re.search(r"改善コメント[:：]\s*(.+)", content_b)
                        st.session_state.score_b = score_match_b.group(1).strip() if score_match_b else "取得できず"
                        st.session_state.comment_b = comment_match_b.group(1).strip() if comment_match_b else "取得できず"
                    except Exception as e:
                        st.error(f"AI採点中にエラーが発生しました（Bパターン）: {str(e)}")
                        st.session_state.score_b = "エラー"
                        st.session_state.comment_b = "AI応答エラー"
                
                st.success("Bパターンの診断が完了しました！")
                st.markdown("### ✨ Bパターン診断結果")
                col_b_score, col_b_comment = st.columns([1, 2])
                with col_b_score:
                    st.metric("総合スコア", st.session_state.score_b)
                with col_b_comment:
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
                                    {"role": "system", "content": "あなたは広告表現の薬機法チェックを行う専門家です。"},
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

                data_b = {
                    "sheet_name": "record_log",
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "platform": platform,
                    "category": category,
                    "industry": industry,
                    "score": st.session_state.score_b,
                    "comment": st.session_state.comment_b,
                    "result": result_input,
                    "follower_gain": follower_gain_input,
                    "memo": memo_input,
                }
                
                try:
                    # Google Driveへのアップロードはここで実行
                    if uploaded_file_b:
                        image_b_pil = Image.open(uploaded_file_b)
                        image_filename_b = f"Banasuko_B_Pattern_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                        google_drive_url_b = upload_image_to_drive_get_url(image_b_pil, image_filename_b)
                        data_b["image_url"] = google_drive_url_b # スプレッドシートにURLを追加
                        st.success(f"Google Driveに画像をアップロードしました: [リンク]({google_drive_url_b})")
                except Exception as e:
                    st.error(f"Google Driveへの画像アップロード中にエラーが発生しました（Bパターン）: {str(e)}")
                    data_b["image_url"] = "アップロード失敗"

                st.write("🖋 送信データ（Bパターン）:", data_b)
                try:
                    response_gas_b = requests.post(GAS_URL, json=data_b)
                    if response_gas_b.status_code == 200:
                        st.success("📊 スプレッドシートに記録しました！（Bパターン）")
                    else:
                        st.error(f"❌ スプレッドシート送信エラー（Bパターン）: {response_gas_b.status_code} - {response_gas_b.text}")
                except Exception as e:
                    st.error(f"GASへのデータ送信中にエラーが発生しました（Bパターン）: {str(e)}")

        st.markdown("---")
        # ABテスト比較機能（両方の診断が完了したら表示）
        if st.session_state.score_a and st.session_state.score_b:
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
                            model="gpt-4o", # A/B比較もGPT-4oで実行
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
    with st.expander("📌 採点基準はこちら", expanded=True): # デフォルトで開くように変更
        st.markdown("バナスコAIは以下の観点に基づいて広告画像を評価します。")
        st.markdown("""
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
        """)
    
    st.markdown("---")
    st.info("💡 **ヒント:** スコアやコメントは、広告改善のヒントとしてご活用ください。AIの提案は参考情報であり、最終的な判断は人間が行う必要があります。")
```
