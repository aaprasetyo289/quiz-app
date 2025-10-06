import streamlit as st
import pandas as pd
import random
import time
import json
from google.cloud import firestore

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

# --- Helper Functions for Saving and Loading ---
def generate_save_code():
    """Generates a simple, memorable save code."""
    words = ["APPLE", "BEAR", "CANDY", "DREAM", "EAGLE", "FROG", "GIANT"]
    return f"{random.choice(words)}-{random.choice(words)}-{random.randint(10, 99)}"

def save_state(code, session_state):
    """Saves the current session state to Firestore."""
    # Convert the Streamlit session state object to a plain dictionary
    state_dict = dict(session_state.items())
    # Save the dictionary to Firestore
    doc_ref = db.collection("quiz_sessions").document(code)
    doc_ref.set(state_dict)

def load_state(code):
    """Loads a session state from Firestore."""
    doc_ref = db.collection("quiz_sessions").document(code)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None

# --- DICTIONARIES AND CONSTANTS (no changes) ---
SUBJECT_FILES = {
    "Mankeb (Manajemen dan Keberlanjutan)": "multichoice-uts-mankeb.csv",
    "Pastra (Pemasaran Strategik) !!!BELUM BISA!!!": "multichoice-uts-pastra.csv"
}
GITHUB_BASE_URL = "https://github.com/aaprasetyo289/quiz-app/blob/main/"

# --- DATA LOADING (no changes) ---
@st.cache_data
def load_questions(file_path):
    # ... (rest of the function is the same)
    try:
        df = pd.read_csv(file_path)
        df = df.dropna(subset=['Pertanyaan', 'Pilihan Ganda', 'Jawaban'])
        questions = []
        for index, row in df.iterrows():
            options_list = [opt.strip() for opt in str(row['Pilihan Ganda']).split('\n')]
            question_data = {'question': row['Pertanyaan'], 'options': options_list, 'answer': str(row['Jawaban']).lower().strip()}
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

# --- Screen 1: Subject Selection & Load ---
if not st.session_state.subject_chosen:
    st.header("Start a New Quiz or Resume")

    # Resume from code section
    st.subheader("Resume a Saved Quiz")
    resume_code = st.text_input("Enter your save code:", placeholder="e.g., APPLE-BEAR-42")
    if st.button("Load Quiz"):
        if resume_code:
            state_data = load_state(resume_code)
            if state_data:
                # Clear current state and load the saved one
                st.session_state.clear()
                st.session_state.update(state_data)
                st.success("Quiz loaded successfully! Resuming...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid save code. Please try again.")
        else:
            st.warning("Please enter a save code.")
    
    st.divider()

    # Start new quiz section
    st.subheader("Start a New Quiz")
    chosen_subject = st.radio("Select a subject:", SUBJECT_FILES.keys())
    if st.button("Select Subject"):
        st.session_state.selected_subject = chosen_subject
        st.session_state.subject_chosen = True
        st.rerun()

# --- Screen 2: Quiz Configuration ---
elif st.session_state.subject_chosen and not st.session_state.quiz_started:
    st.header(f"Configure Your Quiz: {st.session_state.selected_subject}")
    
    # Load questions for the selected subject
    csv_file = SUBJECT_FILES[st.session_state.selected_subject]
    all_questions = load_questions(csv_file)
    
    if not all_questions:
        st.error("Failed to load questions. Please go back and try again.")
        if st.button("Go Back"):
            st.session_state.subject_chosen = False
            st.rerun()
    else:
        st.write(f"Total questions available: **{len(all_questions)}**")
        
        # Configuration options
        num_questions = st.number_input(
            "How many questions do you want?",
            min_value=1,
            max_value=len(all_questions),
            value=min(10, len(all_questions)),
            step=1
        )
        
        randomize = st.checkbox("Randomize question order", value=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start Quiz", type="primary"):
                # Prepare questions for the quiz
                if randomize:
                    random.shuffle(all_questions)
                
                st.session_state.questions = all_questions[:num_questions]
                st.session_state.current_question_index = 0
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
    with st.sidebar:
        st.header("⚙️ Settings")
        st.session_state.auto_next = st.toggle(
            "Auto-Next Question",
            value=st.session_state.get('auto_next', True),
            help="If on, automatically moves to the next question. If off, you must click 'Next Question'."
        )
        st.divider()

        # --- NEW: Save and Exit Feature ---
        st.header("💾 Save Progress")
        if st.button("Save"):
            save_code = generate_save_code()
            save_state(save_code, st.session_state)
            st.info("Your progress has been saved!")
            st.success(f"Your save code is: **{save_code}**")
            st.warning("Copy this code and use it on the main page to resume.")
            # We don't exit automatically, to give the user time to copy the code.

    # ... (the rest of your quiz logic for displaying questions, etc.)
    # Make sure this code is placed within the `elif st.session_state.quiz_started:` block.
    if st.session_state.current_question_index >= len(st.session_state.questions):
        st.header("🎉 Quiz Finished! 🎉")
        st.write(f"Your final score is: **{st.session_state.score}/{len(st.session_state.questions)}**")
        st.write(f"Nilai kamu {st.session_state.score/len(st.session_state.questions) * 100:.1f}")
        if st.button("Play Again"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
    else:
        q_data = st.session_state.questions[st.session_state.current_question_index]
        st.write(f"Current Subject: {st.session_state.selected_subject}")
        st.write(f"Question {st.session_state.current_question_index + 1}/{len(st.session_state.questions)}")
        st.write(f"**Score: {st.session_state.score}**")
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
            
            if st.session_state.auto_next:
                time.sleep(1.5)
                st.session_state.current_question_index += 1
                st.session_state.answer_submitted = False
                st.session_state.scored = False
                st.rerun()
            else:
                if st.button("Next Question"):
                    st.session_state.current_question_index += 1
                    st.session_state.answer_submitted = False
                    st.session_state.scored = False
                    st.rerun()