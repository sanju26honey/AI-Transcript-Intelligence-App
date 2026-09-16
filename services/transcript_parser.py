import re
import os
from typing import Tuple, List
from models import TranscriptMetadata, TranscriptSegment

def parse_timestamp_to_seconds(ts_str: str) -> int:
    """Converts MM:SS or HH:MM:SS to total seconds."""
    parts = ts_str.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0

def parse_transcript_file(file_path: str) -> Tuple[TranscriptMetadata, List[TranscriptSegment]]:
    """Parses a transcript file into metadata and a list of TranscriptSegments."""
    filename = os.path.basename(file_path)
    transcript_id = os.path.splitext(filename)[0]

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = [line.rstrip() for line in content.splitlines()]

    # Parse metadata header
    expert_name = "Unknown Expert"
    role = "Unknown Role"
    market = "Unknown Market"

    header_end_idx = 0
    for idx, line in enumerate(lines):
        if line.startswith("Expert"):
            expert_name = line.split("–")[-1].strip() if "–" in line else line.strip()
        elif line.startswith("Role:"):
            role = line.replace("Role:", "").strip()
        elif line.startswith("Market:"):
            market = line.replace("Market:", "").strip()
        elif re.match(r'^\d{2}:\d{2}', line):
            header_end_idx = idx
            break

    metadata = TranscriptMetadata(
        transcript_id=transcript_id,
        expert_name=expert_name,
        role=role,
        market=market,
        file_path=file_path
    )

    segments: List[TranscriptSegment] = []
    current_timestamp = "00:00"
    current_speaker = "Unknown"
    current_text_lines = []
    segment_counter = 0

    body_lines = lines[header_end_idx:]
    i = 0
    while i < len(body_lines):
        line = body_lines[i].strip()
        if not line:
            i += 1
            continue

        # Check for timestamp line like 00:18
        if re.match(r'^\d{2}:\d{2}$', line) or re.match(r'^\d{2}:\d{2}:\d{2}$', line):
            # Flush previous segment if exists
            if current_text_lines:
                text_content = " ".join(current_text_lines).strip()
                if text_content:
                    segments.append(TranscriptSegment(
                        transcript_id=transcript_id,
                        expert_name=expert_name,
                        market=market,
                        speaker=current_speaker,
                        text=text_content,
                        timestamp=current_timestamp,
                        start_seconds=parse_timestamp_to_seconds(current_timestamp),
                        segment_index=segment_counter
                    ))
                    segment_counter += 1
                current_text_lines = []

            current_timestamp = line
            i += 1
            continue

        # Check speaker line like "Dr. Martin: Adoption is growing..."
        if ":" in line and not line.startswith("http"):
            parts = line.split(":", 1)
            possible_speaker = parts[0].strip()
            # If previous text was accumulating, flush before new speaker
            if current_text_lines:
                text_content = " ".join(current_text_lines).strip()
                if text_content:
                    segments.append(TranscriptSegment(
                        transcript_id=transcript_id,
                        expert_name=expert_name,
                        market=market,
                        speaker=current_speaker,
                        text=text_content,
                        timestamp=current_timestamp,
                        start_seconds=parse_timestamp_to_seconds(current_timestamp),
                        segment_index=segment_counter
                    ))
                    segment_counter += 1
                current_text_lines = []

            current_speaker = possible_speaker
            current_text_lines.append(parts[1].strip())
        else:
            current_text_lines.append(line)

        i += 1

    # Flush last segment
    if current_text_lines:
        text_content = " ".join(current_text_lines).strip()
        if text_content:
            segments.append(TranscriptSegment(
                transcript_id=transcript_id,
                expert_name=expert_name,
                market=market,
                speaker=current_speaker,
                text=text_content,
                timestamp=current_timestamp,
                start_seconds=parse_timestamp_to_seconds(current_timestamp),
                segment_index=segment_counter
            ))

    return metadata, segments
