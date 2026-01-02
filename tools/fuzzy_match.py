import difflib
import logging

logger = logging.getLogger(__name__)

def fuzzy_patch(original_content: str, search_block: str, replace_block: str, threshold: float = 0.9) -> tuple[str, bool]:
    """
    Attempts to apply a patch using fuzzy matching if exact match fails.

    Args:
        original_content: The content of the file.
        search_block: The code block to search for.
        replace_block: The code block to replace with.
        threshold: The similarity threshold (0.0 to 1.0) required to apply the patch.

    Returns:
        tuple[str, bool]: (Modified content, Success boolean)
    """
    if search_block in original_content:
        return original_content.replace(search_block, replace_block, 1), True

    # If exact match fails, try fuzzy matching
    lines = original_content.splitlines(keepends=True)
    search_lines = search_block.splitlines(keepends=True)

    # We will try to find the best matching block of lines
    n_search = len(search_lines)
    best_ratio = 0.0
    best_index = -1

    matcher = difflib.SequenceMatcher(None, search_block, "")

    # Sliding window search (naive but functional for small-medium blocks)
    # Ideally we'd match line-by-line using SequenceMatcher on the list of lines,
    # but a simple block comparison might suffice for now if blocks are small.
    # Let's use line-based matching for better accuracy with whitespace.

    for i in range(len(lines) - n_search + 1):
        window = "".join(lines[i:i+n_search])
        matcher.set_seq2(window)
        ratio = matcher.ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            best_index = i

    if best_ratio >= threshold:
        logger.info(f"Fuzzy match found with confidence {best_ratio:.2f}")
        # Replace the lines
        lines[best_index : best_index + n_search] = [replace_block + ("\n" if not replace_block.endswith("\n") and i < len(lines)-1 else "")]
        # Note: Handling newlines in replace_block vs original lines is tricky.
        # Ideally replace_block should just be inserted.
        # Let's re-join carefully.

        # Simpler approach: construct the new string
        pre_match = "".join(lines[:best_index])
        post_match = "".join(lines[best_index + n_search:])

        # Ensure replace_block has consistent newline ending if needed
        # But we trust the LLM output usually.

        return pre_match + replace_block + post_match, True

    logger.warning(f"Fuzzy patch failed. Best match confidence: {best_ratio:.2f}")
    return original_content, False
