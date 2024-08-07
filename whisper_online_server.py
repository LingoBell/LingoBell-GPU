import asyncio
import base64
import io

import socketio
from fastapi import FastAPI
from fastapi_socketio import SocketManager
from starlette.middleware.cors import CORSMiddleware

from faster_whisper import WhisperModel

# Socket.IO 서버 생성
sio = socketio.AsyncServer(async_mode="asgi",logger=True)
app = FastAPI()
app.mount("/", socketio.ASGIApp(sio))
# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://admin.socket.io", '*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# model = WhisperModel("large-v2", device="cuda", compute_type="float16")

@sio.event
async def connect(sid, environ):
    print(f'A user connected: {sid}')

@sio.event
async def disconnect(sid):
    print(f'User disconnected: {sid}')
    await sio.emit('OPP_DISCONNECTED', room=sid)


@sio.event
async def audio(sid, data):
    audio_data = base64.b64decode(data)
    audio_file = io.BytesIO(audio_data)
    segments, _ = model.transcribe(audio_file, beam_size=5, word_timestamps=True)
    text = " ".join([word.word for segment in segments for word in segment.words])
    await sio.emit("transcription", text, to=sid)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=38080)
