import streamlit as st
import pandas as pd
import random
import time

# --- DICTIONARIES AND CONSTANTS ---
SUBJECT_FILES = {
    "Mankeb (Manajemen dan Keberlanjutan)": "multichoice-uts-mankeb.csv",
    "Pastra (Pemasaran Strategik)": "multichoice-uts-pastra.csv"
}

# --- NEW: Define the base URL for your GitHub repo ---
GITHUB_BASE_URL = "https://github.com/aaprasetyo289/quiz-app/blob/main/"

# --- DATA LOADING (no changes here) ---
@st.cache_data
def load_questions(file_path):
    """Loads quiz questions from a specified CSV file."""
    try:
        df = pd.read_csv(file_path)
        df.dropna(subset=['Pertanyaan', 'Pilihan Ganda', 'Jawaban'], inplace=True)
        questions = []
        for index, row in df.iterrows():
            options_list = [opt.strip() for opt in str(row['Pilihan Ganda']).split('\n')]
            question_data = {
                'question': row['Pertanyaan'],
                'options': options_list,
                'answer': str(row['Jawaban']).lower().strip()
            }
            questions.append(question_data)
        return questions
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please make sure it's in the same directory.")
        return []
    except KeyError as e:
        st.error(f"Error: A required column is missing from the CSV file: {e}. Please ensure you have 'Pertanyaan', 'Pilihan Ganda', and 'Jawaban'.")
        return []

# --- APP LOGIC ---

st.title("📚 Quiz App!")

# --- Initialize States ---
if 'subject_chosen' not in st.session_state:
    st.session_state.subject_chosen = False
    st.session_state.quiz_started = False
    st.session_state.selected_subject = None

# --- Screen 1: Subject Selection ---
if not st.session_state.subject_chosen:
    st.header("Welcome! First, choose a subject.")
    chosen_subject = st.radio("Select the subject:", SUBJECT_FILES.keys())
    if st.button("Select Subject"):
        st.session_state.selected_subject = chosen_subject
        st.session_state.subject_chosen = True
        st.rerun()

# --- Screen 2: Quiz Configuration ---
elif not st.session_state.quiz_started:
    file_path = SUBJECT_FILES[st.session_state.selected_subject]
    all_questions = load_questions(file_path)

    if all_questions:
        st.header(f"Configure your quiz for: {st.session_state.selected_subject}")
        
        # --- NEW: Construct and display the GitHub link ---
        full_url = GITHUB_BASE_URL + file_path
        st.markdown(f"**[View Questions & Answers on GitHub ↗️]({full_url})**")
        st.divider() # Adds a nice visual separator
        
        total_questions = len(all_questions)
        num_questions = st.number_input(f"How many questions? (Max: {total_questions})", min_value=1, max_value=total_questions, value=min(10, total_questions))
        randomize = st.toggle("Randomize question order?", value=True)

        if st.button("Start Quiz"):
            questions_to_ask = list(all_questions)
            if randomize: random.shuffle(questions_to_ask)
            st.session_state.questions = questions_to_ask[:num_questions]
            st.session_state.current_question_index = 0
            st.session_state.score = 0
            st.session_state.quiz_started = True
            st.session_state.answer_submitted = False
            st.session_state.auto_next = True
            st.rerun()
    else:
        if st.button("Back to Subject Selection"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

# --- Screen 3: The Quiz (no changes here) ---
elif st.session_state.quiz_started:
    with st.sidebar:
        st.header("⚙️ Settings")
        st.session_state.auto_next = st.toggle(
            "Auto-Next Question",
            value=st.session_state.get('auto_next', True),
            help="If on, automatically moves to the next question after you answer. If off, you must click 'Next Question'."
        )

    if st.session_state.current_question_index >= len(st.session_state.questions):
        st.header("🎉 Quiz Finished! 🎉")
        st.write(f"Your final score is: **{st.session_state.score}/{len(st.session_state.questions)}**")
        st.write(f"Nilai kamu {st.session_state.score/len(st.session_state.questions) * 100:.1f}")
        if st.button("Play Again"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    else:
        q_data = st.session_state.questions[st.session_state.current_question_index]
        st.write(f"Question {st.session_state.current_question_index + 1}/{len(st.session_state.questions)}")
        st.write(f"**Score: {st.session_state.score}**")
        st.header(q_data['question'])

        user_choice = st.radio(
            "Choose your answer:",
            q_data['options'],
            key=f"q_{st.session_state.current_question_index}",
            index=None,
            disabled=st.session_state.answer_submitted
        )

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