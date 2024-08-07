from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from faster_whisper import WhisperModel
import requests
from io import BytesIO
 
app = FastAPI()

# 모델 로드
model = WhisperModel("large-v2", device="cuda", compute_type="float16")

@app.post("/{chat_room_id}/stt")
async def transcribe_audio(chat_room_id: int, file: UploadFile = File(...)):
    try:
        print(f"Received request for chat_room_id: {chat_room_id}")
        print(f"Received file: {file.filename}, Content type: {file.content_type}")
        # 업로드된 파일 읽기
        print(file)
        audio_data = await file.read()
        audio_data = BytesIO(audio_data)
        print("File read successfully")
 
    # STT 처리
        segments, _ = model.transcribe(audio_data, beam_size=5, word_timestamps=True)
        print("STT processing done")
        
        # 텍스트 변환 결과
        text = " ".join([word.word for segment in segments for word in segment.words])
        print(f"Transcription result: {text}")
 
    # 백엔드 서버로 전송
        backend_url = os.getenv('BACKEND_URL')
        response = requests.post(f"{backend_url}/stt", json={"text": text, "chat_room_id": chat_room_id})
        print(f"Sent transcription result to backend: {response.status_code}")
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return {"text": text}
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)