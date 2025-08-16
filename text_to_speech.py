import os
import soundfile as sf
import torch

# Try different models for better Vietnamese TTS
def text_to_speech(text, output_filename="speech.wav"):
    """
    Converts text to speech using Vietnamese TTS models.
    This version tries multiple models for better quality.

    Args:
        text (str): The text to convert to speech.
        output_filename (str): The name of the output audio file.
    """
    # Create directory if it doesn't exist
    output_dir = "audio_chats"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    try:
        # Try Edge TTS first (best quality, requires internet)
        print("🔊 Trying Edge TTS (Microsoft) for Vietnamese...")
        import edge_tts
        import asyncio
        
        async def generate_edge_tts():
            voice = "vi-VN-NamMinhNeural"  # Male Vietnamese voice
            # voice = "vi-VN-HoaiMyNeural"  # Female Vietnamese voice (alternative)
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
        
        # Run the async function
        asyncio.run(generate_edge_tts())
        print(f"✅ Generated with Edge TTS: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Edge TTS failed: {e}")
        print("💡 Trying alternative method...")
        
        try:
            # Fallback to gTTS (Google Text-to-Speech)
            print("🔊 Trying Google TTS...")
            from gtts import gTTS
            
            tts = gTTS(text=text, lang='vi', slow=False)
            tts.save(output_path)
            print(f"✅ Generated with Google TTS: {output_path}")
            return output_path
            
        except Exception as e2:
            print(f"❌ Google TTS failed: {e2}")
            print("💡 Trying local model...")
            
            try:
                # Final fallback to original model
                from transformers import VitsModel, VitsTokenizer, set_seed
                
                print("🔊 Using local VITS model...")
                model = VitsModel.from_pretrained("facebook/mms-tts-vie")
                tokenizer = VitsTokenizer.from_pretrained("facebook/mms-tts-vie")

                inputs = tokenizer(text=text, return_tensors="pt")
                set_seed(555)  # for reproducibility

                with torch.no_grad():
                    outputs = model(**inputs)

                waveform = outputs.waveform.squeeze().numpy()
                sampling_rate = model.config.sampling_rate

                sf.write(output_path, waveform, sampling_rate)
                print(f"⚠️ Generated with local model: {output_path}")
                return output_path
                
            except Exception as e3:
                print(f"❌ All TTS methods failed: {e3}")
                # Create a silence file as last resort
                import numpy as np
                silence = np.zeros(int(22050 * 2))  # 2 seconds of silence
                sf.write(output_path, silence, 22050)
                print(f"⚠️ Created silence file: {output_path}")
                return output_path

if __name__ == "__main__":
    # Test the improved TTS
    test_text = "Xin chào, đây là hệ thống chuyển văn bản thành giọng nói tiếng Việt đã được cải thiện với chất lượng tốt hơn."
    result = text_to_speech(test_text, "test_improved_tts.wav")
    print(f"🎵 Test audio generated: {result}")