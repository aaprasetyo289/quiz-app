import streamlit as st
import pandas as pd
import random
import time
from google.cloud import firestore
from streamlit_local_storage import LocalStorage
from googletrans import Translator
from functools import lru_cache
import traceback
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow nested event loops in Streamlit
nest_asyncio.apply()

# --- CONSTANTS ---
# Save code generation
SAVE_CODE_WORDS = ["APPLE", "BEAR", "CANDY", "DREAM", "EAGLE", "FROG", "GIANT", "HONEY", "IRIS", "JADE"]

# CSV column names
CSV_QUESTION_COL = 'Pertanyaan'
CSV_OPTIONS_COL = 'Pilihan Ganda'
CSV_ANSWER_COL = 'Jawaban'

# Grade thresholds and messages
GRADE_THRESHOLDS = {
    100.0: ("A", "Perfect score, congratulations! Kamu dapat nilai **A**"),
    80: ("A", "Selamat, kamu dapat nilai **A**!"),
    75: ("AB", "Selamat, kamu dapat nilai **AB**!"),
    70: ("B", "Selamat, kamu dapat nilai **B**!"),
    65: ("BC", "Kamu dapat nilai **BC**."),
    55: ("C", "Kamu dapat nilai **C**. Better luck next time!"),
    45: ("D", "Kamu dapat nilai **D**. Better luck next time!"),
    0: ("E", "Kamu dapat nilai **E**. Don't worry, keep practicing and you'll get there!")
}

# Session state keys to save
STATE_KEYS_TO_SAVE = [
    'session_id', 'selected_subject', 'questions', 'original_questions', 'translated_questions_cache',
    'current_question_index', 'score', 'auto_next',
    'answer_submitted', 'last_choice', 'scored', 'timer_enabled',
    'show_timer', 'time_elapsed_before_pause', 'answer_history', 'language', 'previous_language',
    'user_name'  # Added to persist user name
]

# --- TRANSLATION CONSTANTS ---
DEFAULT_LANGUAGE = "id"  # Indonesian as default (source language)

AVAILABLE_LANGUAGES = {
    "id": "🇮🇩 Bahasa Indonesia (Original)",
    "en": "🇬🇧 English",
    "es": "🇪🇸 Español",
    "fr": "🇫🇷 Français",
    "de": "🇩🇪 Deutsch",
    "zh-cn": "🇨🇳 简体中文",
    "ja": "🇯🇵 日本語",
    "ko": "🇰🇷 한국어",
    "ar": "🇸🇦 العربية",
    "pt": "🇵🇹 Português",
}

# --- Initialise Local Storage ---
localS = LocalStorage()

# --- TRANSLATION FUNCTIONS (ASYNC OPTIMIZED) ---
@st.cache_resource
def get_translator():
    """Initialize and cache the Google Translator instance."""
    return Translator()

async def translate_text_async(translator, text, src_lang, dest_lang):
    """Async function to translate a single text."""
    try:
        result = await translator.translate(text, src=src_lang, dest=dest_lang)
        return result.text if result and hasattr(result, 'text') and result.text else text
    except Exception:
        # Return original text on error
        return text

async def translate_batch_async(translator, texts, src_lang, dest_lang):
    """Async function to translate multiple texts concurrently."""
    # Create tasks for all translations
    tasks = [translate_text_async(translator, text, src_lang, dest_lang) for text in texts]
    
    # Execute all translations concurrently
    results = await asyncio.gather(*tasks)
    return results

def translate_questions_smart(questions, target_lang):
    """
    Translates questions ONLY if target language is different from Indonesian.
    Uses async batch translation for maximum efficiency.
    Returns original questions if target is Indonesian.
    """
    if target_lang == "id":
        return questions
    
    # Check if we already have this translation cached
    cache_key = f"translated_{target_lang}"
    if cache_key in st.session_state.get('translated_questions_cache', {}):
        return st.session_state.translated_questions_cache[cache_key]
    
    try:
        translator = get_translator()
        
        # Collect all texts to translate
        all_texts = []
        for q in questions:
            all_texts.append(q['question'])
            all_texts.extend(q['options'])
        
        # Async batch translate with retry logic
        with st.spinner(f"🔄 Translating {len(questions)} questions to {AVAILABLE_LANGUAGES[target_lang]}..."):
            max_retries = 3
            translated_texts = None
            
            for attempt in range(max_retries):
                try:
                    # Run async translation
                    translated_texts = asyncio.run(translate_batch_async(
                        translator, all_texts, 'id', target_lang
                    ))
                    
                    # Verify we got all results
                    if translated_texts and len(translated_texts) == len(all_texts):
                        # Check if any translations failed (returned original text)
                        success_count = sum(1 for orig, trans in zip(all_texts, translated_texts) if orig != trans)
                        
                        if success_count > 0:
                            # At least some translations succeeded
                            break
                        else:
                            # All translations returned original text (likely API issue)
                            raise ValueError("No texts were translated")
                    else:
                        raise ValueError("Incomplete translation results")
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        st.warning(f"⚠️ Translation attempt {attempt + 1} failed: {str(e)[:100]}. Retrying...")
                        time.sleep(1)
                        # Get a fresh translator instance from cache
                        translator = get_translator()
                    else:
                        st.error(f"❌ Translation failed after {max_retries} attempts: {str(e)[:100]}")
                        st.info("💡 Tip: The Google Translate API can be unstable. Try refreshing or wait a moment.")
                        return questions
            
            if not translated_texts or len(translated_texts) != len(all_texts):
                st.error("❌ Translation failed. Using Indonesian.")
                return questions
        
        # Reconstruct questions
        translated_questions = []
        idx = 0
        for q in questions:
            num_options = len(q['options'])
            translated_q = {
                'question': translated_texts[idx],
                'options': translated_texts[idx+1:idx+1+num_options],
                'answer': q['answer']  # Keep answer letter same
            }
            translated_questions.append(translated_q)
            idx += 1 + num_options
        
        # Cache the translation
        if 'translated_questions_cache' not in st.session_state:
            st.session_state.translated_questions_cache = {}
        st.session_state.translated_questions_cache[cache_key] = translated_questions
        
        st.success(f"✅ Successfully translated {len(questions)} questions!")
        
        return translated_questions
        
    except Exception as e:
        st.error(f"❌ Translation error: {e}")
        st.error(f"Full traceback:\n{traceback.format_exc()}")
        st.info("💡 Tip: Try selecting a different language or refresh the page.")
        return questions

def update_questions_for_language():
    """
    Updates displayed questions when language changes.
    Only translates if necessary.
    """
    if 'original_questions' not in st.session_state:
        st.warning("⚠️ No original questions found. Please start a new quiz.")
        return
    
    current_lang = st.session_state.get('language', DEFAULT_LANGUAGE)
    
    # If Indonesian, use original
    if current_lang == 'id':
        st.session_state.questions = st.session_state.original_questions
    else:
        # Translate if needed
        st.session_state.questions = translate_questions_smart(
            st.session_state.original_questions,
            current_lang
        )

# --- Helper Functions ---
def format_time(seconds):
    """Formats seconds into MM:SS format."""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"

def get_grade_message(score_percentage):
    """Returns grade letter and message based on score percentage."""
    for threshold in sorted(GRADE_THRESHOLDS.keys(), reverse=True):
        if score_percentage >= threshold:
            grade, message = GRADE_THRESHOLDS[threshold]
            return grade, message
    # Fallback (should never reach here due to threshold 0)
    return "E", "Keep practicing!"

def restore_session_from_code(code, resume_timer=True):
    """
    Loads session state from Firestore and updates st.session_state.
    Returns True if successful, False otherwise.
    """
    state_data = load_state(code)
    if state_data:
        st.session_state.clear()
        st.session_state.update(state_data)
        # If loading an old save file, ensure answer_history exists
        if 'answer_history' not in st.session_state:
            st.session_state.answer_history = []
        # Reset the start time to now to resume the timer
        if resume_timer and st.session_state.get('timer_enabled', False):
            st.session_state.start_time = time.time()
        return True
    return False

# --- Firestore Connection ---
@st.cache_resource
def get_db_connection():
    """Establishes a connection to the Firestore database."""
    # Authenticate to Firestore with the credentials
    # cred = service_account.Credentials.from_service_account_info(key_dict)
    # db = firestore.Client(credentials=cred)
    # The above is the proper way, but for Streamlit Community Cloud,
    # we can often rely on its auto-discovery of credentials
    return firestore.Client.from_service_account_info(st.secrets["firestore"])

db = get_db_connection()
# --- Local Storage Synchronization ---
# Use st.session_state as the single source of truth for what should be in the browser
if 'session_id' not in st.session_state:
    # On first ever run, set an initial value to trigger a fetch from browser
    st.session_state.session_id = localS.getItem('session_id')

# Only sync to browser when session_id actually changes (not on every rerun)
if 'last_synced_session_id' not in st.session_state:
    st.session_state.last_synced_session_id = None

if st.session_state.session_id != st.session_state.last_synced_session_id:
    localS.setItem('session_id', st.session_state.session_id)
    st.session_state.last_synced_session_id = st.session_state.session_id

# --- Helper Functions for Saving and Loading ---
def generate_save_code(user_name=None):
    """Generates a save code based on user name and random number."""
    if not user_name:
        # Fallback to old method if no name provided
        return f"{random.choice(SAVE_CODE_WORDS)}-{random.choice(SAVE_CODE_WORDS)}-{random.randint(10, 99)}"
    
    # Sanitize name: remove spaces, special chars, convert to uppercase
    clean_name = ''.join(c for c in user_name if c.isalnum()).upper()
    if not clean_name:
        # If name becomes empty after cleaning, use fallback
        return f"{random.choice(SAVE_CODE_WORDS)}-{random.choice(SAVE_CODE_WORDS)}-{random.randint(10, 99)}"
    
    # Limit name to 15 characters
    clean_name = clean_name[:15]
    
    # Generate random 5-digit number
    random_num = random.randint(10000, 99999)
    
    return f"{clean_name}-{random_num}"

def check_code_exists(code):
    """Check if a save code already exists in Firestore."""
    try:
        # Use the cached db connection instead of creating a new one
        doc_ref = db.collection('quiz_sessions').document(code)
        doc = doc_ref.get()
        return doc.exists
    except Exception:
        # If Firestore check fails, assume code doesn't exist
        return False

def generate_unique_save_code(user_name=None):
    """Generate a unique save code that doesn't exist in Firestore."""
    max_attempts = 10
    for _ in range(max_attempts):
        code = generate_save_code(user_name)
        if not check_code_exists(code):
            return code
    
    # If we can't find a unique code after max_attempts, append timestamp
    if user_name:
        clean_name = ''.join(c for c in user_name if c.isalnum()).upper()[:15]
        timestamp = int(time.time()) % 100000  # Last 5 digits of timestamp
        return f"{clean_name}-{timestamp}"
    else:
        return f"{random.choice(SAVE_CODE_WORDS)}-{random.choice(SAVE_CODE_WORDS)}-{random.randint(10, 99)}"

def save_state(code, session_state):
    """Saves the essential quiz state to Firestore, filtering out widget keys."""
    # If the timer is running, "freeze" the elapsed time before saving.
    if session_state.get('timer_enabled', False):
        current_session_time = time.time() - session_state.start_time
        session_state.time_elapsed_before_pause += current_session_time
        session_state.start_time = time.time()
    
    # Create a new, clean dictionary containing only the keys we want to persist.
    state_to_save = {key: session_state[key] for key in STATE_KEYS_TO_SAVE if key in session_state}

    # Save the cleaned dictionary to Firestore.
    doc_ref = db.collection("quiz_sessions").document(code)
    doc_ref.set(state_to_save)
    
def load_state(code):
    """Loads a session state from Firestore."""
    doc_ref = db.collection("quiz_sessions").document(code)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None

def submit_general_feedback(feedback_text):
    """Saves general feedback to the 'general_feedback' collection."""
    if feedback_text: # Ensure feedback is not empty
        doc_ref = db.collection("general_feedback").document()
        doc_ref.set({
            "feedback": feedback_text,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        return True
    return False

def submit_question_report(subject, question, report_text):
    """Saves a report about a specific question."""
    if report_text: # Ensure report is not empty
        doc_ref = db.collection("question_reports").document()
        doc_ref.set({
            "subject": subject,
            "question_text": question,
            "report": report_text,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        return True
    return False

def generate_report_content(session_state):
    """Generates the content for the results report file."""
    subject = session_state.selected_subject
    score = session_state.score
    total_questions = len(session_state.questions)
    final_score_percent = score / total_questions * 100
    grade, _ = get_grade_message(final_score_percent)
    
    # Header and Summary
    report_lines = [
        f"# Quiz Results: {subject}",
        "---",
        "## Summary",
        f"- **Final Score**: {score} / {total_questions} ({final_score_percent:.1f}%)",
        f"- **Grade**: {grade}"
    ]
    
    # Add time taken if the timer was enabled
    if session_state.get('timer_enabled', False) and session_state.get('final_time_taken') is not None:
        formatted_time = format_time(session_state.final_time_taken)
        report_lines.append(f"- **Time Taken**: {formatted_time}")
    
    # Detailed Review
    report_lines.extend(["", "---", "## Answer Review"])
    for i, entry in enumerate(session_state.answer_history):
        q_data = entry["question_data"]
        report_lines.append(f"\n### Question {i+1}: {q_data['question']}")
        
        if entry['is_correct']:
            report_lines.append(f"- ✓ **Your Answer**: {entry['user_choice']} (Correct)")
        else:
            correct_char = q_data['answer']
            correct_full = next((opt for opt in q_data['options'] if opt.lower().strip().startswith(correct_char)), "N/A")
            report_lines.append(f"- ✗ **Your Answer**: {entry['user_choice']}")
            report_lines.append(f"- **Correct Answer**: {correct_full}")
            
    return "\n".join(report_lines)

# --- DICTIONARIES AND CONSTANTS (no changes) ---
SUBJECT_FILES = {
    "Manajemen dan Keberlanjutan (Mankeb)": "multichoice-uts-mankeb.csv",
    "Pemasaran Strategik (Pastra)": "multichoice-uts-pastra.csv",
    "Manajemen Rantai Pasok dan Logistik (MRPL)": "multichoice-uts-mrpl.csv",
    "MRPL PPT Only": "multichoice-uts-mrpl-ppt-only.csv"
}
GITHUB_BASE_URL = "https://github.com/aaprasetyo289/quiz-app/blob/main/"

# --- DATA LOADING (no changes) ---
@st.cache_data
def load_questions(file_path):
    """Loads quiz questions from a CSV file into a list of dictionaries."""
    try:
        df = pd.read_csv(file_path)
        df = df.dropna(subset=[CSV_QUESTION_COL, CSV_OPTIONS_COL, CSV_ANSWER_COL])
        
        # Use to_dict('records') for better performance than iterrows()
        questions = []
        for row in df.to_dict('records'):
            options_list = [opt.strip() for opt in str(row[CSV_OPTIONS_COL]).split('\n')]
            question_data = {
                'question': row[CSV_QUESTION_COL],
                'options': options_list,
                'answer': str(row[CSV_ANSWER_COL]).lower().strip()
            }
            questions.append(question_data)
        return questions
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found.")
        return []
    except KeyError as e:
        st.error(f"Error: A required column is missing from the CSV file: {e}.")
        return []

# --- APP LOGIC ---
st.title("📚 Quiz App")

# --- Initialize States ---
if 'subject_chosen' not in st.session_state:
    st.session_state.subject_chosen = False
    st.session_state.quiz_started = False
if 'language' not in st.session_state:
    st.session_state.language = DEFAULT_LANGUAGE
    st.session_state.previous_language = DEFAULT_LANGUAGE
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

# --- Screen 1: Subject Selection & Load ---
if not st.session_state.subject_chosen:
    # --- Name Input Section ---
    st.subheader("👤 Welcome!")
    
    user_name_input = st.text_input(
        "Enter your name (optional, but recommended for personalized save codes)",
        value=st.session_state.get('user_name', ''),
        placeholder="e.g., John Doe",
        help="Your name will be used to generate a personalized save code like JOHNDOE-12345",
        key="name_input_field"
    )
    
    # Update session state when name changes
    if user_name_input != st.session_state.user_name:
        st.session_state.user_name = user_name_input
    
    if st.session_state.user_name:
        st.success(f"✅ Welcome, {st.session_state.user_name}!")
    
    st.divider()
    
    # --- Resume Autosave Section --- #
    # Call the component to trigger retrieval from the browser's local storage.
    # Only show the "Resume" section if a valid session ID was actually found.
    if st.session_state.session_id:
        st.subheader("Resume Your Last Session?")
        st.write("Click this button to resume your last session.")
        if st.button("Yes, Resume My Last Autosaved Quiz"):
            if restore_session_from_code(st.session_state.session_id):
                # Important: Restore the session_id after clearing
                st.session_state.session_id = localS.getItem('session_id')
                st.success("Resuming your last session...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Could not find your saved session.")
                st.session_state.session_id = None  # Clear the bad ID
                time.sleep(1)
                st.rerun()
    # Resume from code section
    st.header("Start a New Quiz")
    chosen_subject = st.radio("Select a subject to start the quiz:", SUBJECT_FILES.keys())
    if st.button("Select Subject"):
        st.session_state.session_id = None
        
        st.session_state.selected_subject = chosen_subject
        st.session_state.subject_chosen = True
        st.rerun()
    with st.expander("Resume a Saved Quiz with a Code"):
        resume_code = st.text_input("Enter your save code:", placeholder="e.g. CUTE-CAT-42")
        if st.button("Load Quiz"):
            if resume_code:
                if restore_session_from_code(resume_code):
                    st.success("Quiz loaded successfully! Resuming...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid save code. Please try again.")
            else:
                st.warning("Please enter a save code.")
    
    st.divider()

# --- Screen 2: Quiz Configuration ---
elif st.session_state.subject_chosen and not st.session_state.quiz_started:
    st.header(f"Configure Your Quiz: {st.session_state.selected_subject}")
    
    # Load questions for the selected subject
    csv_file = SUBJECT_FILES[st.session_state.selected_subject]
    all_questions = load_questions(csv_file)
    total_questions = len(all_questions)
    
    if not all_questions:
        st.error("Failed to load questions. Please go back and try again.")
        if st.button("Go Back"):
            st.session_state.subject_chosen = False
            st.rerun()
    else:
        st.write(f"Total questions available: **{total_questions}**")
        
        # Configuration options
        num_questions = st.number_input(
            "How many questions do you want?",
            min_value=1,
            max_value=total_questions,
            value=min(10, total_questions),
            step=1
        )
        
        randomize = st.checkbox("Randomise question order", value=True)
        
        st.divider()
        st.subheader("⏱️ Timer Options")
        timer_enabled = st.toggle("Enable Timer?", value=False)
        show_timer = st.toggle("Show Timer on Screen?", value=False)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start Quiz", type="primary"):
                # Prepare questions for the quiz
                if randomize:
                    random.shuffle(all_questions)
                
                # Generate unique save code with user's name
                user_name = st.session_state.get('user_name', '')
                session_id = generate_unique_save_code(user_name if user_name else None)
                st.session_state.session_id = session_id
                
                # Store ORIGINAL questions (Indonesian)
                st.session_state.original_questions = all_questions[:num_questions]
                
                # Initialize translation cache
                st.session_state.translated_questions_cache = {}
                
                # Initialize language tracking
                if 'language' not in st.session_state:
                    st.session_state.language = DEFAULT_LANGUAGE
                if 'previous_language' not in st.session_state:
                    st.session_state.previous_language = DEFAULT_LANGUAGE
                
                # Set displayed questions based on current language
                update_questions_for_language()
                
                st.session_state.current_question_index = 0
                st.session_state.answer_history = [] 
                st.session_state.timer_enabled = timer_enabled
                st.session_state.show_timer = show_timer
                if timer_enabled:
                    st.session_state.start_time = time.time()
                    st.session_state.time_elapsed_before_pause = 0
                    st.session_state.final_time_taken = None
                st.session_state.score = 0
                st.session_state.answer_submitted = False
                st.session_state.scored = False
                st.session_state.quiz_started = True
                st.rerun()
        
        with col2:
            if st.button("Go Back"):
                st.session_state.subject_chosen = False
                st.rerun()
        
        # Show link to data source
        st.divider()
        st.markdown(f"📄 [View Source Data]({GITHUB_BASE_URL}{csv_file})")

# --- Screen 3: The Quiz ---
elif st.session_state.quiz_started:
    # --- Sidebar ---
    with st.sidebar:
        # Language Selector
        st.header("🌍 Language / Bahasa")
        
        # Get current language from session state
        if 'language' not in st.session_state:
            st.session_state.language = DEFAULT_LANGUAGE
        
        current_lang = st.session_state.language
        
        # Find index
        try:
            current_index = list(AVAILABLE_LANGUAGES.keys()).index(current_lang)
        except ValueError:
            current_index = 0
        
        # Callback function for language change
        def on_language_change():
            new_lang = st.session_state.language_selector_widget
            old_lang = st.session_state.get('language', DEFAULT_LANGUAGE)
            
            # Debug logging
            st.session_state.debug_callback_fired = True
            st.session_state.debug_new_lang = new_lang
            st.session_state.debug_old_lang = old_lang
            
            if new_lang != old_lang:
                st.session_state.language = new_lang
                st.session_state.translation_triggered = True
                try:
                    update_questions_for_language()
                    st.session_state.translation_success = True
                except Exception as e:
                    st.session_state.translation_error = str(e)
                    st.session_state.translation_success = False
        
        # Use selectbox WITH a key and on_change callback
        st.selectbox(
            "Select Language",
            options=list(AVAILABLE_LANGUAGES.keys()),
            format_func=lambda x: AVAILABLE_LANGUAGES[x],
            index=current_index,
            key="language_selector_widget",
            on_change=on_language_change,
            label_visibility="collapsed"
        )
        
        # Debug info
        if 0 > 1:
            with st.expander("🔍 Debug Info"):
                st.write(f"Current language: {st.session_state.language}")
                st.write(f"Selector widget value: {st.session_state.get('language_selector_widget', 'NOT SET')}")
                st.write(f"Callback fired: {st.session_state.get('debug_callback_fired', False)}")
                if st.session_state.get('debug_callback_fired', False):
                    st.write(f"  - New lang in callback: {st.session_state.get('debug_new_lang', 'N/A')}")
                    st.write(f"  - Old lang in callback: {st.session_state.get('debug_old_lang', 'N/A')}")
                    st.write(f"  - Translation triggered: {st.session_state.get('translation_triggered', False)}")
                    if st.session_state.get('translation_success') is not None:
                        st.write(f"  - Translation success: {st.session_state.get('translation_success', False)}")
                    if st.session_state.get('translation_error'):
                        st.write(f"  - Translation error: {st.session_state.get('translation_error', 'None')}")
                st.write(f"Has original_questions: {'original_questions' in st.session_state}")
                st.write(f"Has questions: {'questions' in st.session_state}")
                if 'questions' in st.session_state and len(st.session_state.questions) > 0:
                    st.write(f"First question: {st.session_state.questions[0]['question'][:50]}...")
                st.write(f"Cache keys: {list(st.session_state.get('translated_questions_cache', {}).keys())}")
        
        if st.session_state.language != "id":
            st.caption("🤖 Powered by Google Translate")
        
        st.divider()
        
        st.header("⚙️ Settings")
        # Only show quiz-specific settings if the quiz has started
        if st.session_state.get('quiz_started', False):
            st.session_state.auto_next = st.toggle(
                "Auto-Next Question",
                value=st.session_state.get('auto_next', False),
                help="If on, automatically moves to the next question. If off, you must click 'Next Question'."
            )
            st.divider()
            st.header("💾 Save and Load")
            if st.button("Save Progress"):
                # Generate unique save code with user's name
                user_name = st.session_state.get('user_name', '')
                save_code = generate_unique_save_code(user_name if user_name else None)
                
                save_state(save_code, st.session_state)
                st.info("Your progress has been saved!")
                st.success(f"Your save code is: **{save_code}**")
                st.warning("Copy this code to resume later.")
                if user_name:
                    st.caption(f"💡 Your code includes your name: {user_name}")
                  # --- NEW: Load feature inside an expander ---
            with st.expander("Load a Quiz (Discards Current Progress)"):
                resume_code = st.text_input("Enter save code", key="sidebar_resume_code")
                if st.button("Load Quiz"):
                    if resume_code:
                        if restore_session_from_code(resume_code):
                            st.success("Quiz loaded successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Invalid save code.")
                    else:
                        st.warning("Please enter a code.")
        
        # --- NEW: General Feedback Form ---
        st.divider()
        st.header("🗣️ General Feedback")
        feedback_text = st.text_area("Have feedback or questions? Let me know!", key="general_feedback")
        if st.button("Submit Feedback"):
            if submit_general_feedback(feedback_text):
                st.toast("Thank you for your feedback! 🙏")
            else:
                st.toast("Please enter some feedback before submitting.")

    if st.session_state.current_question_index >= len(st.session_state.questions):
        st.header("🎉 Quiz Finished! 🎉")
        st.session_state.session_id = None
        # Finalize and display the timer if it was enabled
        if st.session_state.get('timer_enabled', False):
            # Calculate and store the final time only once
            if st.session_state.get('final_time_taken') is None:
                current_session_time = time.time() - st.session_state.start_time
                st.session_state.final_time_taken = st.session_state.time_elapsed_before_pause + current_session_time
            
            # Format and display the final time
            formatted_time = format_time(st.session_state.final_time_taken)
            st.metric("Total Time Taken", formatted_time)
        
        st.write(f"You got **{st.session_state.score} out of {len(st.session_state.questions)}** questions right")
        final_score = st.session_state.score / len(st.session_state.questions) * 100
        st.write(f"Nilai kamu {final_score:.1f} dari 100")
        
        # Get and display grade message
        grade, message = get_grade_message(final_score)
        st.write(message)
            
        # Prepare the report content for download
        report_data = generate_report_content(st.session_state)
        file_name = f"Quiz_Results_{st.session_state.selected_subject.replace(' ', '_')}.md"

        # Create columns for the buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Play Again", use_container_width=True):
                for key in st.session_state.keys():
                    del st.session_state[key]
                st.session_state.session_id = None
                retrieved_session_id = False
                st.rerun()
        with col2:
            st.download_button(
                label="Export Results",
                data=report_data,
                file_name=file_name,
                mime="text/markdown",
                use_container_width=True
            )
        st.divider()
        with st.expander("🧐 Review Your Answers"):
            for i, entry in enumerate(st.session_state.answer_history):
                q_data = entry["question_data"]
                
                st.subheader(f"Question {i+1}: {q_data['question']}")

                if entry['is_correct']:
                    st.success(f"✓ You correctly answered: {entry['user_choice']}")
                else:
                    # Find the full text of the correct answer
                    correct_answer_char = q_data['answer']
                    correct_answer_full = next(
                        (opt for opt in q_data['options'] if opt.lower().strip().startswith(correct_answer_char)),
                        "N/A"
                    )
                    
                    st.error(f"✗ Your answer: {entry['user_choice']}")
                    st.info(f"Correct answer: {correct_answer_full}")
                
                st.divider()
    else:
        q_data = st.session_state.questions[st.session_state.current_question_index]
        st.write(f"Current Subject: {st.session_state.selected_subject}")
        # Timer display and logic
        if st.session_state.get('timer_enabled', False):
            # Create a placeholder for the timer display
            timer_placeholder = st.empty()

            # Calculate remaining time only if the quiz is not finished
            if st.session_state.current_question_index < len(st.session_state.questions):
                # Time elapsed in the current active session
                current_session_time = time.time() - st.session_state.start_time
                # Total elapsed time including previous saved sessions
                total_elapsed = st.session_state.time_elapsed_before_pause + current_session_time
                
                if st.session_state.show_timer:
                    formatted_time = format_time(total_elapsed)
                    timer_placeholder.metric("Time Elapsed", formatted_time)
            else:
                # When quiz is finished, display the final time
                total_elapsed = st.session_state.time_elapsed_before_pause
                if st.session_state.show_timer:
                    formatted_time = format_time(total_elapsed)
                    timer_placeholder.metric("Total Time Taken", formatted_time)
        st.write(f"Question {st.session_state.current_question_index + 1}/{len(st.session_state.questions)}")
        questions_answered = st.session_state.current_question_index
        current_score = st.session_state.score

        # Calculate percentage based on questions answered, handling the first question case
        if questions_answered > 0:
            percentage = (current_score / questions_answered) * 100
        else:
        # Before any questions are answered, the score is perfect so far
            percentage = 100.0

        # Display using st.metric for a nice visual
        st.metric(label="Current Score", value=f"{percentage:.1f}%")
        st.write(f"You have answered **{current_score}** of **{questions_answered}** questions correctly.")
        
        # Display question and options (already translated if needed)
        st.header(q_data['question'])

        user_choice = st.radio("Choose your answer:", q_data['options'], key=f"q_{st.session_state.current_question_index}", index=None, disabled=st.session_state.answer_submitted)

        if not st.session_state.answer_submitted:
            if st.button("Submit Answer"):
                if user_choice:
                    st.session_state.last_choice = user_choice
                    st.session_state.answer_submitted = True
                    st.rerun()
                else:
                    st.warning("Please select an answer.")
        else:
            chosen_letter = st.session_state.last_choice.split('.')[0].lower().strip()
            correct_answer = q_data['answer']
            if chosen_letter == correct_answer:
                st.success("Correct! 🎉")
                if 'scored' not in st.session_state or not st.session_state.scored:
                    st.session_state.score += 1
                    st.session_state.scored = True
            else:
                st.error(f"Sorry, that's incorrect. The correct answer was '{correct_answer}'.")
                st.session_state.scored = True
                
            # Record the answer for the review screen, ensuring it's only recorded once
            if 'recorded' not in st.session_state or not st.session_state.recorded:
                history_entry = {
                    "question_data": q_data,
                    "user_choice": st.session_state.last_choice,
                    "is_correct": (chosen_letter == correct_answer)
                }
                st.session_state.answer_history.append(history_entry)
                st.session_state.recorded = True
            
            if st.session_state.auto_next:
                time.sleep(1.5)
                st.session_state.current_question_index += 1
                st.session_state.answer_submitted = False
                st.session_state.scored = False
                st.session_state.recorded = False
                # Autosave
                if 'session_id' in st.session_state:
                    save_state(st.session_state.session_id, st.session_state)
                #    st.toast(f"Autosaved session: {st.session_state.session_id}", icon="💾")  
                    st.rerun()
            else:
                if st.button("Next Question"):
                    st.session_state.current_question_index += 1
                    st.session_state.answer_submitted = False
                    st.session_state.scored = False
                    st.session_state.recorded = False
                    # Autosave
                if 'session_id' in st.session_state:
                    save_state(st.session_state.session_id, st.session_state)
                #    st.toast(f"Autosaved session: {st.session_state.session_id}", icon="💾")  
                    st.rerun()
        # --- Per-Question Report Expander ---
        st.divider()
        with st.expander("Report a problem with this question"):
            report_text = st.text_area(
                "Please describe the issue (e.g., wrong answer, typo, unclear question).",
                key=f"report_{st.session_state.current_question_index}" # Unique key
            )
            if st.button("Submit Report", key=f"submit_report_{st.session_state.current_question_index}"):
                if submit_question_report(st.session_state.selected_subject, q_data['question'], report_text):
                    st.toast("Report submitted. Thank you for helping improve the quiz! 👍")
                else:
                    st.toast("Please describe the problem before submitting.")
                    
        if (st.session_state.get('timer_enabled', False) and
        st.session_state.get('show_timer', False) and
        st.session_state.current_question_index < len(st.session_state.questions)):    
            time.sleep(1)
            st.rerun()