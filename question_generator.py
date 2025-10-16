import pandas as pd
import random
import json
import os

EXCEL_FILE = "Book1.ods"
USED_FILE = "used_questions.json"


import re
import pandas as pd

def _parse_header_token(header):
    """Return (year, paper) parsed from header string."""
    s = str(header).strip()
    # find a 4-digit year
    year_match = re.search(r'(20\d{2}|19\d{2})', s)
    year = year_match.group(0) if year_match else ""

    # look for P1, P2, Paper 1, Paper2, or standalone '1'/'2' that likely mean paper
    paper = ""
    # common patterns
    if re.search(r'\bP(?:aper)?\s*1\b', s, re.IGNORECASE) or re.search(r'\bP1\b', s, re.IGNORECASE):
        paper = "P1"
    elif re.search(r'\bP(?:aper)?\s*2\b', s, re.IGNORECASE) or re.search(r'\bP2\b', s, re.IGNORECASE):
        paper = "P2"
    # sometimes header like "P1 2023" or "2023 P1" or just "1" or "2"
    elif re.search(r'\b1\b', s) and not year_match:
        # if there's a bare 1 and no year, interpret as P1
        paper = "P1"
    elif re.search(r'\b2\b', s) and not year_match:
        paper = "P2"
    # detect calculator keywords
    elif re.search(r'calc(?:ulator)?', s, re.IGNORECASE):
        # try to infer which paper is calculator in your convention
        paper = "P2"  # common convention: P2 = calculator
    elif re.search(r'non[-\s]?calc|noncalc|non calculator|no calc', s, re.IGNORECASE):
        paper = "P1"
    # fallback: if nothing found, try to pick 'P1' if header contains '1' anywhere (likely), else leave blank
    if not paper:
        if re.search(r'1', s):
            paper = "P1"
        elif re.search(r'2', s):
            paper = "P2"

    return year, paper

def load_questions():
    """Load questions from EXCEL_FILE and return structured list with topic, year, paper, question."""
    df = pd.read_excel(EXCEL_FILE, header=0)
    # topic names (rows, after header row)
    topics = df.iloc[1:, 0].dropna().tolist()
    raw_headers = df.iloc[0, 1:].tolist()  # the column headers after first column
    data = df.iloc[1:, 1:]                 # the question cells

    # parse headers into (year, paper)
    header_info = []
    for h in raw_headers:
        year, paper = _parse_header_token(h)
        header_info.append({"raw": str(h), "year": year, "paper": paper})

    questions = []
    for topic_idx, topic in enumerate(topics):
        for col_idx, info in enumerate(header_info):
            cell_value = data.iloc[topic_idx, col_idx]
            if pd.notna(cell_value):
                questions.append({
                    "topic": str(topic).strip(),
                    "year": info["year"] or "",   # possibly empty if not detected
                    "paper": info["paper"] or "", # possibly empty if not detected
                    "question": str(cell_value).strip(),
                    "col_header": info["raw"]
                })
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
