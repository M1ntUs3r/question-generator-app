import random

def filter_questions(questions, topic=None, year=None, paper=None):
    """Filter by optional criteria."""
    filtered = questions
    if topic:
        filtered = [q for q in filtered if str(q["topic"]).lower() == topic.lower()]
    if year:
        filtered = [q for q in filtered if str(q["year"]) == str(year)]
    if paper:
        filtered = [q for q in filtered if str(q["paper"]).lower() == paper.lower()]
    return filtered

def get_random_questions(questions, count=10, filters=None):
    filters = filters or {}
    filtered = filter_questions(questions, **filters)
    if len(filtered) < count:
        count = len(filtered)
    return random.sample(filtered, count)
