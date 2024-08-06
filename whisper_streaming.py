import torch
print("CUDA available:", torch.cuda.is_available())

# 필요한 라이브러리 설치
import os
from dotenv import load_dotenv

load_dotenv()

os.system('pip install numpy soundfile scipy librosa sounddevice faster-whisper pyngrok')
os.system('pip install git+https://github.com/openai/whisper.git')
os.system('pip install git+https://github.com/guillaumekln/faster-whisper.git')

# Whisper-Streaming 프로젝트 클론
if not os.path.exists('LingoBell-GPU/whisper_streaming'):
    os.system('git clone https://github.com/ufal/whisper_streaming.git LingoBell-GPU/whisper_streaming')

from pyngrok import ngrok
import subprocess
import threading
import time

# ngrok 인증 토큰 설정
NGROK_AUTH_TOKEN = os.getenv('NGROK_AUTH_TOKEN')
ngrok.set_auth_token(NGROK_AUTH_TOKEN)

# 모든 ngrok 터널 종료
ngrok.kill()

# Whisper-Streaming 서버 실행
server_command = [
    'python3', 'LingoBell-GPU/whisper_streaming/whisper_online_server.py',
    '--model', 'base',
    '--host', '0.0.0.0',
    '--port', '43004',
    '--language', 'auto',
    '--min-chunk-size', '1',
    '--warmup-file', 'LingoBell-GPU/en-demo16.wav'
]

print("Starting Whisper-Streaming server...")

server_process = subprocess.Popen(server_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# ngrok으로 포트 포워딩 설정
public_url = ngrok.connect(43004, "tcp")
print("ngrok URL:", public_url)

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

# 별도의 스레드에서 로그 출력
log_thread = threading.Thread(target=print_log, args=(server_process,))
log_thread.start()

def send_result(self, o):
    msg = self.format_output_transcript(o)
    if msg is not None:
        print("Sending to client:", msg)  # 디버깅 로그
        self.connection.send(msg)

print("Server is running... ngrok URL:", public_url)

# 서버가 종료되지 않도록 유지
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Server stopped.")
    ngrok.disconnect(public_url)
    server_process.terminate()
