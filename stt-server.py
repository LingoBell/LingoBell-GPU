import torch
print("CUDA available:", torch.cuda.is_available())

# 필요한 라이브러리 설치
import os
from dotenv import load_dotenv

load_dotenv()

import subprocess
import threading
import time

# Whisper-Streaming 서버 실행
server_command = [
    'python3', 'whisper_streaming/whisper_online_server.py',
    '--model', 'base',
    '--host', '0.0.0.0',
    '--port', '43004',
    '--language', 'auto',
    '--min-chunk-size', '1',
    '--warmup-file', 'en-demo16.wav'
]

print("Starting Whisper-Streaming server...")

server_process = subprocess.Popen(server_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# 서버 로그 출력 함수
def print_log(process):
    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            print("Server stopped.")
            break
        if output:
            print("STDOUT:", output.decode('utf-8').strip())
            
    while True:
        error = process.stderr.readline()
        if error == b'' and process.poll() is not None:
            break
        if error:
            print("STDERR:", error.decode('utf-8').strip())
            
def send_result(self, o):
    msg = self.format_output_transcript(o)
    if msg is not None:
        print("Sending to client:", msg)  # 디버깅 로그
        self.connection.send(msg)
        
# 서버가 종료되지 않도록 유지
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Server stopped.")
    server_process.terminate()