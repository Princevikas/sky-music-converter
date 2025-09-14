#!/usr/bin/env python3
"""
Sky Music Converter - Simplified Version
Converts YouTube videos and audio files to Sky: Children of Light music sheets
Clean interface focused on conversion functionality
"""

import os
import sys
import json
import logging
import traceback
import subprocess
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
import threading
import time
import uuid
import platform

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def check_ffmpeg():
    """Check if FFmpeg is installed and provide installation instructions if not"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg is installed and working")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg not found!")
        print("\n🔧 FFmpeg Installation Instructions:")
        
        if platform.system() == "Windows":
            print("1. Download FFmpeg from: https://github.com/BtbN/FFmpeg-Builds/releases")
            print("2. Extract the zip file to C:\\ffmpeg\\")
            print("3. Add C:\\ffmpeg\\bin to your system PATH")
            print("4. Restart your command prompt and try again")
        elif platform.system() == "Darwin":  # macOS
            print("Run: brew install ffmpeg")
        else:  # Linux
            print("Run: sudo apt-get install ffmpeg  (Ubuntu/Debian)")
            print("Or: sudo yum install ffmpeg     (CentOS/RHEL)")
        
        print("\n⚠️  FFmpeg is required for audio processing. Please install it first.")
        return False

def check_and_install_dependencies():
    """Check and install required packages with Python 3.12+ compatibility"""
    dependencies = {
        'numpy': '>=1.26.4',
        'scipy': '>=1.14.0',
        'librosa': '>=0.10.2',
        'yt-dlp': '>=2024.8.6',
        'flask': '>=3.0.0',
        'flask-cors': '>=4.0.0',
        'requests': '>=2.31.0',
        'soundfile': '>=0.12.1',
        'pydub': '>=0.25.1'
    }
    
    print("🔍 Checking Python dependencies...")
    missing_packages = []
    
    for package, version in dependencies.items():
        try:
            if package == 'yt-dlp':
                import yt_dlp
            elif package == 'flask-cors':
                from flask_cors import CORS
            elif package == 'soundfile':
                import soundfile
            elif package == 'pydub':
                from pydub import AudioSegment
            else:
                __import__(package)
            print(f"✅ {package} is available")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} not found")
    
    if missing_packages:
        print(f"📦 Installing missing packages: {', '.join(missing_packages)}")
        for package in missing_packages:
            try:
                version_spec = dependencies[package]
                install_cmd = [sys.executable, '-m', 'pip', 'install', f'{package}{version_spec}']
                subprocess.check_call(install_cmd)
                print(f"✅ Successfully installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {package}: {e}")
                return False
    
    print("✅ All Python dependencies installed!")
    return True

# Check FFmpeg first
if not check_ffmpeg():
    input("\nPress Enter to continue anyway (conversion may fail) or Ctrl+C to exit...")

# Install Python dependencies
if not check_and_install_dependencies():
    sys.exit(1)

# Now import the packages
import numpy as np
import librosa
import yt_dlp
from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
import soundfile as sf
from pydub import AudioSegment

# Global progress tracking
progress_data = {}

class SkyMusicConverter:
    """Sky Music Converter with simplified, robust processing"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "sky_music_converter"
        self.output_dir = Path("output")
        self.create_directories()
        
        # Sky Music note mapping (15-key layout)
        self.sky_notes = {
            'A1': {'freq': 261.63, 'row': 0, 'col': 0},  # C4
            'A2': {'freq': 293.66, 'row': 0, 'col': 1},  # D4
            'A3': {'freq': 329.63, 'row': 0, 'col': 2},  # E4
            'A4': {'freq': 369.99, 'row': 0, 'col': 3},  # F#4
            'A5': {'freq': 415.30, 'row': 0, 'col': 4},  # G#4
            
            'B1': {'freq': 466.16, 'row': 1, 'col': 0},  # A#4
            'B2': {'freq': 523.25, 'row': 1, 'col': 1},  # C5
            'B3': {'freq': 587.33, 'row': 1, 'col': 2},  # D5
            'B4': {'freq': 659.25, 'row': 1, 'col': 3},  # E5
            'B5': {'freq': 739.99, 'row': 1, 'col': 4},  # F#5
            
            'C1': {'freq': 830.61, 'row': 2, 'col': 0},  # G#5
            'C2': {'freq': 932.33, 'row': 2, 'col': 1},  # A#5
            'C3': {'freq': 1046.50, 'row': 2, 'col': 2}, # C6
            'C4': {'freq': 1174.66, 'row': 2, 'col': 3}, # D6
            'C5': {'freq': 1318.51, 'row': 2, 'col': 4}  # E6
        }
        
        self.note_frequencies = [note['freq'] for note in self.sky_notes.values()]
        self.note_names = list(self.sky_notes.keys())
    
    def create_directories(self):
        """Create necessary directories"""
        self.temp_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        logger.info("📁 Directories created")
    
    def update_progress(self, job_id: str, percent: int, message: str, details: str = ""):
        """Update progress for a specific job"""
        progress_data[job_id] = {
            'percent': percent,
            'message': message,
            'details': details,
            'timestamp': time.time()
        }
        logger.info(f"Progress {job_id}: {percent}% - {message}")
    
    def download_youtube_audio(self, url: str, job_id: str) -> str:
        """Download audio from YouTube with enhanced compatibility"""
        try:
            self.update_progress(job_id, 5, "Initializing YouTube downloader", "Setting up yt-dlp with enhanced headers")
            
            output_path = self.temp_dir / f"audio_{int(time.time())}"
            
            # Enhanced yt-dlp options for better compatibility
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(output_path) + '.%(ext)s',
                'noplaylist': True,
                'extractaudio': True,
                'audioformat': 'wav',
                'audioquality': '192K',
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Encoding': 'gzip,deflate',
                    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                    'Connection': 'keep-alive'
                },
                'extractor_retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
            }
            
            self.update_progress(job_id, 10, "Extracting video information", "Fetching metadata and available formats")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First, extract info
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                self.update_progress(job_id, 20, f"Found: {title}", f"Duration: {duration//60}:{duration%60:02d}, Starting download...")
                
                # Now download
                ydl.download([url])
            
            self.update_progress(job_id, 60, "Download completed", "Processing downloaded file")
            
            # Find the downloaded file and convert to WAV
            downloaded_files = list(self.temp_dir.glob(f"audio_{int(time.time())-5}*"))
            if not downloaded_files:
                # Try broader search
                downloaded_files = list(self.temp_dir.glob("audio_*"))
            
            if not downloaded_files:
                raise FileNotFoundError("No audio file found after download")
            
            input_file = downloaded_files[-1]  # Get the most recent
            wav_path = input_file.with_suffix('.wav')
            
            self.update_progress(job_id, 70, "Converting to WAV format", f"Converting {input_file.suffix} to WAV for analysis")
            
            try:
                # Use pydub to convert to WAV
                audio = AudioSegment.from_file(str(input_file))
                audio.export(str(wav_path), format="wav")
                
                # Remove original file
                if input_file != wav_path:
                    input_file.unlink()
                
                return str(wav_path)
                
            except Exception as e:
                self.update_progress(job_id, 0, "Audio conversion failed", f"FFmpeg error: {str(e)}")
                raise Exception(f"Audio conversion failed. Please ensure FFmpeg is installed: {str(e)}")
            
        except Exception as e:
            self.update_progress(job_id, 0, "Download failed", f"Error: {str(e)}")
            logger.error(f"YouTube download failed: {e}")
            raise
    
    def analyze_audio(self, audio_path: str, job_id: str) -> Tuple[np.ndarray, np.ndarray, float]:
        """Advanced audio analysis with improved pitch detection"""
        try:
            self.update_progress(job_id, 75, "Loading audio file", "Reading audio data with librosa")
            
            # Load audio with librosa
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            audio_duration = len(y) / sr
            
            self.update_progress(job_id, 80, "Analyzing audio properties", f"Loaded {audio_duration:.1f}s of audio at {sr}Hz sample rate")
            
            # Enhanced pitch detection using pYIN algorithm
            self.update_progress(job_id, 85, "Detecting pitches with AI", "Using pYIN algorithm for accurate pitch detection")
            
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y, 
                fmin=librosa.note_to_hz('C4'), 
                fmax=librosa.note_to_hz('C7'),
                sr=sr,
                frame_length=2048,
                hop_length=512,
                threshold=0.1,
                resolution=0.1
            )
            
            self.update_progress(job_id, 88, "Filtering pitch data", "Removing unreliable pitch detections")
            
            # Remove NaN values and keep only confident pitches
            valid_indices = ~np.isnan(f0) & (voiced_probs > 0.7)
            if not np.any(valid_indices):
                raise ValueError("No reliable pitches detected in audio. Try with a clearer musical recording.")
                
            pitches = f0[valid_indices]
            
            self.update_progress(job_id, 92, "Analyzing tempo", "Detecting beats and calculating BPM")
            
            # Calculate tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            
            # Time alignment
            hop_length = 512
            times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)
            valid_times = times[valid_indices]
            
            self.update_progress(job_id, 95, "Analysis complete", f"Found {len(pitches)} pitch points, tempo: {tempo:.1f} BPM")
            
            logger.info(f"Detected {len(pitches)} pitch points, tempo: {tempo:.1f} BPM")
            return pitches, valid_times, float(tempo)
            
        except Exception as e:
            self.update_progress(job_id, 0, "Analysis failed", f"Error: {str(e)}")
            logger.error(f"Audio analysis failed: {e}")
            raise
    
    def pitch_to_sky_note(self, frequency: float) -> str:
        """Convert frequency to Sky Music note"""
        if frequency <= 0 or np.isnan(frequency):
            return None
            
        # Find closest Sky note
        freq_ratios = np.array([abs(np.log2(frequency / note_freq)) 
                               for note_freq in self.note_frequencies])
        closest_idx = np.argmin(freq_ratios)
        
        # Only accept if within reasonable range (±50 cents)
        if freq_ratios[closest_idx] < 0.5:
            return self.note_names[closest_idx]
        
        return None
    
    def convert_to_sky_sheet(self, pitches: np.ndarray, times: np.ndarray, 
                           tempo: float, title: str, job_id: str) -> Dict:
        """Convert analyzed audio to Sky Music sheet format"""
        try:
            self.update_progress(job_id, 96, "Converting to Sky Music format", "Mapping frequencies to Sky's 15-key system")
            
            # Convert pitches to Sky notes
            sky_notes = []
            processed_count = 0
            
            for pitch, time in zip(pitches, times):
                note = self.pitch_to_sky_note(pitch)
                if note:
                    sky_notes.append({
                        'note': note,
                        'time': float(time),
                        'duration': 0.5
                    })
                
                processed_count += 1
                if processed_count % 100 == 0:
                    progress = 96 + int((processed_count / len(pitches)) * 2)
                    self.update_progress(job_id, progress, f"Processing notes: {processed_count}/{len(pitches)}", f"Converted {len(sky_notes)} valid notes so far")
            
            if not sky_notes:
                raise ValueError("No valid Sky notes detected. The audio may not contain recognizable musical pitches.")
            
            self.update_progress(job_id, 98, "Optimizing note sequence", "Grouping chords and removing duplicates")
            
            # Group notes by time proximity (chord detection)
            processed_notes = []
            i = 0
            while i < len(sky_notes):
                current_time = sky_notes[i]['time']
                chord_notes = [sky_notes[i]['note']]
                
                # Look for notes within 0.1 seconds (chord)
                j = i + 1
                while j < len(sky_notes) and sky_notes[j]['time'] - current_time < 0.1:
                    chord_notes.append(sky_notes[j]['note'])
                    j += 1
                
                # Remove duplicates and sort
                chord_notes = sorted(list(set(chord_notes)))
                
                processed_notes.append({
                    'time': current_time,
                    'notes': chord_notes,
                    'duration': 0.5
                })
                
                i = j
            
            self.update_progress(job_id, 99, "Generating JSON output", "Creating Sky Music compatible format")
            
            # Create Sky Music JSON format
            sky_sheet = {
                "name": title,
                "author": "Sky Music Converter",
                "transcribedBy": "AI Converter v2",
                "bpm": int(tempo),
                "bitsPerPage": 16,
                "pitchLevel": 0,
                "isComposed": True,
                "isEncrypted": False,
                "songNotes": []
            }
            
            # Convert to Sky Music note format
            for note_group in processed_notes:
                if len(note_group['notes']) == 1:
                    # Single note
                    sky_sheet["songNotes"].append({
                        "key": note_group['notes'][0],
                        "time": note_group['time']
                    })
                else:
                    # Chord - add as simultaneous notes
                    for note in note_group['notes']:
                        sky_sheet["songNotes"].append({
                            "key": note,
                            "time": note_group['time']
                        })
            
            self.update_progress(job_id, 100, "Conversion complete!", f"Generated {len(sky_sheet['songNotes'])} notes in Sky Music format")
            
            logger.info(f"Generated {len(sky_sheet['songNotes'])} notes")
            return sky_sheet
            
        except Exception as e:
            self.update_progress(job_id, 0, "Conversion failed", f"Error: {str(e)}")
            logger.error(f"Conversion failed: {e}")
            raise
    
    def save_sheet(self, sheet_data: Dict, filename: str) -> str:
        """Save Sky Music sheet to file"""
        output_path = self.output_dir / f"{filename}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sheet_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Sheet saved to: {output_path}")
        return str(output_path)
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                    except Exception:
                        pass  # Ignore files in use
            logger.info("🧹 Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

# Flask Web Application
app = Flask(__name__)
CORS(app)

converter = SkyMusicConverter()

# Simplified, clean HTML template focused on conversion
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sky Music Converter</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 3rem;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #fff, #f0f8ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
            max-width: 500px;
            margin: 0 auto;
        }

        .converter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }

        .converter-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 2rem;
            transition: all 0.3s ease;
        }

        .converter-card:hover {
            transform: translateY(-3px);
            background: rgba(255, 255, 255, 0.15);
        }

        .card-title {
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .input-group {
            margin-bottom: 1.5rem;
        }

        .input-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .input-field {
            width: 100%;
            padding: 1rem;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .input-field::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }

        .input-field:focus {
            outline: none;
            border-color: rgba(255, 255, 255, 0.8);
            background: rgba(255, 255, 255, 0.2);
        }

        .file-input-wrapper {
            position: relative;
            cursor: pointer;
            width: 100%;
        }

        .file-input {
            position: absolute;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }

        .file-input-display {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100px;
            border: 2px dashed rgba(255, 255, 255, 0.5);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
            text-align: center;
        }

        .file-input-wrapper:hover .file-input-display {
            border-color: rgba(255, 255, 255, 0.8);
            background: rgba(255, 255, 255, 0.1);
        }

        .convert-btn {
            width: 100%;
            padding: 1rem;
            background: linear-gradient(45deg, #ff6b6b, #ff8e53);
            color: white;
            border: none;
            border-radius: 50px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .convert-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(255, 107, 107, 0.3);
        }

        .convert-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .progress-container {
            display: none;
            margin-top: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 1.5rem;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 1rem;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4facfe, #00f2fe);
            width: 0%;
            transition: width 0.3s ease;
        }

        .progress-text {
            font-weight: 600;
            margin-bottom: 0.5rem;
        }

        .progress-details {
            font-size: 0.9rem;
            opacity: 0.8;
        }

        .result-container {
            display: none;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            margin-top: 2rem;
            text-align: center;
        }

        .result-success {
            border: 2px solid #4CAF50;
        }

        .result-error {
            border: 2px solid #f44336;
        }

        .download-btn {
            display: inline-block;
            padding: 1rem 2rem;
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 600;
            transition: all 0.3s ease;
            margin-top: 1rem;
        }

        .download-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(76, 175, 80, 0.3);
        }

        .info-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 2rem;
            margin-top: 2rem;
        }

        .info-section h3 {
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }

        .info-section ul {
            list-style: none;
            padding-left: 0;
        }

        .info-section li {
            margin-bottom: 0.5rem;
            padding-left: 1.5rem;
            position: relative;
        }

        .info-section li::before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #4CAF50;
            font-weight: bold;
        }

        .ffmpeg-warning {
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.5);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 2rem;
            text-align: center;
        }

        @media (max-width: 768px) {
            .converter-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .container {
                padding: 20px 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 Sky Music Converter</h1>
            <p>Convert YouTube videos and audio files to Sky: Children of the Light music sheets</p>
        </div>

        <div class="ffmpeg-warning">
            <strong>⚠️ Important:</strong> FFmpeg must be installed for audio processing. 
            <a href="https://ffmpeg.org/download.html" target="_blank" style="color: #fff; text-decoration: underline;">
                Download FFmpeg here
            </a>
        </div>

        <div class="converter-grid">
            <!-- YouTube Converter -->
            <div class="converter-card">
                <h3 class="card-title">🎬 YouTube to Sky Music</h3>
                
                <div class="input-group">
                    <label for="youtube-url">YouTube URL</label>
                    <input type="url" 
                           id="youtube-url" 
                           class="input-field"
                           placeholder="https://www.youtube.com/watch?v=..."
                           required>
                </div>
                
                <div class="input-group">
                    <label for="youtube-title">Song Title (optional)</label>
                    <input type="text" 
                           id="youtube-title" 
                           class="input-field"
                           placeholder="Enter song title...">
                </div>
                
                <button onclick="convertYoutube()" 
                        class="convert-btn" 
                        id="youtube-btn">
                    Convert YouTube Video
                </button>
                
                <div class="progress-container" id="youtube-progress">
                    <div class="progress-text" id="youtube-progress-text">Initializing...</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="youtube-progress-fill"></div>
                    </div>
                    <div class="progress-details" id="youtube-progress-details">Preparing to start...</div>
                </div>
            </div>

            <!-- File Upload Converter -->
            <div class="converter-card">
                <h3 class="card-title">🎵 Audio File to Sky Music</h3>
                
                <div class="input-group">
                    <label>Upload Audio File</label>
                    <div class="file-input-wrapper">
                        <input type="file" 
                               id="audio-file" 
                               class="file-input"
                               accept=".mp3,.wav,.m4a,.flac,.ogg"
                               onchange="handleFileSelect(event)">
                        <div class="file-input-display" id="file-display">
                            <div>
                                <div style="font-size: 2rem; margin-bottom: 10px;">📁</div>
                                <div>Click to select audio file</div>
                                <div style="font-size: 0.9rem; opacity: 0.7; margin-top: 5px;">
                                    MP3, WAV, M4A, FLAC, OGG
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="input-group">
                    <label for="file-title">Song Title (optional)</label>
                    <input type="text" 
                           id="file-title" 
                           class="input-field"
                           placeholder="Enter song title...">
                </div>
                
                <button onclick="convertFile()" 
                        class="convert-btn" 
                        id="file-btn"
                        disabled>
                    Convert Audio File
                </button>
                
                <div class="progress-container" id="file-progress">
                    <div class="progress-text" id="file-progress-text">Initializing...</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="file-progress-fill"></div>
                    </div>
                    <div class="progress-details" id="file-progress-details">Preparing to start...</div>
                </div>
            </div>
        </div>

        <div class="result-container" id="result-container">
            <div id="result-content"></div>
        </div>

        <div class="info-section">
            <h3>🎼 Sky Music Format</h3>
            <p>This converter generates JSON files compatible with:</p>
            <ul>
                <li>Sky Music Nightly</li>
                <li>Sky Studio (mobile app)</li>
                <li>Sky Music (web app)</li>
                <li>Other Sky music tools</li>
            </ul>
            
            <h3 style="margin-top: 1.5rem;">🔧 Requirements</h3>
            <ul>
                <li>Python 3.12+ with required packages (auto-installed)</li>
                <li>FFmpeg for audio processing</li>
                <li>Clear musical audio for best results</li>
            </ul>
        </div>
    </div>

    <script>
        let progressIntervals = {};

        function handleFileSelect(event) {
            const file = event.target.files[0];
            const display = document.getElementById('file-display');
            const btn = document.getElementById('file-btn');
            
            if (file) {
                display.innerHTML = `
                    <div>
                        <div style="font-size: 2rem; margin-bottom: 10px;">🎵</div>
                        <div><strong>${file.name}</strong></div>
                        <div style="font-size: 0.9rem; opacity: 0.7; margin-top: 5px;">
                            ${(file.size / 1024 / 1024).toFixed(2)} MB
                        </div>
                    </div>
                `;
                btn.disabled = false;
            } else {
                display.innerHTML = `
                    <div>
                        <div style="font-size: 2rem; margin-bottom: 10px;">📁</div>
                        <div>Click to select audio file</div>
                        <div style="font-size: 0.9rem; opacity: 0.7; margin-top: 5px;">
                            MP3, WAV, M4A, FLAC, OGG
                        </div>
                    </div>
                `;
                btn.disabled = true;
            }
        }

        function updateProgress(type, percent, text, details) {
            const fill = document.getElementById(`${type}-progress-fill`);
            const textEl = document.getElementById(`${type}-progress-text`);
            const detailsEl = document.getElementById(`${type}-progress-details`);
            
            fill.style.width = percent + '%';
            textEl.textContent = text;
            detailsEl.textContent = details || '';
        }

        function showProgress(type) {
            document.getElementById(`${type}-progress`).style.display = 'block';
            document.getElementById(`${type}-btn`).disabled = true;
        }

        function hideProgress(type) {
            document.getElementById(`${type}-progress`).style.display = 'none';
            document.getElementById(`${type}-btn`).disabled = false;
            if (progressIntervals[type]) {
                clearInterval(progressIntervals[type]);
                delete progressIntervals[type];
            }
        }

        function startProgressPolling(type, jobId) {
            progressIntervals[type] = setInterval(async () => {
                try {
                    const response = await fetch(`/progress/${jobId}`);
                    const data = await response.json();
                    
                    if (data.percent !== undefined) {
                        updateProgress(type, data.percent, data.message, data.details);
                        
                        if (data.percent >= 100) {
                            clearInterval(progressIntervals[type]);
                            delete progressIntervals[type];
                        }
                    }
                } catch (error) {
                    console.error('Progress polling error:', error);
                }
            }, 500);
        }

        function showResult(success, message, downloadUrl = null) {
            const container = document.getElementById('result-container');
            const content = document.getElementById('result-content');
            
            container.className = 'result-container ' + (success ? 'result-success' : 'result-error');
            container.style.display = 'block';
            
            let html = `
                <div style="font-size: 3rem; margin-bottom: 1rem;">
                    ${success ? '✅' : '❌'}
                </div>
                <h3>${success ? 'Conversion Successful!' : 'Conversion Failed'}</h3>
                <p style="margin: 1rem 0;">${message}</p>
            `;
            
            if (success && downloadUrl) {
                html += `<a href="${downloadUrl}" class="download-btn" download>📥 Download Sky Music Sheet</a>`;
            }
            
            content.innerHTML = html;
        }

        async function convertYoutube() {
            const url = document.getElementById('youtube-url').value.trim();
            const title = document.getElementById('youtube-title').value.trim() || 'YouTube Song';
            
            if (!url) {
                alert('Please enter a YouTube URL');
                return;
            }
            
            const jobId = 'yt_' + Date.now();
            showProgress('youtube');
            startProgressPolling('youtube', jobId);
            updateProgress('youtube', 1, 'Starting conversion...', 'Initializing YouTube converter');
            
            try {
                const response = await fetch('/convert/youtube', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url, title, job_id: jobId })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    updateProgress('youtube', 100, 'Conversion complete!', `Successfully generated ${result.notes_count} notes`);
                    setTimeout(() => {
                        showResult(true, `Successfully converted "${result.title}" to Sky Music format! Generated ${result.notes_count} notes.`, result.download_url);
                        hideProgress('youtube');
                    }, 1000);
                } else {
                    showResult(false, result.error || 'An error occurred during conversion');
                    hideProgress('youtube');
                }
            } catch (error) {
                showResult(false, 'Network error: ' + error.message);
                hideProgress('youtube');
            }
        }

        async function convertFile() {
            const fileInput = document.getElementById('audio-file');
            const title = document.getElementById('file-title').value.trim() || 'Audio File';
            
            if (!fileInput.files[0]) {
                alert('Please select an audio file');
                return;
            }
            
            const jobId = 'file_' + Date.now();
            showProgress('file');
            startProgressPolling('file', jobId);
            updateProgress('file', 1, 'Starting conversion...', 'Preparing to upload file');
            
            const formData = new FormData();
            formData.append('audio', fileInput.files[0]);
            formData.append('title', title);
            formData.append('job_id', jobId);
            
            try {
                const response = await fetch('/convert/file', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    updateProgress('file', 100, 'Conversion complete!', `Successfully generated ${result.notes_count} notes`);
                    setTimeout(() => {
                        showResult(true, `Successfully converted "${result.title}" to Sky Music format! Generated ${result.notes_count} notes.`, result.download_url);
                        hideProgress('file');
                    }, 1000);
                } else {
                    showResult(false, result.error || 'An error occurred during conversion');
                    hideProgress('file');
                }
            } catch (error) {
                showResult(false, 'Network error: ' + error.message);
                hideProgress('file');
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/progress/<job_id>')
def get_progress(job_id):
    """Get progress for a specific job"""
    if job_id in progress_data:
        return jsonify(progress_data[job_id])
    else:
        return jsonify({'percent': 0, 'message': 'Job not found', 'details': ''})

@app.route('/convert/youtube', methods=['POST'])
def convert_youtube():
    try:
        data = request.get_json()
        url = data.get('url')
        title = data.get('title', 'YouTube Song')
        job_id = data.get('job_id', str(uuid.uuid4()))
        
        logger.info(f"Converting YouTube URL: {url}")
        converter.update_progress(job_id, 1, "Starting YouTube conversion", "Initializing converter")
        
        # Download audio
        audio_path = converter.download_youtube_audio(url, job_id)
        
        # Analyze audio
        pitches, times, tempo = converter.analyze_audio(audio_path, job_id)
        
        # Convert to Sky Music
        sheet_data = converter.convert_to_sky_sheet(pitches, times, tempo, title, job_id)
        
        # Save sheet
        safe_filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        output_path = converter.save_sheet(sheet_data, safe_filename)
        
        # Cleanup
        converter.cleanup_temp_files()
        
        return jsonify({
            'success': True,
            'title': title,
            'download_url': f'/download/{Path(output_path).name}',
            'notes_count': len(sheet_data['songNotes'])
        })
        
    except Exception as e:
        logger.error(f"YouTube conversion failed: {e}")
        converter.cleanup_temp_files()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/convert/file', methods=['POST'])
def convert_file():
    try:
        audio_file = request.files.get('audio')
        title = request.form.get('title', 'Audio File')
        job_id = request.form.get('job_id', str(uuid.uuid4()))
        
        if not audio_file:
            return jsonify({'success': False, 'error': 'No audio file provided'}), 400
        
        logger.info(f"Converting uploaded file: {audio_file.filename}")
        converter.update_progress(job_id, 1, "Starting file conversion", f"Processing {audio_file.filename}")
        
        # Save uploaded file temporarily
        temp_path = converter.temp_dir / f"upload_{int(time.time())}.{audio_file.filename.split('.')[-1]}"
        audio_file.save(str(temp_path))
        
        converter.update_progress(job_id, 10, "File uploaded", "Converting to WAV format if needed")
        
        # Convert to WAV if needed
        if temp_path.suffix.lower() != '.wav':
            wav_path = temp_path.with_suffix('.wav')
            try:
                audio = AudioSegment.from_file(str(temp_path))
                audio.export(str(wav_path), format="wav")
                temp_path.unlink()
                temp_path = wav_path
            except Exception as e:
                raise Exception(f"Audio conversion failed. Please ensure FFmpeg is installed: {str(e)}")
        
        # Analyze audio
        pitches, times, tempo = converter.analyze_audio(str(temp_path), job_id)
        
        # Convert to Sky Music
        sheet_data = converter.convert_to_sky_sheet(pitches, times, tempo, title, job_id)
        
        # Save sheet
        safe_filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        output_path = converter.save_sheet(sheet_data, safe_filename)
        
        # Cleanup
        converter.cleanup_temp_files()
        
        return jsonify({
            'success': True,
            'title': title,
            'download_url': f'/download/{Path(output_path).name}',
            'notes_count': len(sheet_data['songNotes'])
        })
        
    except Exception as e:
        logger.error(f"File conversion failed: {e}")
        converter.cleanup_temp_files()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = converter.output_dir / filename
        if file_path.exists():
            return send_file(str(file_path), as_attachment=True)
        else:
            return "File not found", 404
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return "Download failed", 500

def main():
    print("="*60)
    print("🎵 SKY MUSIC CONVERTER - Simplified Version")
    print("="*60)
    print("🚀 Starting Sky Music Converter...")
    print("📁 Creating directories...")
    
    # Create converter instance
    global converter
    converter = SkyMusicConverter()
    
    print("✅ Setup complete!")
    print("🌐 Starting web server...")
    print("📍 Open your browser and go to: http://localhost:5000")
    print("💡 Features:")
    print("   • Convert YouTube videos to Sky Music sheets")
    print("   • Upload and convert audio files") 
    print("   • Real-time progress tracking")
    print("   • Clean, focused interface")
    print("⚠️  Make sure FFmpeg is installed for audio processing!")
    print("⏹️  Press Ctrl+C to stop the server")
    print("="*60)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        converter.cleanup_temp_files()

if __name__ == '__main__':
    main()