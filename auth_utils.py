# auth_utils.py
import streamlit as st
import os
import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime # Firestore REST APIでタイムスタンプを扱うために追加


# .envファイルから環境変数を読み込む
load_dotenv()

# Firebase Authentication REST APIに必要なAPIキーを取得
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

if not FIREBASE_API_KEY:
    st.error("Firebase APIキーが.envファイルに見つかりません。")
    st.stop()

# Firebase Authentication REST APIのエンドポイントベースURL
FIREBASE_AUTH_BASE_URL = "https://identitytoolkit.googleapis.com/v1/accounts:"

# --- Firebase Admin SDKの初期化 (Firestore用) ---
try:
    if "firebase_admin_initialized" not in st.session_state:
        admin_project_id = os.getenv("FIREBASE_PROJECT_ID_ADMIN")
        admin_private_key = os.getenv("FIREBASE_PRIVATE_KEY_ADMIN")
        admin_client_email = os.getenv("FIREBASE_CLIENT_EMAIL_ADMIN")

        if not admin_project_id or not admin_private_key or not admin_client_email:
            st.error("Firebase Admin SDKの環境変数（PROJECT_ID_ADMIN, PRIVATE_KEY_ADMIN, CLIENT_EMAIL_ADMIN）が不足しています。Secretsを確認してください。")
            st.stop()

        service_account_info = {
            "type": "service_account",
            "project_id": admin_project_id,
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID_ADMIN"),
            "private_key": admin_private_key,
            "client_email": admin_client_email,
            "client_id": os.getenv("FIREBASE_CLIENT_ID_ADMIN"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{admin_client_email.replace('@', '%40')}",
            "universe_domain": "googleapis.com"
        }
        
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
        st.session_state.firebase_admin_initialized = True
        db = firestore.client()
except Exception as e:
    st.error(f"Firebase Admin SDKの初期化に失敗しました。サービスアカウントキーを確認してください: {e}")
    st.error(f"エラー詳細: {e}")
    st.stop()


# Streamlitのセッションステートを初期化 (初回ロード時のみ)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "email" not in st.session_state:
    st.session_state.email = None
if "plan" not in st.session_state:
    st.session_state.plan = "Guest"
if "remaining_uses" not in st.session_state:
    st.session_state.remaining_uses = 0


# --- Firebase Authentication REST APIの関数 ---
def sign_in_with_email_and_password(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def create_user_with_email_and_password(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


# --- Firestoreの操作関数 (Admin SDKを使用) ---
def get_user_data_from_firestore(uid):
    """Firestoreからユーザーのプランと利用回数を取得する"""
    global db 
    doc_ref = db.collection('users').document(uid)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        st.session_state.plan = data.get("plan", "Free")
        st.session_state.remaining_uses = data.get("remaining_uses", 0)
    else:
        st.session_state.plan = "Free"
        st.session_state.remaining_uses = 5 
        doc_ref.set({
            "email": st.session_state.email,
            "plan": st.session_state.plan,
            "remaining_uses": st.session_state.remaining_uses,
            "created_at": firestore.SERVER_TIMESTAMP
        })
    st.sidebar.write(f"残り回数: {st.session_state.remaining_uses}回 ({st.session_state.plan}プラン)")


def update_user_uses_in_firestore(uid, uses_to_deduct=1):
    """Firestoreのユーザー利用回数を減らす"""
    global db
    doc_ref = db.collection('users').document(uid)
    try:
        doc_ref.update({
            "remaining_uses": firestore.Increment(-uses_to_deduct),
            "last_used_at": firestore.SERVER_TIMESTAMP
        })
        st.session_state.remaining_uses -= uses_to_deduct
        st.sidebar.write(f"残り回数: {st.session_state.remaining_uses}回 ({st.session_state.plan}プラン)")
        return True
    except Exception as e:
        st.error(f"利用回数の更新に失敗しました: {e}")
        return False


# --- StreamlitのUI表示と認証フロー ---
def login_page():
    """Streamlit上にログイン画面を表示する関数"""
    st.title("🔐 バナスコAI ログイン")
    st.markdown("アカウント情報入力フォームの機能を利用するにはログインが必要です。")

    email = st.text_input("メールアドレス", key="login_email")
    password = st.text_input("パスワード", type="password", key="login_password")

    login_col, create_col = st.columns(2)

    with login_col:
        if st.button("ログイン", key="login_button"):
            with st.spinner("ログイン中..."):
                try:
                    user_info = sign_in_with_email_and_password(email, password)
                    st.session_state["user"] = user_info["localId"]
                    st.session_state["email"] = user_info["email"]
                    st.session_state["logged_in"] = True
                    
                    get_user_data_from_firestore(st.session_state["user"])

                    st.success(f"ログインしました: {user_info['email']}")
                    st.rerun()
                except requests.exceptions.HTTPError as e:
                    error_json = e.response.json()
                    error_code = error_json.get("error", {}).get("message", "Unknown error")
                    if error_code == "EMAIL_NOT_FOUND" or error_code == "INVALID_PASSWORD":
                        st.error("ログインに失敗しました。メールアドレスまたはパスワードが間違っています。")
                    elif error_code == "USER_DISABLED":
                        st.error("このアカウントは無効化されています。")
                    else:
                        st.error(f"ログイン中にエラーが発生しました: {error_code}")
                except Exception as e:
                    st.error(f"予期せぬエラーが発生しました: {e}")

    with create_col:
        if st.button("アカウント作成", key="create_account_button"):
            with st.spinner("アカウント作成中..."):
                try:
                    user_info = create_user_with_email_and_password(email, password)
                    st.success(f"アカウント '{user_info['email']}' を作成しました。ログインしてください。")
                except requests.exceptions.HTTPError as e:
                    error_json = e.response.json()
                    error_code = error_json.get("error", {}).get("message", "Unknown error")
                    if error_code == "EMAIL_EXISTS":
                        st.error("このメールアドレスは既に使用されています。")
                    elif error_code == "WEAK_PASSWORD":
                        st.error("パスワードが弱すぎます（6文字以上必要）。")
                    else:
                        st.error(f"アカウント作成中にエラーが発生しました: {error_code}")
                except Exception as e:
                    st.error(f"予期せぬエラーが発生しました: {e}")

def logout():
    """ユーザーをログアウトさせる関数"""
    if st.session_state.get("logged_in"):
        keys_to_clear = ["user", "email", "logged_in", "plan", "remaining_uses",
                         "score_a", "comment_a", "yakujihou_a", "score_b", "comment_b", "yakujihou_b",
                         "ai_response_a", "ai_response_b"]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.success("ログアウトしました。")
        st.rerun()

def check_login():
    """
    ユーザーのログイン状態をチェックし、未ログインならログインページを表示してアプリの実行を停止する。
    Firestoreの残り回数も確認し、サイドバーに表示する。
    """
    if not st.session_state.get("firebase_admin_initialized"):
        st.stop() 

    if st.session_state.get("logged_in"):
        st.sidebar.write(f"ようこそ, {st.session_state.get('email')}!")
        
        if "remaining_uses" not in st.session_state or st.session_state.remaining_uses is None:
            get_user_data_from_firestore(st.session_state["user"])
        
        st.sidebar.write(f"残り回数: {st.session_state.remaining_uses}回 ({st.session_state.plan}プラン)")
        st.sidebar.button("ログアウト", on_click=logout)

    if not st.session_state.get("logged_in"):
        login_page()
        st.stop()
