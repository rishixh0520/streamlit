import streamlit as st
import sqlite3
import hashlib
import datetime
import random
import time
import json
import base64
from typing import Optional
import plotly.express as px
import pandas as pd

# Configuration
DATABASE_NAME = "education_platform.db"

# Translations for English and Hindi
TRANSLATIONS = {
    'en': {
        'title': 'Rural Education Platform',
        'login': 'Login',
        'register': 'Register',
        'username': 'Username',
        'password': 'Password',
        'role': 'Role',
        'student': 'Student',
        'parent': 'Parent',
        'teacher': 'Teacher',
        'language': 'Language',
        'dashboard': 'Dashboard',
        'quizzes': 'Quizzes',
        'games': 'Games',
        'chat': 'Group Chat',
        'ai_assistant': 'AI Assistant',
        'progress': 'Progress',
        'video_call': 'Video Call',
        'logout': 'Logout',
        'points': 'Points',
        'level': 'Level',
        'daily_quiz': 'Daily Quiz',
        'take_quiz': 'Take Quiz',
        'submit': 'Submit',
        'correct': 'Correct!',
        'incorrect': 'Incorrect. Try again!',
        'motivational_quote': 'Remember: "Success is not final, failure is not fatal!"',
        'hydration_reminder': '💧 Time for a water break! Stay hydrated!',
        'eye_break_reminder': '👀 Take a 20-second break and look at something 20 feet away!',
        'archery_game': 'Archery Quiz Game',
        'shoot_answer': 'Shoot the correct answer!',
        'great_shot': 'Great shot! 🏹',
        'missed_target': 'Missed! Try again! 🎯',
        'chat_message': 'Type your message...',
        'send': 'Send',
        'ask_ai': 'Ask AI Assistant',
        'ai_placeholder': 'Ask me about any subject...',
        'welcome': 'Welcome'
    },
    'hi': {
        'title': 'ग्रामीण शिक्षा मंच',
        'login': 'लॉगिन',
        'register': 'पंजीकरण',
        'username': 'उपयोगकर्ता नाम',
        'password': 'पासवर्ड',
        'role': 'भूमिका',
        'student': 'छात्र',
        'parent': 'अभिभावक',
        'teacher': 'शिक्षक',
        'language': 'भाषा',
        'dashboard': 'डैशबोर्ड',
        'quizzes': 'क्विज़',
        'games': 'खेल',
        'chat': 'समूह चैट',
        'ai_assistant': 'AI सहायक',
        'progress': 'प्रगति',
        'video_call': 'वीडियो कॉल',
        'logout': 'लॉगआउट',
        'points': 'अंक',
        'level': 'स्तर',
        'daily_quiz': 'दैनिक क्विज़',
        'take_quiz': 'क्विज़ लें',
        'submit': 'जमा करें',
        'correct': 'सही!',
        'incorrect': 'गलत। फिर कोशिश करें!',
        'motivational_quote': 'याद रखें: "सफलता अंतिम नहीं है, असफलता घातक नहीं है!"',
        'hydration_reminder': '💧 पानी पीने का समय! हाइड्रेटेड रहें!',
        'eye_break_reminder': '👀 20 सेकंड का ब्रेक लें और 20 फीट दूर कुछ देखें!',
        'archery_game': 'तीरंदाजी क्विज़ गेम',
        'shoot_answer': 'सही उत्तर को निशाना बनाएं!',
        'great_shot': 'शानदार शॉट! 🏹',
        'missed_target': 'चूक गए! फिर कोशिश करें! 🎯',
        'chat_message': 'अपना संदेश लिखें...',
        'send': 'भेजें',
        'ask_ai': 'AI सहायक से पूछें',
        'ai_placeholder': 'किसी भी विषय के बारे में पूछें...',
        'welcome': 'स्वागत'
    }
}

class DatabaseManager:
    def __init__(self):
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT,
                parent_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                points INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                badges TEXT,
                total_quizzes INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                question TEXT,
                options TEXT,
                correct_answer TEXT,
                type TEXT DEFAULT 'mcq',
                difficulty TEXT DEFAULT 'easy'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_id INTEGER,
                user_answer TEXT,
                is_correct BOOLEAN,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (question_id) REFERENCES quiz_questions (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
        conn.close()

    def create_user(self, username: str, password: str, role: str, parent_id: Optional[int] = None):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            cursor.execute('''
                INSERT INTO users (username, password, role, parent_id)
                VALUES (?, ?, ?, ?)
            ''', (username, hashed_password, role, parent_id))
            user_id = cursor.lastrowid
            cursor.execute('''
                INSERT INTO user_progress (user_id, points, level, badges)
                VALUES (?, 0, 1, '[]')
            ''', (user_id,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def authenticate_user(self, username: str, password: str):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('''
            SELECT id, username, role FROM users
            WHERE username = ? AND password = ?
        ''', (username, hashed_password))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"id": result[0], "username": result[1], "role": result[2]}
        return None

    def get_user_progress(self, user_id: int):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT points, level, badges, total_quizzes, correct_answers
            FROM user_progress WHERE user_id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "points": row[0],
                "level": row[1],
                "badges": json.loads(row[2]) if row[2] else [],
                "total_quizzes": row[3],
                "correct_answers": row[4]
            }
        return {"points": 0, "level": 1, "badges": [], "total_quizzes": 0, "correct_answers": 0}

    def update_progress(self, user_id: int, points: int, correct: bool):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_progress
            SET points = points + ?, total_quizzes = total_quizzes + 1,
                correct_answers = correct_answers + ?
            WHERE user_id = ?
        ''', (points, 1 if correct else 0, user_id))
        cursor.execute('SELECT points FROM user_progress WHERE user_id = ?', (user_id,))
        new_points = cursor.fetchone()[0]
        new_level = (new_points // 100) + 1
        cursor.execute('UPDATE user_progress SET level = ? WHERE user_id = ?', (new_level, user_id))
        conn.commit()
        conn.close()

    def get_random_quiz_question(self):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0], "subject": row[1], "question": row[2],
                "options": json.loads(row[3]), "correct_answer": row[4],
                "type": row[5], "difficulty": row[6]
            }
        return None

    def save_chat_message(self, user_id: int, username: str, message: str):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_messages (user_id, username, message)
            VALUES (?, ?, ?)
        ''', (user_id, username, message))
        conn.commit()
        conn.close()

    def get_chat_messages(self, limit: int = 50):
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, message, timestamp
            FROM chat_messages
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{"username": r[0], "message": r[1], "timestamp": r[2]} for r in reversed(rows)]

# Initialize database manager
db = DatabaseManager()

def get_text(key: str, lang: str):
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

def show_login_page():
    lang = st.session_state.get('language', 'en')
    st.title(get_text('title', lang))
    st.session_state.language = st.selectbox(get_text('language', lang),
                                             ['en', 'hi'],
                                             format_func=lambda x: 'English' if x=='en' else 'हिंदी')
    tab1, tab2 = st.tabs([get_text('login', lang), get_text('register', lang)])
    with tab1:
        with st.form("login_form"):
            u = st.text_input(get_text('username', lang))
            p = st.text_input(get_text('password', lang), type='password')
            if st.form_submit_button(get_text('login', lang)):
                user = db.authenticate_user(u, p)
                if user:
                    st.session_state.user = user
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials!")
    with tab2:
        with st.form("register_form"):
            u = st.text_input(get_text('username', lang))
            p = st.text_input(get_text('password', lang), type='password')
            r = st.selectbox(get_text('role', lang),
                             ['student','parent','teacher'],
                             format_func=lambda x: get_text(x, lang))
            if st.form_submit_button(get_text('register', lang)):
                if db.create_user(u, p, r):
                    st.success("Account created! Please login.")
                else:
                    st.error("Username already exists.")

def show_dashboard():
    lang = st.session_state.get('language','en')
    user = st.session_state.user
    col1, col2 = st.columns([3,1])
    with col1:
        st.title(f"{get_text('welcome', lang)}, {user['username']}!")
    with col2:
        if st.button(get_text('logout', lang)):
            st.session_state.clear()
            st.rerun()

    # Health reminders every 10 minutes
    if 'last_reminder' not in st.session_state:
        st.session_state.last_reminder = time.time()
    if time.time() - st.session_state.last_reminder > 600:
        st.info(random.choice([get_text('hydration_reminder', lang),
                                get_text('eye_break_reminder', lang)]))
        st.session_state.last_reminder = time.time()

    if user['role']=='student':
        show_student_dashboard(lang)
    elif user['role']=='parent':
        show_parent_dashboard(lang)
    else:
        show_teacher_dashboard(lang)

def show_student_dashboard(lang):
    user = st.session_state.user
    prog = db.get_user_progress(user['id'])
    c1,c2,c3 = st.columns(3)
    c1.metric(get_text('points', lang), prog['points'])
    c2.metric(get_text('level', lang), prog['level'])
    accuracy = (prog['correct_answers']/prog['total_quizzes']*100) if prog['total_quizzes']>0 else 0
    c3.metric("Accuracy", f"{accuracy:.1f}%")

    tabs = st.tabs([get_text('quizzes',lang),get_text('games',lang),
                    get_text('chat',lang),get_text('ai_assistant',lang),
                    get_text('video_call',lang)])
    with tabs[0]: show_quiz_section(lang)
    with tabs[1]: show_games_section(lang)
    with tabs[2]: show_chat_section(lang)
    with tabs[3]: show_ai_assistant(lang)
    with tabs[4]: show_video_call_section(lang)

def show_quiz_section(lang):
    st.subheader(get_text('daily_quiz',lang))
    if st.button(get_text('take_quiz',lang)):
        st.session_state.current_q = db.get_random_quiz_question()
    if 'current_q' in st.session_state:
        q=st.session_state.current_q
        st.write(f"**Subject:** {q['subject']}")
        st.write(f"**Question:** {q['question']}")
        ans = st.radio("Choose your answer:", q['options'])
        if st.button(get_text('submit',lang)):
            correct = ans==q['correct_answer']
            if correct:
                st.success(get_text('correct',lang))
                st.balloons()
                pts=10
            else:
                st.error(get_text('incorrect',lang))
                st.info(get_text('motivational_quote',lang))
                pts=2
            db.update_progress(st.session_state.user['id'], pts, correct)
            del st.session_state.current_q
            st.rerun()

def show_games_section(lang):
    st.subheader(get_text('games',lang))
    if st.selectbox("Select Game:", [get_text('archery_game',lang)])==get_text('archery_game',lang):
        show_archery_game(lang)

def show_archery_game(lang):
    st.write(get_text('shoot_answer',lang))
    if 'archery_q' not in st.session_state:
        st.session_state.archery_q = db.get_random_quiz_question()
    q = st.session_state.archery_q
    st.write(f"🏹 **{q['question']}**")
    cols = st.columns(len(q['options']))
    for i, opt in enumerate(q['options']):
        with cols[i]:
            if st.button(opt, key=i):
                correct = opt==q['correct_answer']
                if correct:
                    st.success(get_text('great_shot',lang)); st.balloons(); pts=15
                else:
                    st.error(get_text('missed_target',lang)); pts=3
                db.update_progress(st.session_state.user['id'], pts, correct)
                del st.session_state.archery_q
                st.rerun()

def show_chat_section(lang):
    st.subheader(get_text('chat',lang))
    for m in db.get_chat_messages():
        st.write(f"**{m['username']}**: {m['message']}")
    with st.form("chat"):
        msg=st.text_input(get_text('chat_message',lang))
        if st.form_submit_button(get_text('send',lang)) and msg:
            db.save_chat_message(st.session_state.user['id'],
                                 st.session_state.user['username'], msg)
            st.rerun()

def show_ai_assistant(lang):
    st.subheader(get_text('ai_assistant',lang))
    faqs={
        'math':"Practice multiplication tables daily!",
        'science':"Plants make food via photosynthesis.",
        'english':"Read 15 mins daily for vocabulary.",
        'hindi':"रोज़ हिंदी कविताएँ पढ़ें।",
        'history':"Use timelines for key dates.",
        'geography':"Use maps to learn capitals."
    }
    q=st.text_input(get_text('ai_placeholder',lang))
    if st.button(get_text('ask_ai',lang)):
        resp="I'm here to help! Ask about Math, Science, English, Hindi, History, or Geography."
        for k,v in faqs.items():
            if k in q.lower(): resp=v; break
        st.write(resp)

def show_video_call_section(lang):
    st.subheader(get_text('video_call',lang))
    room=st.text_input("Room Name:", value=f"class_{st.session_state.user['username']}")
    if st.button("Join Video Call") and room:
        url=f"https://meet.jit.si/{room}"
        st.markdown(f'<iframe src="{url}" width="100%" height="600"></iframe>', unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Rural Education Platform", page_icon="📚", layout="wide")
    if 'logged_in' not in st.session_state: st.session_state.logged_in=False
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_dashboard()

if __name__=="__main__":
    main()
