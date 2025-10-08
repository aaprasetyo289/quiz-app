# languages.py
import streamlit as st

LANGUAGES = {
    "EN": {
        # General
        "app_title": "Quiz App",
        "settings_header": "Settings",

        # Welcome Screen
        "welcome_header": "Start a New Quiz or Resume",
        "start_new_quiz_subheader": "Start a New Quiz",
        "select_subject_radio": "Select a subject:",
        "select_subject_button": "Select Subject",
        "resume_autosave_subheader": "Resume Your Last Session?",
        "resume_autosave_button": "Yes, Resume My Last Autosaved Quiz",
        "resume_code_subheader": "Resume a Saved Quiz with a Code",
        "resume_code_placeholder": "e.g., APPLE-BEAR-42",
        "load_quiz_button": "Load Quiz",

        # Config Screen
        "config_header": "Configure Your Quiz: {subject}",
        "total_questions_available": "Total questions available: **{count}**",
        "how_many_questions": "How many questions do you want?",
        "randomize_checkbox": "Randomize question order",
        "timer_options_subheader": "Timer Options",
        "enable_timer_toggle": "Enable Timer?",
        "show_timer_toggle": "Show Timer on Screen?",
        "start_quiz_button": "Start Quiz",
        "go_back_button": "Go Back",
        "view_source_data_link": "📄 [View Source Data]({url})",

        # Quiz Screen
        "current_subject": "Current Subject: {subject}",
        "question_counter": "Question {current}/{total}",
        "score_display": "**{score}** out of **{total}** correct.",
        "final_score_display": "**Score: {score}**",
        "time_elapsed_metric": "Time Elapsed",
        "submit_answer_button": "Submit Answer",
        "next_question_button": "Next Question",

        # Finished Screen
        "finished_header": "🎉 Quiz Finished! 🎉",
        "total_time_taken_metric": "Total Time Taken",
        "final_score_write": "You got **{score} out of {total}** questions right",
        "your_grade_write": "Your final score is {final_score:.1f} out of 100",
        "play_again_button": "Play Again",
        "export_results_button": "Export Results",
        "review_answers_expander": "🧐 Review Your Answers",

        # Sidebar
        "auto_next_toggle": "Auto-Next Question",
        "save_load_header": "Save & Load Progress",
        "save_button": "Save Progress",
        "load_expander": "Load a Quiz (Discards Current Progress)",
        "feedback_header": "🗣️ General Feedback",
        "feedback_placeholder": "Have feedback or questions? Let me know!",
        "submit_feedback_button": "Submit Feedback",
    },
    "ID": {
        # General
        "app_title": "Aplikasi Kuis",
        "settings_header": "Pengaturan",

        # Welcome Screen
        "welcome_header": "Mulai Kuis Baru atau Lanjutkan",
        "start_new_quiz_subheader": "Mulai Kuis Baru",
        "select_subject_radio": "Pilih mata kuliah:",
        "select_subject_button": "Pilih Mata Kuliah",
        "resume_autosave_subheader": "Lanjutkan Sesi Terakhir?",
        "resume_autosave_button": "Ya, Lanjutkan Kuis Terakhir",
        "resume_code_subheader": "Lanjutkan Kuis dengan Kode",
        "resume_code_placeholder": "contoh: APPLE-BEAR-42",
        "load_quiz_button": "Muat Kuis",

        # Config Screen
        "config_header": "Atur Kuis Anda: {subject}",
        "total_questions_available": "Total soal tersedia: **{count}**",
        "how_many_questions": "Berapa soal yang Anda inginkan?",
        "randomize_checkbox": "Acak urutan soal",
        "timer_options_subheader": "Opsi Timer",
        "enable_timer_toggle": "Aktifkan Timer?",
        "show_timer_toggle": "Tampilkan Timer di Layar?",
        "start_quiz_button": "Mulai Kuis",
        "go_back_button": "Kembali",
        "view_source_data_link": "📄 [Lihat Sumber Data]({url})",

        # Quiz Screen
        "current_subject": "Mata Kuliah: {subject}",
        "question_counter": "Soal {current}/{total}",
        "score_display": "**{score}** dari **{total}** benar.",
        "final_score_display": "**Skor: {score}**",
        "time_elapsed_metric": "Waktu Berlalu",
        "submit_answer_button": "Kirim Jawaban",
        "next_question_button": "Soal Berikutnya",

        # Finished Screen
        "finished_header": "🎉 Kuis Selesai! 🎉",
        "total_time_taken_metric": "Total Waktu",
        "final_score_write": "Kamu berhasil menjawab **{score} dari {total}** soal dengan benar",
        "your_grade_write": "Nilai kamu {final_score:.1f} dari 100",
        "play_again_button": "Ulang Quiz",
        "export_results_button": "Download Hasil",
        "review_answers_expander": "🧐 Tinjau Jawaban Anda",

        # Sidebar
        "auto_next_toggle": "Lanjut Otomatis",
        "save_load_header": "Simpan & Muat Progres",
        "save_button": "Simpan Progres",
        "load_expander": "Muat Kuis (Akan menghapus progres saat ini)",
        "feedback_header": "🗣️ Saran dan Kritik",
        "feedback_placeholder": "Punya masukan atau pertanyaan? Kasih tahu aku di sini ya!",
        "submit_feedback_button": "Kirim Saran/Kritik",
    }
}

def get_lang():
    """Returns the dictionary of strings for the currently selected language."""
    if 'lang' not in st.session_state:
        st.session_state.lang = "EN"  # Default language
    return LANGUAGES[st.session_state.lang]