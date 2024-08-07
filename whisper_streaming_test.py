import socket
import sounddevice as sd
import numpy as np
import threading

# ngrok이 제공한 주소와 포트 설정
server_ip = '8.tcp.ngrok.io'  # ngrok이 제공한 주소로 업데이트하세요
server_port = 19069           # ngrok이 제공한 포트로 업데이트하세요

# 오디오 스트리밍 설정
samplerate = 16000
channels = 1
dtype = np.int16
blocksize = 1024  # 버퍼 크기 설정

# 소켓 연결
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))

print("Connected to server. Streaming audio...")

def receive_transcription():
    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if data:
                print("Transcription:", data)
        except:
            break

# 소켓 연결 후 수신 스레드 시작
receive_thread = threading.Thread(target=receive_transcription)
receive_thread.start()

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    print("Sending audio chunk of size:", len(indata.tobytes()))  # 디버깅 로그
    client_socket.sendall(indata.tobytes())


def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    client_socket.sendall(indata.tobytes())

try:
    with sd.InputStream(samplerate=samplerate, channels=channels, dtype=dtype, 
                        callback=audio_callback, blocksize=blocksize):
        print("Streaming. Press Ctrl+C to stop.")
        sd.sleep(10000000)  # 무한 대기
except KeyboardInterrupt:
    print("Streaming stopped")
finally:
    client_socket.close()
    print("Socket closed")