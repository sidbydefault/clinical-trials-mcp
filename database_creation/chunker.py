import re
from typing import Dict, List

class ClinicalTrialChunker:
    """Extract structured clinical sections using simple regex patterns."""

    DEFAULT_SECTIONS = {
        'title': '',
        'inclusion': '',
        'exclusion': '',
        'conditions': '',
        'locations': '',
        'interventions': '',
        'primary_outcomes': '',
        'secondary_outcomes': '',
    }

    def __init__(self, text: str, max_length: int = 4096):
        if not text:
            raise ValueError("Document text cannot be empty")
        self.text = text
        self.max_length = max_length
        self.sections = dict(self.DEFAULT_SECTIONS)

    def parse(self) -> Dict[str, str]:
        """Parse document into key clinical sections."""
        lines = self.text.split('\n')
        
        if lines:
            self.sections['title'] = lines[0].replace('Title: ', '').replace('Title:', '').strip()

        # Eligibility
        eligibility = self._extract_between('Eligibility:', 'Conditions:')
        if eligibility:
            self.sections['inclusion'] = self._extract_between('Inclusion Criteria:', 'Exclusion Criteria:', eligibility)
            self.sections['exclusion'] = self._extract_between('Exclusion Criteria:', None, eligibility)

        # Standard sections
        self.sections['conditions'] = self._extract_between('Conditions:', 'Locations:')
        self.sections['locations'] = self._extract_between('Locations:', 'Interventions:')
        self.sections['interventions'] = self._extract_between('Interventions:', 'Outcomes:')

        # Outcomes
        outcomes = self._extract_between('Outcomes:', None)
        if outcomes:
            self._extract_outcomes(outcomes)

        return self.sections

    def _extract_between(self, start: str, end: str = None, text: str = None) -> str:
        """Extract text between markers."""
        source = text if text is not None else self.text
        
        if start not in source:
            return ""
        
        start_idx = source.index(start) + len(start)
        
        if end and end in source[start_idx:]:
            end_idx = source.index(end, start_idx)
            return source[start_idx:end_idx].strip()
        
        return source[start_idx:].strip()

    def _extract_outcomes(self, text: str):
        """Extract outcomes as lists for intelligent chunking."""
        pattern = r'-\s*(PRIMARY|SECONDARY):\s*(.+?)(?=\s*-\s*(?:PRIMARY|SECONDARY):|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        primary = []
        secondary = []
        
        for outcome_type, content in matches:
            content = content.strip()
            if content:
                if outcome_type == 'PRIMARY':
                    primary.append(content)
                else:
                    secondary.append(content)
        
        # Store as LISTS not strings! Important for chunking
        self.sections['primary_outcomes'] = primary
        self.sections['secondary_outcomes'] = secondary

    def create_chunks(self) -> List[Dict[str, str]]:
        """Generate semantic chunks."""
        if not self.sections:
            self.parse()
        
        chunks = []
        title = self.sections['title']

        # Overview - split properly if too long
        overview_text = f"Title: {title}\nConditions: {self.sections['conditions']}"
        
        if len(overview_text) <= self.max_length:
            chunks.append({
                'text': overview_text
            })
        else:
            # Title as separate chunk
            chunks.append({
                'text': f"Title: {title}"
            })
            
            # Split conditions properly (not truncate!)
            if self.sections['conditions']:
                self._split_long(chunks, "Conditions", self.sections['conditions'])

        # Add standard sections
        self._add_chunk(chunks, 'inclusion', 'Inclusion Criteria')
        self._add_chunk(chunks, 'exclusion', 'Exclusion Criteria')
        self._add_chunk(chunks, 'locations', 'Locations')
        self._add_chunk(chunks, 'interventions', 'Interventions')
        
        # Handle outcomes specially (they're lists!)
        self._add_outcome_chunks(chunks, 'primary_outcomes', 'Primary Outcomes')
        self._add_outcome_chunks(chunks, 'secondary_outcomes', 'Secondary Outcomes')

        return chunks

    def _add_chunk(self, chunks: List, section_key: str, section_label: str):
        """Add a section chunk with splitting if needed."""
        data = self.sections.get(section_key)
        if not data:
            return

        title = self.sections['title']
        base_text = f"Title: {title}\n{section_label}: {data}"
        
        if len(base_text) <= self.max_length:
            chunks.append({
                'text': base_text
            })
        else:
            self._split_long(chunks, section_label, data)

    def _add_outcome_chunks(self, chunks: List, section_key: str, section_label: str):
        """Add outcome chunks - intelligently group multiple outcomes."""
        outcomes = self.sections.get(section_key)
        if not outcomes or not isinstance(outcomes, list):
            return
        
        title = self.sections['title']
        header = f"Title: {title}\n{section_label}:\n"
        header_len = len(header)
        
        current_chunk_outcomes = []
        current_length = header_len
        
        for outcome in outcomes:
            outcome_text = f"  - {outcome}\n"
            outcome_len = len(outcome_text)
            
            # Check if adding this outcome exceeds limit
            if current_length + outcome_len > self.max_length and current_chunk_outcomes:
                # Save current chunk
                chunk_text = header + ''.join(current_chunk_outcomes)
                chunks.append({
                    'text': chunk_text
                })
                # Start new chunk
                current_chunk_outcomes = [outcome_text]
                current_length = header_len + outcome_len
            else:
                current_chunk_outcomes.append(outcome_text)
                current_length += outcome_len
        
        # Add remaining outcomes
        if current_chunk_outcomes:
            chunk_text = header + ''.join(current_chunk_outcomes)
            chunks.append({
                'text': chunk_text
            })

    def _split_long(self, chunks: List, label: str, content: str):
        """Split long section into multiple chunks by words."""
        title = self.sections['title']
        header = f"Title: {title}\n{label}: "
        header_len = len(header)
        remaining = self.max_length - header_len
        
        if remaining <= 100:
            # Not enough space
            chunks.append({
                'text': header + content[:100]
            })
            return

        # Split by words to avoid cutting mid-word
        words = content.split()
        current_words = []
        current_length = 0

        for word in words:
            word_len = len(word) + 1  # +1 for space
            
            if current_length + word_len > remaining and current_words:
                # Save current chunk
                chunks.append({
                    'text': header + ' '.join(current_words)
                })
                # Start new chunk
                current_words = [word]
                current_length = word_len
            else:
                current_words.append(word)
                current_length += word_len

        # Add remaining words
        if current_words:
            chunks.append({
                'text': header + ' '.join(current_words)
            })
