import os
import re
from typing import List, Dict

def parse_interview_guide(file_path: str) -> List[Dict[str, str]]:
    """Parses Interview_Guide.txt into a list of question dicts [{"id": "q1", "text": "..."}]"""
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    questions = []
    lines = content.splitlines()

    for line in lines:
        line_str = line.strip()
        # Match questions starting with "1.", "2.", etc.
        match = re.match(r'^(\d+)\.\s+(.*)$', line_str)
        if match:
            q_num = match.group(1)
            q_text = match.group(2).strip()
            questions.append({
                "id": f"q{q_num}",
                "text": q_text
            })

    return questions
