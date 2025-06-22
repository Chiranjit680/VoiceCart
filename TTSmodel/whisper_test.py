import os
from whisper import load_model

# Change to script directory
os.chdir(os.path.dirname(__file__))

# Show all files in current directory
print("Files in current directory:")
for file in os.listdir("."):
    print(f"  {file}")
print()

# Load Whisper model
print("Loading Whisper model...")
model = load_model("tiny")

# Audio file to transcribe
audio_path = "testing_audio2.opus"

# Check if file exists
if not os.path.isfile(audio_path):
    raise FileNotFoundError(f"File '{audio_path}' not found!")

# Transcribe audio
print(f"Transcribing '{audio_path}'...")
result = model.transcribe(audio_path)

# Print results
print("\nTranscription:")
print(result["text"])

# Optional: Show confidence and other info
if "segments" in result:
    print(f"\nDetected language: {result.get('language', 'Unknown')}")
    print(f"Number of segments: {len(result['segments'])}")