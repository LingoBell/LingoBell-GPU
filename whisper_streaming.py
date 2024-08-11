import json
import asyncio
import websockets
import logging
import numpy as np
import argparse
import os
import sys
import soundfile
import io
from whisper_online import *

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
        self.last_end = None

    async def process_audio_stream(self, websocket):
        self.online_asr_proc.init()
        while True:
            try:
                data = await websocket.recv()

                if not data:
                    logger.error("Received empty data, skipping processing")
                    continue

                # 수신된 데이터를 wav 형식으로 처리
                audio_wav_io = io.BytesIO(data)
                audio_wav_io.seek(0)
                logger.info(f"Received audio data of size: {len(data)} bytes")

                try:
                    # librosa로 오디오 데이터를 처리합니다.
                    audio_data, _ = librosa.load(audio_wav_io, sr=SAMPLING_RATE, dtype=np.float32)
                    self.online_asr_proc.insert_audio_chunk(audio_data)
                    o = online.process_iter()
                    transcription = self.format_output_transcript(o)
                    
                    if transcription:
                        await websocket.send(transcription)
                except Exception as e:
                    logger.error(f"Error processing audio stream: {str(e)}")
            except websockets.ConnectionClosed:
                break
            except Exception as e:
                logger.error(f"Error processing audio stream: {e}")

    def format_output_transcript(self, o):
        if o[0] is not None:
            beg, end = o[0] * 1000, o[1] * 1000
            if self.last_end is not None:
                beg = max(beg, self.last_end)
            self.last_end = end
            return json.dumps({"transcription": o[2]})
        return None

# WebSocket 서버 처리
async def handle_client(websocket, path):
    processor = ServerProcessor(online_asr_proc=online, min_chunk=min_chunk)
    await processor.process_audio_stream(websocket)

# WebSocket 서버 시작
start_server = websockets.serve(handle_client, args.host, args.port)

logger.info(f"Server started on {args.host}:{args.port}")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
