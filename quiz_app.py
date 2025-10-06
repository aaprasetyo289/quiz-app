import pandas as pd
import random

def load_questions(file_path):
    """Loads quiz questions from a CSV file into a list of dictionaries."""
    try:
        # --- THIS IS THE ONLY LINE THAT CHANGED ---
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(file_path)
        # --- END OF CHANGE ---

        # The rest of the function is identical
        questions = []
        for index, row in df.iterrows():
            # Ensure the 'Pilihan Ganda' column is treated as a string before splitting
            options_list = [opt.strip() for opt in str(row['Pilihan Ganda']).split('\n')]
            question_data = {
                'question': row['Pertanyaan'],
                'options': options_list,
                'answer': str(row['Jawaban']).lower().strip()
            }
            questions.append(question_data)
        return questions
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return []

def run_quiz(questions, num_questions=None, randomize=True):
    """Runs the quiz, asking a specified number of questions."""
    if not questions:
        print("No questions to run the quiz.")
        return

    if randomize:
        random.shuffle(questions)

    if num_questions is None or num_questions > len(questions):
        questions_to_ask = questions
    else:
        questions_to_ask = questions[:num_questions]
    
    score = 0
    print("\n--- Welcome to the Quiz! ---")

    for i, q_data in enumerate(questions_to_ask, 1):
        print(f"\nQuestion {i}: {q_data['question']}")
        for option in q_data['options']:
            print(f"  {option}")
        
        user_answer = ""
        while not user_answer:
            user_answer = input("Your answer (e.g., 'a', 'b', 'c', etc.): ").lower().strip()

        if user_answer == q_data['answer']:
            print("Correct! 🎉")
            score += 1
        else:
            print(f"Sorry, the correct answer was '{q_data['answer']}'.")

    print("\n--- Quiz Finished! ---")
    print(f"Your final score is: {score}/{len(questions_to_ask)}")

# --- Main part of the program ---
if __name__ == "__main__":
    # Just update the file name here
    file_name = 'multichoice-uts-mankeb.csv'
    all_questions = load_questions(file_name)

    if all_questions:
        try:
            num = int(input(f"How many questions do you want? (Max: {len(all_questions)}): "))
            is_random = input("Randomize questions? (yes/no): ").lower().strip() == 'yes'
            run_quiz(all_questions, num_questions=num, randomize=is_random)
        except ValueError:
            print("Invalid number. Please enter an integer.")