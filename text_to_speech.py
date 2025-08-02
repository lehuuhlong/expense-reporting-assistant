import os

import soundfile as sf
import torch
from transformers import VitsModel, VitsTokenizer, set_seed


def text_to_speech(text, output_filename="speech.wav"):
    """
    Converts text to speech using the HuggingFace VITS model for Vietnamese.

    Args:
        text (str): The text to convert to speech.
        output_filename (str): The name of the output audio file.
    """
    # Create directory if it doesn't exist
    output_dir = "audio_chats"
    os.makedirs(output_dir, exist_ok=True)

    # Use Vietnamese model
    model = VitsModel.from_pretrained("facebook/mms-tts-vie")
    tokenizer = VitsTokenizer.from_pretrained("facebook/mms-tts-vie")

    inputs = tokenizer(text=text, return_tensors="pt")

    set_seed(555)  # for reproducibility

    with torch.no_grad():
        outputs = model(**inputs)

    waveform = outputs.waveform.squeeze().numpy()
    sampling_rate = model.config.sampling_rate

    output_path = os.path.join(output_dir, output_filename)
    sf.write(output_path, waveform, sampling_rate)
    return output_path


if __name__ == "__main__":
    text_to_speech(
        "Xin chào, đây là một bài kiểm tra hệ thống chuyển văn bản thành giọng nói."
    )
