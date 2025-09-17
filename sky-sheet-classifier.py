import os
import json
import re
import shutil
from pathlib import Path

class SkyMusicSheetClassifier:
    """
    Classifies Sky music sheets into different format categories based on content analysis.
    
    Supported formats:
    1. Sky Studio JSON (.json/.txt) - Sky Studio mobile app format
    2. Sky Music JSON (.json) - Web-based sky-music.specy.app format  
    3. ABC1-5 Text (.txt) - Traditional Sky notation (A1, B2, C3, etc.)
    4. Jianpu Text (.txt) - Chinese numbered notation (1, 2, 3, 4, 5, 6, 7)
    5. Doremi Text (.txt) - Western solfege notation (do, re, mi, fa, sol, la, ti)
    6. English Text (.txt) - Standard note names (C, D, E, F, G, A, B)
    7. Sky Script Text (.txt) - Simplified key notation (l, j, k, h, etc.)
    8. HTML Sheets (.html) - Visual sheet format from sky-music.github.io
    """
    
    def __init__(self, input_dir, output_base_dir):
        self.input_dir = Path(input_dir)
        self.output_base_dir = Path(output_base_dir)
        self.formats = {
            'sky_studio_json': 'Sky_Studio_JSON_Format',
            'sky_music_json': 'Sky_Music_JSON_Format', 
            'abc15_text': 'ABC1-5_Text_Format',
            'jianpu_text': 'Jianpu_Numbered_Format',
            'doremi_text': 'Doremi_Solfege_Format',
            'english_text': 'English_Notes_Format',
            'sky_script_text': 'Sky_Script_Format',
            'html_sheets': 'HTML_Visual_Sheets',
            'unknown_format': 'Unknown_Format'
        }
        
    def read_file_content(self, file_path, max_chars=2048):
        """Safely read file content with encoding fallback."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    return f.read(max_chars).strip()
            except:
                continue
        return ""
    
    def detect_json_type(self, content, file_path):
        """Detect specific JSON format type."""
        try:
            # Try to parse as JSON
            if content.startswith('['):
                data = json.loads(content[:1000] + ']' if len(content) > 1000 else content)
                if isinstance(data, list) and len(data) > 0:
                    first_item = data[0]
                    if isinstance(first_item, dict):
                        # Sky Studio JSON format markers
                        if 'songNotes' in first_item and 'time' in str(first_item):
                            return 'sky_studio_json'
            else:
                data = json.loads(content[:1000] + '}' if len(content) > 1000 else content)
                if isinstance(data, dict):
                    # Sky Music JSON format markers
                    if any(key in data for key in ['columns', 'instruments', 'isComposed', 'appName']):
                        return 'sky_music_json'
                    # Sky Studio single song format
                    elif 'songNotes' in data and 'bpm' in data:
                        return 'sky_studio_json'
                        
        except json.JSONDecodeError:
            pass
            
        return None
    
    def detect_text_format(self, content):
        """Detect text-based music notation format."""
        content_lower = content.lower()
        lines = content.split('\n')[:20]  # Check first 20 lines
        
        # HTML format detection
        if any(tag in content_lower for tag in ['<html>', '<div', '<body>', 'DOCTYPE']):
            return 'html_sheets'
            
        # Sky Script format detection (key pattern: letters like l, j, k, h, g, f, d, s, a)
        sky_script_pattern = r'[ljkhgfdsa\s\d]+'
        if re.search(r'\b[ljkhgfdsa]{2,}\b', content_lower):
            return 'sky_script_text'
        
        # ABC1-5 format detection (A1, B2, C3, etc.)
        abc_pattern = r'[ABC][1-5]'
        if re.search(abc_pattern, content, re.IGNORECASE):
            abc_matches = len(re.findall(abc_pattern, content, re.IGNORECASE))
            if abc_matches > 3:  # Multiple ABC1-5 notes found
                return 'abc15_text'
        
        # Jianpu format detection (numbered notation 1-7)
        jianpu_pattern = r'\b[1-7]\b'
        if re.search(jianpu_pattern, content):
            # Check for typical Jianpu markers
            jianpu_markers = ['1=', 'bpm', '4/4', '3/4', '2/4']
            if any(marker in content_lower for marker in jianpu_markers):
                return 'jianpu_text'
            # Count standalone numbers 1-7
            jianpu_matches = len(re.findall(jianpu_pattern, content))
            if jianpu_matches > 5:
                return 'jianpu_text'
        
        # Doremi format detection
        doremi_notes = ['do', 're', 'mi', 'fa', 'sol', 'la', 'ti', 'si']
        doremi_count = sum(content_lower.count(note) for note in doremi_notes)
        if doremi_count > 3:
            return 'doremi_text'
        
        # English notation detection (C, D, E, F, G, A, B)
        english_pattern = r'\b[CDEFGAB][#b]?[0-9]?\b'
        english_matches = len(re.findall(english_pattern, content))
        if english_matches > 5:
            return 'english_text'
        
        return None
    
    def classify_file(self, file_path):
        """Classify a single file and return its format."""
        file_path = Path(file_path)
        
        # Skip hidden files and directories
        if file_path.name.startswith('.'):
            return None
            
        content = self.read_file_content(file_path)
        if not content:
            return None
        
        # JSON format detection (works for both .json and .txt files containing JSON)
        json_type = self.detect_json_type(content, file_path)
        if json_type:
            return json_type
        
        # Text format detection
        text_type = self.detect_text_format(content)
        if text_type:
            return text_type
            
        # Fallback based on file extension
        ext = file_path.suffix.lower()
        if ext == '.html':
            return 'html_sheets'
        elif ext in ['.json', '.txt']:
            return 'unknown_format'
        
        return None
    
    def create_output_directories(self):
        """Create output directories for each format."""
        for format_dir in self.formats.values():
            Path(self.output_base_dir / format_dir).mkdir(parents=True, exist_ok=True)
    
    def sort_files(self, copy_files=True):
        """Sort all files in input directory by format."""
        self.create_output_directories()
        
        results = {format_name: [] for format_name in self.formats.values()}
        results['skipped'] = []
        
        for file_path in self.input_dir.rglob('*'):
            if file_path.is_file():
                format_type = self.classify_file(file_path)
                
                if format_type and format_type in self.formats:
                    target_dir = self.output_base_dir / self.formats[format_type]
                    target_path = target_dir / file_path.name
                    
                    # Handle duplicate filenames
                    counter = 1
                    while target_path.exists():
                        stem = file_path.stem
                        suffix = file_path.suffix
                        target_path = target_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    if copy_files:
                        shutil.copy2(file_path, target_path)
                        print(f"Copied: {file_path.name} -> {self.formats[format_type]}/")
                    else:
                        shutil.move(str(file_path), str(target_path))
                        print(f"Moved: {file_path.name} -> {self.formats[format_type]}/")
                    
                    results[self.formats[format_type]].append(file_path.name)
                else:
                    results['skipped'].append(file_path.name)
                    print(f"Skipped: {file_path.name} (unknown format)")
        
        return results
    
    def generate_report(self, results):
        """Generate a classification report."""
        print("\n" + "="*60)
        print("SKY MUSIC SHEET CLASSIFICATION REPORT")
        print("="*60)
        
        total_files = sum(len(files) for files in results.values())
        
        for format_name, files in results.items():
            if files:
                print(f"\n{format_name}: {len(files)} files")
                if len(files) <= 10:
                    for file in files[:10]:
                        print(f"  - {file}")
                else:
                    for file in files[:5]:
                        print(f"  - {file}")
                    print(f"  ... and {len(files)-5} more files")
        
        print(f"\nTOTAL FILES PROCESSED: {total_files}")
        print("="*60)

# Usage example
def main():
    # Configuration - CHANGE THESE PATHS FOR YOUR USE CASE
    input_directory = "input_sheets"  # Replace with your input directory path
    output_directory = "sorted_sky_sheets"  # Replace with desired output path
    
    # Create classifier instance
    classifier = SkyMusicSheetClassifier(input_directory, output_directory)
    
    # Sort files (copy_files=True to copy files, False to move them)
    results = classifier.sort_files(copy_files=True)
    
    # Generate classification report
    classifier.generate_report(results)

if __name__ == "__main__":
    main()