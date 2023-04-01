import whisper
import os
import time

models = ["medium", "medium.en", "large"]
for filename in sorted(os.listdir("downgraded_recordings-first-negotiation")):
    filename = "downgraded_recordings-first-negotiation/" + filename
    print(filename)
    for model_text in models:
        print(model_text)
        start = time.time()
        model = whisper.load_model(model_text)
        result = model.transcribe(filename)
        print(result["text"])
        end = time.time()
        print("runtime = ", str(end - start))