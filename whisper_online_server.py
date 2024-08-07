import asyncio
import base64
import io

import socketio
from fastapi import FastAPI
# from faster_whisper import WhisperModel

# Socket.IO 서버 생성
sio = socketio.AsyncServer(async_mode="asgi")
app = FastAPI()
app.mount("/", socketio.ASGIApp(sio))

# model = WhisperModel("large-v2", device="cuda", compute_type="float16")

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def audio(sid, data):
    audio_data = base64.b64decode(data)
    audio_file = io.BytesIO(audio_data)
    # segments, _ = model.transcribe(audio_file, beam_size=5, word_timestamps=True)
    # text = " ".join([word.word for segment in segments for word in segment.words])
    # await sio.emit("transcription", text, to=sid)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
