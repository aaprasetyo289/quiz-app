import streamlit as st
import pandas as pd
import random
import time
from google.cloud import firestore
from streamlit_local_storage import LocalStorage

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
    'subject_chosen', 'quiz_started', 'selected_subject',
    'questions', 'current_question_index', 'score', 'auto_next',
    'answer_submitted', 'last_choice', 'scored', 'timer_enabled',
    'show_timer', 'time_elapsed_before_pause', 'answer_history'
]

# --- Initialise Local Storage ---
localS = LocalStorage()

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

# Now, on every run, sync the browser's state to match our session_state
localS.setItem('session_id', st.session_state.session_id)

# --- Helper Functions for Saving and Loading ---
def generate_save_code():
    """Generates a simple, memorable save code."""
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
    "Mankeb (Manajemen dan Keberlanjutan)": "multichoice-uts-mankeb.csv",
    "Pastra (Pemasaran Strategik)": "multichoice-uts-pastra.csv"
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

# --- Screen 1: Subject Selection & Load ---
if not st.session_state.subject_chosen:    
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
        
        randomize = st.checkbox("Randomise question order", value=True)
        
        st.divider()
        st.subheader("⏱️ Timer Options")
        timer_enabled = st.toggle("Enable Timer?", value=True)
        show_timer = st.toggle("Show Timer on Screen?", value=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start Quiz", type="primary"):
                # Prepare questions for the quiz
                if randomize:
                    random.shuffle(all_questions)
                
                session_id = generate_save_code()
                st.session_state.session_id = session_id
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
                while True:
                    save_code = generate_save_code()
                    if load_state(save_code) is None:
                    # This code is unique, so we can exit the loop.
                        break
                save_state(save_code, st.session_state)
                st.info("Your progress has been saved!")
                st.success(f"Your save code is: **{save_code}**")
                st.warning("Copy this code to resume later.")
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