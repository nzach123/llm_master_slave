import re
import logging
from typing import List, Dict, Optional
from core.specs import ToolCall

logger = logging.getLogger(__name__)

class TagParser:
    """
    A robust state-machine based parser for extracting XML-like tags from LLM output.
    It is designed to be more forgiving than standard XML parsers, specifically handling
    unescaped characters within code blocks.
    """

    def parse_tool_calls(self, text: str) -> List[ToolCall]:
        """
        Parse tool calls from the provided text.

        Args:
            text: The raw output from the LLM.

        Returns:
            A list of ToolCall objects.
        """
        tool_calls = []
        cursor = 0
        length = len(text)

        while cursor < length:
            # Find the next opening tag we care about
            write_match = re.search(r'<write_file\s+path=["\']([^"\']*)["\']\s*>', text[cursor:])
            patch_match = re.search(r'<apply_patch\s+path=["\']([^"\']*)["\']\s*>', text[cursor:])

            # Determine which one comes first
            next_write_idx = write_match.start() + cursor if write_match else float('inf')
            next_patch_idx = patch_match.start() + cursor if patch_match else float('inf')

            if next_write_idx == float('inf') and next_patch_idx == float('inf'):
                break

            if next_write_idx < next_patch_idx:
                # Process write_file
                path = write_match.group(1)
                start_content_idx = next_write_idx + len(write_match.group(0))

                # We need to find the closing tag `</write_file>`
                # BUT, if we encounter another `<write_file` before the closing tag,
                # we assume the first one was unclosed/malformed and we drop it to process the second one.

                end_tag_match = re.search(r'</write_file>', text[start_content_idx:])
                next_start_match = re.search(r'<write_file\s+path=', text[start_content_idx:])

                if end_tag_match:
                    end_content_local_idx = end_tag_match.start()

                    # Check if a new start tag appears BEFORE the closing tag
                    if next_start_match and next_start_match.start() < end_content_local_idx:
                         # Found a start tag before the closing tag.
                         # This means the current tag is likely broken/unclosed.
                         # We abandon the current tag and advance cursor to the *new* start tag.
                         # The main loop will then pick it up.
                         logger.warning(f"Found nested/unclosed <write_file> for {path}. discarding.")
                         cursor = start_content_idx + next_start_match.start()
                         continue

                    # Valid case
                    end_content_idx = start_content_idx + end_content_local_idx
                    content = text[start_content_idx:end_content_idx]

                    tool_calls.append(ToolCall(
                        action="write_file",
                        path=path,
                        content=content.strip()
                    ))

                    cursor = end_content_idx + len("</write_file>")
                else:
                    # No closing tag found at all
                    logger.warning(f"Found <write_file> for {path} but no closing tag.")
                    # If we have another start tag, jump to it. Else finish.
                    if next_start_match:
                         cursor = start_content_idx + next_start_match.start()
                    else:
                         break # No more tags

            else:
                # Process apply_patch
                path = patch_match.group(1)
                start_content_idx = next_patch_idx + len(patch_match.group(0))

                end_tag_match = re.search(r'</apply_patch>', text[start_content_idx:])
                next_start_match = re.search(r'<apply_patch\s+path=', text[start_content_idx:])

                if end_tag_match:
                    end_content_local_idx = end_tag_match.start()

                    if next_start_match and next_start_match.start() < end_content_local_idx:
                        logger.warning(f"Found nested/unclosed <apply_patch> for {path}. discarding.")
                        cursor = start_content_idx + next_start_match.start()
                        continue

                    end_content_idx = start_content_idx + end_content_local_idx
                    full_block_content = text[start_content_idx:end_content_idx]

                    old_content = self._extract_inner_tag(full_block_content, "old")
                    new_content = self._extract_inner_tag(full_block_content, "new")

                    if old_content is not None and new_content is not None:
                         tool_calls.append(ToolCall(
                            action="apply_patch",
                            path=path,
                            content=new_content,
                            old_content=old_content
                        ))
                    else:
                        logger.warning(f"Malformed <apply_patch> for {path}: missing <old> or <new> blocks.")

                    cursor = end_content_idx + len("</apply_patch>")
                else:
                    logger.warning(f"Found <apply_patch> for {path} but no closing tag.")
                    if next_start_match:
                         cursor = start_content_idx + next_start_match.start()
                    else:
                         break

        return tool_calls

    def _extract_inner_tag(self, text: str, tag_name: str) -> Optional[str]:
        """
        Helper to extract content between <tag> and </tag>.
        """
        start_pattern = re.compile(f'<{tag_name}>')
        end_pattern = re.compile(f'</{tag_name}>')

        start_match = start_pattern.search(text)
        if not start_match:
            return None

        start_idx = start_match.end()

        # Similar logic: if we find <old> again before </old>, it's weird, but inner tags
        # usually don't have attributes so it's simpler.
        # But wait, what if the code *contains* <old>?
        # That's the hard part.
        # If the code contains <old>, we rely on the first </old> closing it.
        # This is the "greedy vs non-greedy" issue.
        # A true XML parser would fail.
        # Here we just take the first </old> we find.

        end_match = end_pattern.search(text[start_idx:])

        if not end_match:
            return None

        return text[start_idx : start_idx + end_match.start()]
