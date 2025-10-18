import pandas as pd
import random

EXCEL_FILE = "converted_questions.ods"

def load_questions():
    df = pd.read_excel(EXCEL_FILE, engine="odf")
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={
        "question id": "question_id",
        "topic": "topic",
        "year": "year",
        "paper": "paper"
    })
    return df

def clean_question_number(qid):
    """
    Extracts the question number cleanly from IDs like '2014_P1_Q1', '2014_P1_Q12', etc.
    Removes underscores and prefixes.
    """
    if not isinstance(qid, str):
        return ""
    # Find part after the last 'Q' and remove underscores
    if "Q" in qid:
        q_part = qid.split("Q")[-1].strip("_")
        return "Q" + q_part.lstrip("_")
    return qid[-3:]  # fallback for other formats

def generate_random_questions(df, n=5):
    # Randomly select n rows
    selected = df.sample(n=min(n, len(df)), random_state=random.randint(0, 9999))
    
    # Sort by Year then Paper (P1 before P2)
    selected = selected.sort_values(
        by=["year", "paper"],
        key=lambda col: col.map({"P1": 1, "P2": 2}).fillna(3)
    )
    
    # Build display strings
    output = []
    for _, row in selected.iterrows():
        q_num = clean_question_number(row["question_id"])
        output.append(f"{q_num} — {row['year']} {row['paper']} — {row['topic']}")
    return output

def main():
    df = load_questions()
    print(f"✅ Loaded {len(df)} questions from {EXCEL_FILE}")
    
    try:
        n = int(input("How many questions would you like to generate? "))
    except ValueError:
        n = 5

    random_questions = generate_random_questions(df, n)
    
    print("\n🎯 Randomly Selected Questions (Sorted by Year & Paper):")
    print("----------------------------------------------------------")
    for q in random_questions:
        print(q)

if __name__ == "__main__":
    main()
