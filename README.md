# 🎵 Sky Music Converter

Convert YouTube videos and audio files to Sky: Children of the Light music sheets with AI-powered pitch detection.

![Sky Music Converter](https://img.shields.io/badge/version-2.0-blue) ![Python](https://img.shields.io/badge/python-3.12+-green) ![License](https://img.shields.io/badge/license-MIT-yellow)

## ✨ Features

- **🎬 YouTube Integration**: Download and convert YouTube videos directly
- **🎵 Audio File Support**: Upload MP3, WAV, M4A, FLAC, OGG files
- **🤖 Advanced AI Analysis**: Uses cutting-edge pitch detection algorithms
- **⚡ Real-time Processing**: Live progress tracking with detailed step information
- **🎼 Perfect Sky Format**: Generates JSON files compatible with Sky Music apps
- **🌟 Modern UI**: Beautiful web interface inspired by Sky Music Nightly
- **📱 Responsive Design**: Works on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/YOUR_USERNAME/sky-music-converter.git
cd sky-music-converter
```

2. **Run the application**:
```bash
python sky_music_converter_v2.py
```

The script will automatically:
- ✅ Check for missing dependencies
- ✅ Install everything needed (librosa, yt-dlp, flask, etc.)
- ✅ Start the web server
- ✅ Open at http://localhost:5000

### Usage

1. **Open your browser** and go to `http://localhost:5000`
2. **Choose conversion type**:
   - **YouTube**: Paste a YouTube URL
   - **File Upload**: Select an audio file from your computer
3. **Enter song title** (optional)
4. **Click Convert** and watch real-time progress
5. **Download** your Sky Music JSON file

## 🎹 Sky Music Format

The converter generates JSON files compatible with:
- Sky Music Nightly
- Sky Studio (mobile app)
- Sky Music (web app)
- Other Sky music tools

### 15-Key Layout Mapping
```
A1  A2  A3  A4  A5
B1  B2  B3  B4  B5  
C1  C2  C3  C4  C5
```

## 🔧 Technical Details

### Dependencies
- **numpy** (≥1.26.4): Numerical computing
- **scipy** (≥1.14.0): Scientific computing
- **librosa** (≥0.10.2): Audio analysis
- **yt-dlp** (≥2024.8.6): YouTube downloading
- **flask** (≥3.0.0): Web framework
- **pydub**: Audio file handling

### Algorithms Used
- **pYIN**: Advanced pitch detection algorithm
- **Beat tracking**: Tempo analysis
- **Frequency mapping**: Convert Hz to Sky notes
- **Chord detection**: Group simultaneous notes

## 🐛 Troubleshooting

### Common Issues

**YouTube 403 Forbidden Error**:
- Update yt-dlp: `pip install -U yt-dlp`
- Try different video URLs
- Check if video is region-restricted

**Python 3.12 Compatibility Issues**:
- The script automatically handles compatibility
- All dependencies are pinned to compatible versions

**Audio Analysis Fails**:
- Ensure audio file is not corrupted
- Try converting file to WAV format first
- Check that audio contains musical content

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 🙏 Acknowledgments

- **Sky: Children of the Light** by thatgamecompany
- **Sky Music Nightly** community
- **librosa** team for audio analysis tools
- **yt-dlp** developers for YouTube integration

## ⚠️ Disclaimer

This is a fan-made tool and is not affiliated with thatgamecompany. Sky: Children of the Light is a trademark of thatgamecompany.

## 🌟 Star This Repository

If you find this tool helpful, please consider starring the repository to help others discover it!

---

**Made with ❤️ for the Sky: Children of the Light community**