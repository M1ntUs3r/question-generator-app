import pandas as pd
import random
import json
import os

EXCEL_FILE = "Book1.ods"
USED_FILE = "used_questions.json"


import re
import pandas as pd

def _parse_header_token(header):
    """Optional: parse year/paper if needed"""
    s = str(header).strip()
    year_match = re.search(r'(20\d{2}|19\d{2})', s)
    year = year_match.group(0) if year_match else ""
    paper = ""
    if re.search(r'\bP(?:aper)?\s*1\b', s, re.IGNORECASE) or re.search(r'\bP1\b', s, re.IGNORECASE):
        paper = "P1"
    elif re.search(r'\bP(?:aper)?\s*2\b', s, re.IGNORECASE) or re.search(r'\bP2\b', s, re.IGNORECASE):
        paper = "P2"
    return year, paper

def load_questions():
    """Load questions with solutions from spreadsheet."""
    df = pd.read_excel(EXCEL_FILE, engine="odf")  # or openpyxl if xlsx
    questions = []

    for idx, row in df.iterrows():
        question = {
            "topic": str(row.get("topic", "")).strip(),
            "year": str(row.get("year", "")).strip(),
            "paper": str(row.get("paper", "")).strip(),
            "question_id": str(row.get("question_ID", "")).strip(),
            "pdf_question": str(row.get("PDF Question", "")).strip(),
            "pdf_solution": str(row.get("PDF Solution", "")).strip(),
            "q_pages": str(row.get("Q_Pages", "")).strip(),
            "s_pages": str(row.get("S_pages", "")).strip(),
        }
        questions.append(question)

    return questions



def load_used_questions():
    """Load previously used questions from JSON."""
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_used_questions(used_questions):
    """Save used questions to JSON."""
    with open(USED_FILE, "w") as f:
        json.dump(list(used_questions), f, indent=2)


def generate_random_questions(all_questions, used_questions, n):
    """Generate n random unused questions (works for dicts too)."""
    used_texts = set(used_questions)

    def qid(q):
        return f"{q['year']} {q['paper']} – {q['question']} – {q['topic']}"

    available = [q for q in all_questions if qid(q) not in used_texts]

    if len(available) < n:
        print("⚠️ Not enough unused questions left. Resetting history.")
        used_questions.clear()
        available = all_questions

    import random
    selection = random.sample(available, n)

    used_questions.update(qid(q) for q in selection)
    save_used_questions(used_questions)

    return selection



def replace_question(current_list, all_questions, used_questions, index):
    """Replace a single question in the list."""
    def qid(q):
        return f"{q['year']} {q['paper']} – {q['question']} – {q['topic']}"

    used_texts = set(used_questions)
    available = [q for q in all_questions if qid(q) not in used_texts]

    if not available:
        print("⚠️ No unused questions left. Resetting history.")
        used_questions.clear()
        available = all_questions

    import random
    new_q = random.choice(available)
    used_questions.add(qid(new_q))
    save_used_questions(used_questions)
    current_list[index] = new_q
    return current_list



def save_to_excel(selected_questions):
    """Save the selected questions to a new sheet."""
    try:
        with pd.ExcelWriter(EXCEL_FILE, mode="a", engine="openpyxl", if_sheet_exists="new") as writer:
            pd.DataFrame({"Generated Questions": selected_questions}).to_excel(
                writer, index=False, sheet_name="Generated_Questions"
            )
        print(f"✅ Saved to new sheet in '{EXCEL_FILE}'.")
    except Exception as e:
        print(f"❌ Could not save to Excel: {e}")


def main():
    print("📘 Random Question Generator")
    print("=" * 40)

    all_questions = load_questions()
    used_questions = load_used_questions()

    while True:
        try:
            n = int(input("\nHow many questions would you like to generate? "))
            break
        except ValueError:
            print("Please enter a valid number.")

    questions = generate_random_questions(all_questions, used_questions, n)

    while True:
        print("\nYour generated questions:")
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q}")

        print("\nOptions:")
        print("1. Generate a completely new list")
        print("2. Replace a specific question")
        print("3. Save current list to Excel")
        print("4.  Exit")

        choice = input("Choose an option (1-4): ").strip()

        if choice == "1":
            questions = generate_random_questions(all_questions, used_questions, n)
        elif choice == "2":
            try:
                idx = int(input("Enter question number to replace: ")) - 1
                if 0 <= idx < len(questions):
                    questions = replace_question(questions, all_questions, used_questions, idx)
                else:
                    print("❌ Invalid question number.")
            except ValueError:
                print("❌ Please enter a number.")
        elif choice == "3":
            save_to_excel(questions)
        elif choice == "4":
            print("👋 Exiting. Goodbye!")
            break
        else:
            print("❌ Invalid option. Try again.")


if __name__ == "__main__":
    main()
