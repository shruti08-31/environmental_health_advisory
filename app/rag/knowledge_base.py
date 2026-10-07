from pathlib import Path
import re


def load_knowledge_document(file_path):
    """
    Load the environmental health knowledge document.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Knowledge document not found: {file_path}"
        )

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError(
            "Knowledge document must be UTF-8 encoded."
        )

    text = text.strip()

    if not text:
        raise ValueError(
            "Knowledge document is empty."
        )

    return text


def split_into_chunks(text):
    """
    Split the knowledge document into smaller,
    meaningful chunks for better RAG retrieval.
    """

    if not isinstance(text, str):
        raise ValueError("Knowledge document must be a string.")

    text = text.strip()

    if not text:
        raise ValueError("Knowledge document is empty.")

    chunks = []

    # Find major section headings such as:
    # == KEY POLLUTANTS ==
    # == HEALTH EFFECTS OF AIR POLLUTION ==
    heading_pattern = r"(?m)^==\s*(.*?)\s*==\s*$"

    matches = list(re.finditer(heading_pattern, text))

    if not matches:
        return _split_large_text(text, "GENERAL")

    for index, match in enumerate(matches):

        section_title = match.group(1).strip()

        section_start = match.end()

        if index + 1 < len(matches):
            section_end = matches[index + 1].start()
        else:
            section_end = len(text)

        section_text = text[section_start:section_end].strip()

        if not section_text:
            continue

        # Special handling for KEY POLLUTANTS.
        # Each pollutant gets its own chunk.
        if section_title.upper() == "KEY POLLUTANTS":

            pollutant_chunks = _split_pollutants(section_text)

            for pollutant_chunk in pollutant_chunks:
                chunks.append({
                    "text": pollutant_chunk,
                    "section": section_title
                })

        else:
            smaller_chunks = _split_large_text(
                section_text,
                section_title
            )

            chunks.extend(smaller_chunks)

    return chunks


def _split_pollutants(text):
    """
    Split the KEY POLLUTANTS section into
    one chunk per pollutant.
    """

    pattern = r"(?m)^-\s*([A-Za-z0-9]+(?:\.[A-Za-z0-9]+)?)\s*\((.*?)\):"

    matches = list(re.finditer(pattern, text))

    if not matches:
        return [text.strip()]

    chunks = []

    for index, match in enumerate(matches):

        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

    return chunks


def _split_large_text(text, section_title, max_characters=1800):
    """
    Split a large section into paragraph-based chunks.
    """

    paragraphs = re.split(r"\n\s*\n", text)

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        if not current_chunk:
            current_chunk = paragraph

        elif len(current_chunk) + len(paragraph) + 2 <= max_characters:
            current_chunk += "\n\n" + paragraph

        else:
            chunks.append({
                "text": current_chunk,
                "section": section_title
            })

            current_chunk = paragraph

    if current_chunk:
        chunks.append({
            "text": current_chunk,
            "section": section_title
        })

    return chunks