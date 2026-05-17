from whisper_utils import transcribe_audio

# 测试第一条录音
text, _ = transcribe_audio("test_audio_1.wav")
print("识别结果：", text)