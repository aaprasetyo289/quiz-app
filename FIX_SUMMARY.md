# Quiz App - Fix Summary

## Issues Fixed ✅

### 1. **Code Quality Issues in Helper Functions**
- **Problem**: Used dict comprehension instead of dict constructor
- **Fix**: Changed `{k: v for k, v in session_state.items()}` to `dict(session_state.items())`
- **Location**: `save_state()` function (line 31)

### 2. **F-String Without Replacements**
- **Problem**: Used f-string without any format placeholders
- **Fix**: Changed `f"Quiz loaded successfully! Resuming..."` to regular string
- **Location**: Load quiz success message (line 94)

### 3. **DataFrame inplace Parameter**
- **Problem**: Used deprecated `inplace=True` parameter with `dropna()`
- **Fix**: Changed to `df = df.dropna(...)` pattern
- **Location**: `load_questions()` function (line 58)

### 4. **Missing Screen 2 (Quiz Configuration)**
- **Problem**: The quiz configuration screen logic was completely missing
- **Fix**: Implemented complete Screen 2 with:
  - Number input for question count
  - Checkbox for randomization
  - Start Quiz and Go Back buttons
  - Display of total available questions
  - Link to source data on GitHub
- **Location**: Lines 111-161

### 5. **Unnecessary list() Call**
- **Problem**: Used `list(st.session_state.keys())` when keys() is already iterable
- **Fix**: Changed to direct iteration over `st.session_state.keys()`
- **Location**: "Play Again" button logic (line 191)

## App Structure

The app now has a complete three-screen flow:

### Screen 1: Subject Selection & Load
- Resume a saved quiz with a save code
- OR start a new quiz by selecting a subject

### Screen 2: Quiz Configuration
- Select number of questions (1 to max available)
- Toggle randomization
- View total questions available
- Access to source data on GitHub

### Screen 3: Quiz Gameplay
- Question display with multiple choice options
- Answer submission and feedback
- Auto-next or manual progression
- Score tracking
- Save & Exit functionality (saves to Firestore)
- Final score display with percentage

## How to Run

```bash
streamlit run quiz_webapp.py
```

## Requirements

- `streamlit`
- `pandas`
- `google-cloud-firestore` (optional, for save/load features)

## Features

✅ Multiple subjects support
✅ Configurable number of questions
✅ Question randomization
✅ Auto-next or manual progression
✅ Progress saving to Firestore
✅ Resume from save code
✅ Score tracking and final results
✅ Clean, error-free code

## Notes

- CSV file must have columns: `Pertanyaan`, `Pilihan Ganda`, `Jawaban`
- Save/Load features require Firestore credentials in `.streamlit/secrets.toml`
- Currently supports "Mankeb" subject (185 questions)
