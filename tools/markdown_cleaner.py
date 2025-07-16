import re


def clean_escaped_markdown(content):
    """
    Clean escaped markdown syntax from Google Docs' "Download as Markdown" feature.
    
    Google Docs escapes markdown syntax with backslashes, which breaks rendering.
    This function removes those escape characters while preserving legitimate backslashes.
    
    Args:
        content (str): Markdown content with escaped syntax
        
    Returns:
        str: Cleaned markdown content
        
    Examples:
        Before: \\# Header \\- List item \\*emphasis\\* \\1. Numbered list project\\_name
        After:  # Header - List item *emphasis* 1. Numbered list project_name
    """
    if not content:
        return content
    
    # Handle markdown elements in specific order to avoid conflicts
    
    # 1. Headers - handle both with and without spaces after
    content = re.sub(r'\\(#{1,6})\s', r'\1 ', content)  # \# Header with space
    content = re.sub(r'\\(#{1,6})(?=\s|$|\w)', r'\1', content)  # \## Header without space
    
    # 2. Lists (handle both with and without immediate spaces)
    content = re.sub(r'(\d+)\\\.', r'\1.', content)  # Numbered lists - fix escaped periods after numbers
    content = re.sub(r'^\\([-*+])\s', r'\1 ', content, flags=re.MULTILINE)  # Bullet lists at start of line
    
    # 3. Code blocks
    content = re.sub(r'\\(```)', r'\1', content)
    
    # 4. Blockquotes
    content = re.sub(r'\\(>)\s', r'\1 ', content)
    
    # 5. Emphasis/strong - handle escaped asterisks/underscores correctly
    # Handle bold with double asterisks first - improved pattern to handle punctuation and quotes
    content = re.sub(r'\\(\*)\s*\\(\*)([^*\n]*?)\\(\*)\s*\\(\*)', r'\1\2\3\4\5', content)  # \\* \\*bold\\* \\*
    content = re.sub(r'\\(\*)\\(\*)([^*\n]*?)\\(\*)\\(\*)', r'\1\2\3\4\5', content)  # \\*\\*bold\\*\\*
    
    # Handle bold with double underscores
    content = re.sub(r'\\(_)\s*\\(_)([^_\n]+?)\\(_)\s*\\(_)', r'\1\2\3\4\5', content)  # \\_\\_bold\\_\\_
    content = re.sub(r'\\(_)\\(_)([^_\n]+?)\\(_)\\(_)', r'\1\2\3\4\5', content)  # \\_\\_bold\\_\\_
    
    # Handle single emphasis
    content = re.sub(r'\\(\*)([^*\n]+?)\\(\*)', r'\1\2\3', content)  # \\*italic\\*
    content = re.sub(r'\\(_)([^_\n]+?)\\(_)', r'\1\2\3', content)  # \\_italic\\_
    
    # 6. Inline code - handle both cases
    content = re.sub(r'\\(`[^`\n]*?`)\\', r'\1', content)  # \\`code`\\
    content = re.sub(r'\\(`[^`\n]*?`)', r'\1', content)  # \\`code`
    # Clean up any remaining backslashes before backticks
    content = re.sub(r'\\(`)', r'\1', content)
    
    # 7. Strikethrough
    content = re.sub(r'\\(~~)([^~\n]+?)\\(~~)', r'\1\2\3', content)
    
    # 8. Links and images
    content = re.sub(r'\\(\[[^\]]*?\])\\(\([^)]*?\))', r'\1\2', content)  # [text](url)
    content = re.sub(r'\\(!\[[^\]]*?\])\\(\([^)]*?\))', r'\1\2', content)  # ![alt](url)
    
    # 9. Individual escaped characters
    content = re.sub(r'\\([\[\]()])', r'\1', content)  # Brackets and parentheses
    content = re.sub(r'\\(_)(?=[a-zA-Z0-9])', r'\1', content)  # Underscores in words
    content = re.sub(r'\\(\|)', r'\1', content)  # Table separators
    content = re.sub(r'\\(-)', r'\1', content)  # Escaped dashes
    
    # 10. Horizontal rules (after emphasis to avoid conflicts)
    content = re.sub(r'\\(---|___|\*\*\*)', r'\1', content)
    
    # 11. D&D character sheet patterns and special characters
    content = re.sub(r'\\(\+)', r'\1', content)  # Escaped plus signs (common in D&D stats)
    content = re.sub(r'\\(!)', r'\1', content)  # Escaped exclamation marks
    content = re.sub(r'\\(\?)', r'\1', content)  # Escaped question marks
    content = re.sub(r'\\(,)', r'\1', content)  # Escaped commas
    content = re.sub(r'\\(;)', r'\1', content)  # Escaped semicolons
    content = re.sub(r'\\(:)', r'\1', content)  # Escaped colons
    content = re.sub(r'\\(")', r'\1', content)  # Escaped quotes
    content = re.sub(r'\\(\')', r'\1', content)  # Escaped single quotes
    content = re.sub(r'\\(&)', r'\1', content)  # Escaped ampersands (common in D&D)
    
    # 12. Additional cleanup for any remaining escaped special characters that are common in markdown
    content = re.sub(r'\\(\#)', r'\1', content)  # Any remaining escaped hashes
    content = re.sub(r'\\(\*)', r'\1', content)  # Any remaining escaped asterisks
    
    return content