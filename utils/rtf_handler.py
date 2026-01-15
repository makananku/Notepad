"""
RTF Handler for Notepad with Pets
Handles RTF export and import with formatting preservation
"""

import re
from typing import Dict, List, Tuple, Optional


class RTFHandler:
    """Handle RTF file format for saving and loading formatted text"""
    
    # RTF header template
    RTF_HEADER = (
        r"{\rtf1\ansi\ansicpg1252\deff0"
        r"{\fonttbl{\f0\fnil\fcharset0 Consolas;}}"
        r"{\colortbl;\red249\green226\blue175;\red166\green227\blue161;"  # yellow, green
        r"\red245\green194\blue231;\red137\green180\blue250;}"  # pink, blue
        r"\viewkind4\uc1\pard\f0\fs22 "
    )
    
    # Color mapping for highlights
    HIGHLIGHT_COLORS = {
        'highlight_yellow': 1,
        'highlight_green': 2,
        'highlight_pink': 3,
        'highlight_blue': 4,
    }
    
    # Font sizes mapping (pt to half-points for RTF)
    FONT_SIZES = {8: 16, 10: 20, 12: 24, 14: 28, 16: 32, 18: 36, 20: 40, 24: 48}
    DEFAULT_SIZE = 22  # 11pt in half-points
    
    @classmethod
    def export_to_rtf(cls, text: str, tags_info: Dict[str, List[Tuple[str, str]]]) -> str:
        """
        Export text with tags to RTF format
        
        Args:
            text: Plain text content
            tags_info: Dictionary mapping tag names to list of (start, end) index tuples
            
        Returns:
            RTF formatted string
        """
        if not text:
            return cls.RTF_HEADER + "}"
        
        # Build a list of formatting changes at each position
        changes = {}  # position -> list of (type, value)
        
        for tag_name, ranges in tags_info.items():
            for start, end in ranges:
                # Convert tkinter indices to character positions
                start_pos = cls._index_to_pos(start, text)
                end_pos = cls._index_to_pos(end, text)
                
                if start_pos is None or end_pos is None:
                    continue
                
                # Add start marker
                if start_pos not in changes:
                    changes[start_pos] = []
                changes[start_pos].append(('start', tag_name))
                
                # Add end marker
                if end_pos not in changes:
                    changes[end_pos] = []
                changes[end_pos].append(('end', tag_name))
        
        # Build RTF content
        rtf_content = []
        active_tags = set()
        
        for i, char in enumerate(text):
            # Process any formatting changes at this position
            if i in changes:
                for change_type, tag_name in changes[i]:
                    if change_type == 'start':
                        rtf_content.append(cls._get_rtf_start(tag_name))
                        active_tags.add(tag_name)
                    else:
                        rtf_content.append(cls._get_rtf_end(tag_name))
                        active_tags.discard(tag_name)
            
            # Add the character (escape special RTF characters)
            rtf_content.append(cls._escape_rtf_char(char))
        
        # Close any remaining tags
        for tag in active_tags:
            rtf_content.append(cls._get_rtf_end(tag))
        
        return cls.RTF_HEADER + ''.join(rtf_content) + "}"
    
    @classmethod
    def import_from_rtf(cls, rtf_content: str) -> Tuple[str, Dict[str, List[Tuple[int, int]]]]:
        """
        Import RTF content and extract text with formatting info
        
        Args:
            rtf_content: RTF formatted string
            
        Returns:
            Tuple of (plain text, dict of tag names to list of (line, col) ranges)
        """
        # Check if this is actually RTF format
        if not rtf_content.strip().startswith('{') or r'{\rtf' not in rtf_content[:100]:
            # Not RTF, return as plain text
            return rtf_content, {}
        
        try:
            # Simple RTF parser - extract text and track formatting
            text_parts = []
            tags_info = {
                'bold': [], 'italic': [], 'underline': [],
                'bold_italic': [], 'bold_underline': [], 'italic_underline': [],
                'bold_italic_underline': [],
                'highlight_yellow': [], 'highlight_green': [],
                'highlight_pink': [], 'highlight_blue': [],
            }
            
            # Add font size tags
            for size in cls.FONT_SIZES.keys():
                tags_info[f'font_{size}'] = []
            
            # Track current state
            is_bold = False
            is_italic = False
            is_underline = False
            current_highlight = None
            current_font_size = None
            
            # Positions for tracking tag ranges
            bold_start = None
            italic_start = None
            underline_start = None
            highlight_start = None
            size_start = None
            
            # Skip RTF header - find \pard which marks start of content
            i = 0
            # Find \pard which typically appears after header
            pard_pos = rtf_content.find(r'\pard')
            if pard_pos != -1:
                # Start parsing after \pard and any following commands
                i = pard_pos + 5  # Skip '\pard'
                # Skip whitespace and font commands like \f0\fs22
                while i < len(rtf_content):
                    if rtf_content[i] in ' \t\n\r':
                        i += 1
                    elif rtf_content[i] == '\\':
                        # Skip control word (like \f0, \fs22)
                        j = i + 1
                        while j < len(rtf_content) and (rtf_content[j].isalnum() or rtf_content[j] == '-'):
                            j += 1
                        i = j
                        # Skip space after control word if present
                        if i < len(rtf_content) and rtf_content[i] == ' ':
                            i += 1
                    else:
                        break
            else:
                # Fallback: try to find first text character after header
                # Look for closing brace of colortbl or fonttbl
                colortbl_end = rtf_content.find('}')
                if colortbl_end != -1:
                    i = colortbl_end + 1
                    # Skip until we find actual content (not control words)
                    while i < len(rtf_content) and (rtf_content[i] in ' \t\n\r{}' or rtf_content[i] == '\\'):
                        if rtf_content[i] == '\\':
                            # Skip control word
                            j = i + 1
                            while j < len(rtf_content) and (rtf_content[j].isalnum() or rtf_content[j] == '-'):
                                j += 1
                            i = j
                            if i < len(rtf_content) and rtf_content[i] == ' ':
                                i += 1
                        else:
                            i += 1
            
            # Parse RTF content
            while i < len(rtf_content):
                if rtf_content[i] == '\\':
                    # Control word
                    j = i + 1
                    while j < len(rtf_content) and rtf_content[j].isalpha():
                        j += 1
                    
                    # Get optional numeric parameter
                    k = j
                    while k < len(rtf_content) and (rtf_content[k].isdigit() or rtf_content[k] == '-'):
                        k += 1
                    
                    word = rtf_content[i+1:j]
                    param = rtf_content[j:k] if j < k else ''
                    
                    current_pos = len(''.join(text_parts))
                    
                    # Handle formatting commands
                    if word == 'b':
                        if param == '0':
                            if is_bold and bold_start is not None:
                                cls._add_style_range(tags_info, 'bold', bold_start, current_pos, is_italic, is_underline)
                            is_bold = False
                            bold_start = None
                        else:
                            is_bold = True
                            bold_start = current_pos
                    elif word == 'i':
                        if param == '0':
                            if is_italic and italic_start is not None:
                                cls._add_style_range(tags_info, 'italic', italic_start, current_pos, is_bold, is_underline)
                            is_italic = False
                            italic_start = None
                        else:
                            is_italic = True
                            italic_start = current_pos
                    elif word == 'ul':
                        is_underline = True
                        underline_start = current_pos
                    elif word == 'ulnone':
                        if is_underline and underline_start is not None:
                            cls._add_style_range(tags_info, 'underline', underline_start, current_pos, is_bold, is_italic)
                        is_underline = False
                        underline_start = None
                    elif word == 'highlight':
                        if current_highlight and highlight_start is not None:
                            tags_info[current_highlight].append((highlight_start, current_pos))
                        
                        color_idx = int(param) if param else 0
                        current_highlight = cls._get_highlight_tag(color_idx)
                        highlight_start = current_pos if current_highlight else None
                    elif word == 'fs':
                        if current_font_size and size_start is not None:
                            tags_info[f'font_{current_font_size}'].append((size_start, current_pos))
                        
                        if param:
                            half_points = int(param)
                            current_font_size = cls._get_font_size(half_points)
                            size_start = current_pos if current_font_size else None
                    elif word == 'par':
                        text_parts.append('\n')
                    elif word == "'":
                        # Hex character
                        if k + 2 <= len(rtf_content):
                            hex_code = rtf_content[k:k+2]
                            try:
                                text_parts.append(chr(int(hex_code, 16)))
                            except:
                                pass
                            k += 2
                    
                    i = k
                    # Skip trailing space after control word
                    if i < len(rtf_content) and rtf_content[i] == ' ':
                        i += 1
                elif rtf_content[i] == '{' or rtf_content[i] == '}':
                    i += 1
                elif rtf_content[i] == '\n' or rtf_content[i] == '\r':
                    i += 1
                else:
                    text_parts.append(rtf_content[i])
                    i += 1
            
            # Close any open tags
            final_pos = len(''.join(text_parts))
            if is_bold and bold_start is not None:
                cls._add_style_range(tags_info, 'bold', bold_start, final_pos, is_italic, is_underline)
            if is_italic and italic_start is not None:
                cls._add_style_range(tags_info, 'italic', italic_start, final_pos, is_bold, is_underline)
            if is_underline and underline_start is not None:
                cls._add_style_range(tags_info, 'underline', underline_start, final_pos, is_bold, is_italic)
            if current_highlight and highlight_start is not None:
                tags_info[current_highlight].append((highlight_start, final_pos))
            if current_font_size and size_start is not None:
                tags_info[f'font_{current_font_size}'].append((size_start, final_pos))
            
            # Convert positions to tkinter indices
            text = ''.join(text_parts)
            converted_tags = {}
            for tag_name, ranges in tags_info.items():
                if ranges:
                    converted_ranges = []
                    for start_pos, end_pos in ranges:
                        start_idx = cls._pos_to_index(start_pos, text)
                        end_idx = cls._pos_to_index(end_pos, text)
                        if start_idx and end_idx:
                            converted_ranges.append((start_idx, end_idx))
                    if converted_ranges:
                        converted_tags[tag_name] = converted_ranges
            
            return text, converted_tags
        except Exception as e:
            # If parsing fails, return empty text or try to extract plain text
            print(f"RTF parsing error: {e}")
            # Try to extract any readable text by removing RTF codes
            import re
            # Remove RTF control words and braces, keep only text
            plain_text = re.sub(r'\\[a-z]+\d*\s?', '', rtf_content)
            plain_text = re.sub(r'[{}]', '', plain_text)
            return plain_text.strip(), {}
    
    @classmethod
    def _add_style_range(cls, tags_info, base_style, start, end, has_other1, has_other2):
        """Add style range, combining with other active styles"""
        # Determine the compound tag name
        styles = []
        if base_style == 'bold' or has_other1 if base_style == 'italic' else has_other2 if base_style == 'underline' else False:
            styles.append('bold')
        if base_style == 'italic' or (has_other1 if base_style != 'italic' else False):
            styles.append('italic')
        if base_style == 'underline' or (has_other2 if base_style != 'underline' else False):
            styles.append('underline')
        
        # Just add to the base style for simplicity
        tags_info[base_style].append((start, end))
    
    @classmethod
    def _index_to_pos(cls, index: str, text: str) -> Optional[int]:
        """Convert tkinter index (line.col) to character position"""
        try:
            parts = index.split('.')
            line = int(parts[0])
            col = int(parts[1])
            
            lines = text.split('\n')
            pos = 0
            for i in range(line - 1):
                if i < len(lines):
                    pos += len(lines[i]) + 1  # +1 for newline
            pos += col
            return pos
        except:
            return None
    
    @classmethod
    def _pos_to_index(cls, pos: int, text: str) -> Optional[str]:
        """Convert character position to tkinter index (line.col)"""
        try:
            line = 1
            col = 0
            for i, char in enumerate(text):
                if i == pos:
                    return f"{line}.{col}"
                if char == '\n':
                    line += 1
                    col = 0
                else:
                    col += 1
            return f"{line}.{col}"
        except:
            return None
    
    @classmethod
    def _get_rtf_start(cls, tag_name: str) -> str:
        """Get RTF control codes for starting a tag"""
        parts = tag_name.split('_')
        
        # Check for font size tags
        if tag_name.startswith('font_'):
            size_str = parts[1] if len(parts) > 1 else ''
            if size_str.isdigit():
                size = int(size_str)
                half_points = cls.FONT_SIZES.get(size, cls.DEFAULT_SIZE)
                rtf = f"\\fs{half_points} "
                # Add style if compound tag
                if 'bold' in tag_name:
                    rtf += "\\b "
                if 'italic' in tag_name:
                    rtf += "\\i "
                if 'underline' in tag_name:
                    rtf += "\\ul "
                return rtf
        
        # Basic style tags
        if tag_name == 'bold':
            return "\\b "
        elif tag_name == 'italic':
            return "\\i "
        elif tag_name == 'underline':
            return "\\ul "
        elif tag_name == 'bold_italic':
            return "\\b\\i "
        elif tag_name == 'bold_underline':
            return "\\b\\ul "
        elif tag_name == 'italic_underline':
            return "\\i\\ul "
        elif tag_name == 'bold_italic_underline':
            return "\\b\\i\\ul "
        elif tag_name in cls.HIGHLIGHT_COLORS:
            color_idx = cls.HIGHLIGHT_COLORS[tag_name]
            return f"\\highlight{color_idx} "
        
        return ""
    
    @classmethod
    def _get_rtf_end(cls, tag_name: str) -> str:
        """Get RTF control codes for ending a tag"""
        parts = tag_name.split('_')
        
        # Check for font size tags
        if tag_name.startswith('font_'):
            rtf = f"\\fs{cls.DEFAULT_SIZE} "
            if 'bold' in tag_name:
                rtf += "\\b0 "
            if 'italic' in tag_name:
                rtf += "\\i0 "
            if 'underline' in tag_name:
                rtf += "\\ulnone "
            return rtf
        
        # Basic style tags
        if tag_name == 'bold':
            return "\\b0 "
        elif tag_name == 'italic':
            return "\\i0 "
        elif tag_name == 'underline':
            return "\\ulnone "
        elif tag_name == 'bold_italic':
            return "\\b0\\i0 "
        elif tag_name == 'bold_underline':
            return "\\b0\\ulnone "
        elif tag_name == 'italic_underline':
            return "\\i0\\ulnone "
        elif tag_name == 'bold_italic_underline':
            return "\\b0\\i0\\ulnone "
        elif tag_name in cls.HIGHLIGHT_COLORS:
            return "\\highlight0 "
        
        return ""
    
    @classmethod
    def _escape_rtf_char(cls, char: str) -> str:
        """Escape special RTF characters"""
        if char == '\\':
            return '\\\\'
        elif char == '{':
            return '\\{'
        elif char == '}':
            return '\\}'
        elif char == '\n':
            return '\\par\n'
        elif ord(char) > 127:
            # Non-ASCII character
            return f"\\u{ord(char)}?"
        return char
    
    @classmethod
    def _get_highlight_tag(cls, color_idx: int) -> Optional[str]:
        """Get highlight tag name from RTF color index"""
        for tag, idx in cls.HIGHLIGHT_COLORS.items():
            if idx == color_idx:
                return tag
        return None
    
    @classmethod
    def _get_font_size(cls, half_points: int) -> Optional[int]:
        """Get font size from RTF half-points value"""
        for size, hp in cls.FONT_SIZES.items():
            if hp == half_points:
                return size
        return None
