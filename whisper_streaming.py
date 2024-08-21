import json
import asyncio
import websockets
import logging
import numpy as np
import argparse
import os
import sys
import soundfile
import requests
import io
from whisper_online import *
import base64

from openai import OpenAI
openai_client = OpenAI(api_key=openai_api_key)

# Logging 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 파라미터 설정
parser = argparse.ArgumentParser()

# 서버 설정
parser.add_argument("--host", type=str, default='0.0.0.0')
parser.add_argument("--port", type=int, default=38080)
parser.add_argument("--warmup-file", type=str, default="./en-demo16.wav", 
        help="Whisper의 초기 설정을 따뜻하게 유지하기 위한 wav 파일 경로입니다. 예: https://github.com/ggerganov/whisper.cpp/ra>")

# whisper_online 모듈에서 옵션 추가
add_shared_args(parser)
args = parser.parse_args()

# Logging 설정
set_logging(args, logger, other="")

# Whisper 모델 초기 설정
SAMPLING_RATE = 16000
asr, online = asr_factory(args)
if args.vad:
    asr.use_vad()
min_chunk = args.min_chunk_size

# 초기 웜업 파일 처리
if args.warmup_file:
    if os.path.isfile(args.warmup_file):
        a = load_audio_chunk(args.warmup_file, 0, 1)
        asr.transcribe(a)
        logger.info("Whisper is warmed up.")
    else:
        logger.critical("The warm up file is not available.")
        sys.exit(1)
else:
    logger.warning("Whisper is not warmed up. The first chunk processing may take longer.")

class ServerProcessor:
    def __init__(self, online_asr_proc, min_chunk):
        self.online_asr_proc = online_asr_proc
        self.min_chunk = min_chunk
        self.user_processors = {}
        self.last_end = None
        
    def get_or_create_processor(self, user_id, args):
        if user_id not in self.user_processors:
            asr, online = asr_factory(args)
            self.user_processors[user_id] = online
            self.last_end[user_id] = None
        return self.user_processors[user_id]

    async def process_audio_stream(self, websocket, chat_room_id):
        user_id = None
        while True:
            try:
                data = await websocket.recv()
                if isinstance(data, str):
                    try:
                        message = json.loads(data)
                        
                        if message.get("type") == "language":
                            user_id = message.get("userId")
                            logger.info(f"Received userId: {user_id}")
                            logger.info(f"Received language info: {message}")
                            native_language = message.get("nativeLanguage")
                            learning_languages = message.get("learningLanguages")
                            logger.info(f"Native Language: {native_language}")
                            logger.info(f"Learning Languages: {learning_languages}")
                        
                            processor = self.get_or_create_processor(user_id, args)
                            
                        elif message.get("type") == "audio":
                            user_id = message.get("userId")
                            audio_data = base64.b64decode(message.get("blob"))
                            
                            audio_wav_io = io.BytesIO(audio_data)
                            audio_wav_io.seek(0)
                            logger.info(f"Received audio data of size: {len(audio_data)} bytes")

                            try:
                                audio_data, _ = librosa.load(audio_wav_io, sr=SAMPLING_RATE, dtype=np.float32)

                                processor = self.get_or_create_processor(user_id, args)
                                processor.insert_audio_chunk(audio_data)
                                o = processor.process_iter()
                                print(f"process_iter의 반환 값: {o}")
                                
                                transcription = self.format_output_transcript(o, user_id)
                                print("format_output_transcript 실행 되고 난 결과값인 transcription", transcription)

                                if transcription is not None:
                                    if isinstance(transcription, bytes):
                                        transcription = transcription.decode('utf-8')
                                    logger.info(f"Transcription for user {user_id}: {transcription}")
                                    
                                    # 타입 확인 후 WebSocket으로 전송
                                    if isinstance(transcription, str):
                                        await websocket.send(transcription)
                                    else:
                                        logger.error("Transcription is not a string, cannot send via WebSocket.")

                                    self.send_stt_to_backend(user_id, chat_room_id, transcription)
                                    print("🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥process_audio_stream에서 send_stt_to_backend 호출함🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥")
                                else:
                                    print("transcription이 None이여서 send_stt_to_backend 호출되지 않음")
                            except Exception as e:
                                logger.error(f"여기에서 걸림. 가장 안쪽에서 에러: {str(e)}")
                    except Exception as e:
                        logger.error(f"중간에서 걸림. 중간에서 에러 발생: {e}")
            except websockets.ConnectionClosed:
                break
            except Exception as e:
                logger.error(f"가장 바깥에서 걸림. 바깥에서 에러 발생: {e}")

    def format_output_transcript(self, o, user_id):
        print(f"format_output_transcript이 아예 실행 되는지? o의 값: {o}")

        if user_id is None:
            print("user_id가 None입니다. 사용자 ID가 제대로 전달되었는지 확인하세요.")
            return None

        if self.last_end is None:
            print("self.last_end이 초기화되지 않았습니다. 초기화합니다.")
            self.last_end = {}

        if user_id not in self.last_end:
            print(f"🔍 Info: user_id {user_id}가 self.last_end에 존재하지 않습니다. 새로운 항목을 추가합니다.")
            self.last_end[user_id] = None

        if o[0] is not None:
            beg, end = o[0] * 1000, o[1] * 1000
            print(f"시작 시간(beg) = {beg}, 종료 시간(end) = {end}")

            if self.last_end[user_id] is not None:
                beg = max(beg, self.last_end[user_id])
                print(f"last_end가 존재하여 beg 값이 조정되었습니다. 새로운 beg = {beg}")

            self.last_end[user_id] = end
            print(f"user_id {user_id}의 last_end가 {end}으로 업데이트되었습니다.")

            transcription = o[2]
            
            return transcription
        
        print("o[0]이 None입니다. 처리할 수 없습니다.")
        return None

    def send_stt_to_backend(self, user_id, chat_room_id, transcription):
        print("send_stt_to_backend가 실행이 되는지?")
        try:
            payload = {
               "userId": user_id,
               "chatRoomId": chat_room_id,
               "stt_text": transcription
           }
            response = requests.post("http://127.0.0.1:8000/api/chats/pst", json=payload)
            print("백엔드 서버로 잘 보낼 준비가 된 response의 모양은? ", response)
            if response.status_code == 200:
               logger.info(f"STT result successfully sent to backend for user {user_id} in chat room {chat_room_id}")
            else:
               logger.error(f"Failed to send STT result to backend: {response.status_code}")
    
        except Exception as e:
            logger.error(f"Error sending STT result to backend: {e}")

# WebSocket 서버 처리
async def handle_client(websocket, path):
    processor = ServerProcessor(online_asr_proc=online, min_chunk=min_chunk)
    
    # chat_room_id를 경로에서 추출
    chat_room_id = path.lstrip("/ws/")
    
    # processor에 chat_room_id와 함께 websocket을 전달
    await processor.process_audio_stream(websocket, chat_room_id)

# WebSocket 서버 시작
start_server = websockets.serve(handle_client, args.host, args.port)

logger.info(f"Server started on {args.host}:{args.port}")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
