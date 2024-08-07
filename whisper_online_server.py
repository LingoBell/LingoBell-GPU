import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from faster_whisper import WhisperModel
import requests

app = FastAPI()

# 모델 로드
model = WhisperModel("large-v2", device="cuda", compute_type="float16")

@app.post("/stt")
async def transcribe_audio(chat_room_id: int, file: UploadFile = File(...)):
    try:
        # 업로드된 파일 읽기
        audio_data = await file.read()
        
        # STT 처리
        segments, _ = model.transcribe(audio_data, beam_size=5, word_timestamps=True)
        
        # 텍스트 변환 결과
        text = " ".join([word.word for segment in segments for word in segment.words])
        
        # 백엔드 서버로 전송
        backend_url = os.getenv('BACKEND_URL')
        response = requests.post(f"{backend_url}/stt", json={"text": text, "chat_room_id": chat_room_id})
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)