import streamlit as st
import pandas as pd
import random
import time
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
    """Saves the essential quiz state to Firestore, filtering out widget keys."""
    # If the timer is running, "freeze" the elapsed time before saving.
    if session_state.get('timer_enabled', False):
        current_session_time = time.time() - session_state.start_time
        session_state.time_elapsed_before_pause += current_session_time
    # Define the specific keys that represent the core state of the quiz.
    keys_to_save = [
        'subject_chosen', 'quiz_started', 'selected_subject',
        'questions', 'current_question_index', 'score', 'auto_next',
        'answer_submitted', 'last_choice', 'scored', 'timer_enabled', 'show_timer',
        'time_elapsed_before_pause'
    ]
    
    # Create a new, clean dictionary containing only the keys we want to persist.
    state_to_save = {key: session_state[key] for key in keys_to_save if key in session_state}

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

# --- DICTIONARIES AND CONSTANTS (no changes) ---
SUBJECT_FILES = {
    "Mankeb (Manajemen dan Keberlanjutan)": "multichoice-uts-mankeb.csv",
    "Pastra (Pemasaran Strategik)": "multichoice-uts-pastra.csv"
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

    # Start new quiz section
    st.subheader("Start a New Quiz")
    chosen_subject = st.radio("Select a subject:", SUBJECT_FILES.keys())
    if st.button("Select Subject"):
        st.session_state.selected_subject = chosen_subject
        st.session_state.subject_chosen = True
        st.rerun()

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
                # Reset the start time to now to resume the timer
                if st.session_state.get('timer_enabled', False):
                    st.session_state.start_time = time.time()
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
        
        st.divider()
        st.subheader("⏱️ Timer Options")
        timer_enabled = st.toggle("Enable Timer?", value=False)
        show_timer = st.toggle("Show Timer on Screen?", value=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start Quiz", type="primary"):
                # Prepare questions for the quiz
                if randomize:
                    random.shuffle(all_questions)
                
                st.session_state.questions = all_questions[:num_questions]
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
        st.header("⚙️ Settings")
        # Only show quiz-specific settings if the quiz has started
        if st.session_state.get('quiz_started', False):
            st.session_state.auto_next = st.toggle(
                "Auto-Next Question",
                value=st.session_state.get('auto_next', True),
                help="If on, automatically moves to the next question. If off, you must click 'Next Question'."
            )
            st.divider()
            st.header("💾 Save and Load")
            if st.button("Save Progress"):
                save_code = generate_save_code()
                save_state(save_code, st.session_state)
                st.info("Your progress has been saved!")
                st.success(f"Your save code is: **{save_code}**")
                st.warning("Copy this code to resume later.")
                  # --- NEW: Load feature inside an expander ---
            with st.expander("Load a Quiz (Discards Current Progress)"):
                resume_code = st.text_input("Enter save code", key="sidebar_resume_code")
                if st.button("Load Quiz"):
                    if resume_code:
                        state_data = load_state(resume_code)
                        if state_data:
                            st.session_state.clear()
                            st.session_state.update(state_data)
                            st.success("Quiz loaded successfully!")
                            time.sleep(1)
                            # Reset the start time to now to resume the timer
                            if st.session_state.get('timer_enabled', False):
                                st.session_state.start_time = time.time()
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
        # Finalize and display the timer if it was enabled
        if st.session_state.get('timer_enabled', False):
            # Calculate and store the final time only once
            if st.session_state.get('final_time_taken') is None:
                current_session_time = time.time() - st.session_state.start_time
                st.session_state.final_time_taken = st.session_state.time_elapsed_before_pause + current_session_time
            
            # Format and display the final time
            minutes, seconds = divmod(int(st.session_state.final_time_taken), 60)
            st.metric("Total Time Taken", f"{minutes:02d}:{seconds:02d}")
        st.write(f"You got **{st.session_state.score} out of {len(st.session_state.questions)}** questions right")
        final_score = st.session_state.score/len(st.session_state.questions) * 100
        st.write(f"Nilai kamu {st.session_state.score/len(st.session_state.questions) * 100:.1f} dari 100")
        match final_score:
            case 100.0:
                st.write("Perfect score, congratulations! Kamu dapat nilai **A**")
            case final_score if 80 <= final_score < 100:
                st.write("Selamat, kamu dapat nilai **A**!")
            case final_score if 75 <= final_score < 80:
                st.write("Selamat, kamu dapat nilai **AB**!")
            case final_score if 70 <= final_score < 75:
                st.write("Selamat, kamu dapat nilai **B**!")
            case final_score if 65 <= final_score < 70:
                st.write("Kamu dapat nilai **BC**.")
            case final_score if 55 <= final_score < 65:
                st.write("Kamu dapat nilai **C**. Better luck next time!")
            case final_score if 45 <= final_score < 55:
                st.write("Kamu dapat nilai **D**. Better luck next time!")
            case _:
                st.write("Kamu dapat nilai **E**. Don't worry, keep practicing and you'll get there!")
            
        if st.button("Play Again"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
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
                    # Format as MM:SS
                    minutes, seconds = divmod(int(total_elapsed), 60)
                    timer_placeholder.metric("Time Elapsed", f"{minutes:02d}:{seconds:02d}")
            else:
                # When quiz is finished, display the final time
                total_elapsed = st.session_state.time_elapsed_before_pause
                if st.session_state.show_timer:
                    minutes, seconds = divmod(int(total_elapsed), 60)
                    timer_placeholder.metric("Total Time Taken", f"{minutes:02d}:{seconds:02d}")
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
                st.rerun()
            else:
                if st.button("Next Question"):
                    st.session_state.current_question_index += 1
                    st.session_state.answer_submitted = False
                    st.session_state.scored = False
                    st.session_state.recorded = False
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