# Run this file separately to test if gTTS works:
# python tts_debug.py

try:
    from gtts import gTTS
    import io
    print("✅ gTTS imported successfully")
    
    # Test Telugu
    tts = gTTS(text="నమస్కారం", lang='te', slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    print("✅ Telugu TTS works! Size:", buf.tell(), "bytes")
    
    # Test Hindi  
    tts2 = gTTS(text="नमस्कार", lang='hi', slow=False)
    buf2 = io.BytesIO()
    tts2.write_to_fp(buf2)
    print("✅ Hindi TTS works! Size:", buf2.tell(), "bytes")
    
    print("\n✅ All good! The /api/tts route should work.")
    
except ImportError:
    print("❌ gTTS not installed! Run: pip install gTTS")
except Exception as e:
    print(f"❌ Error: {e}")
    print("Check your internet connection - gTTS needs internet")
