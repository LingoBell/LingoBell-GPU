#!/usr/bin/env python3

"""Functions for sending and receiving individual lines of text over a socket.

A line is transmitted using one or more fixed-size packets of UTF-8 bytes
containing:

  - Zero or more bytes of UTF-8, excluding \n and \0, followed by

  - Zero or more \0 bytes as required to pad the packet to PACKET_SIZE

Originally from the UEDIN team of the ELITR project. 
"""

PACKET_SIZE = 65536


def send_one_line(socket, text):
    """Sends a line of text over the given socket.

    The 'text' argument should contain a single line of text (line break
    characters are optional). Line boundaries are determined by Python's
    str.splitlines() function [1]. We also count '\0' as a line terminator.
    If 'text' contains multiple lines then only the first will be sent.

    If the send fails then an exception will be raised.

    [1] https://docs.python.org/3.5/library/stdtypes.html#str.splitlines

    Args:
        socket: a socket object.
        text: string containing a line of text for transmission.
    """
    text.replace('\0', '\n')
    lines = text.splitlines()
    first_line = '' if len(lines) == 0 else lines[0]
    # TODO Is there a better way of handling bad input than 'replace'?
    data = first_line.encode('utf-8', errors='replace') + b'\n\0'
    for offset in range(0, len(data), PACKET_SIZE):
        bytes_remaining = len(data) - offset
        if bytes_remaining < PACKET_SIZE:
            padding_length = PACKET_SIZE - bytes_remaining
            packet = data[offset:] + b'\0' * padding_length
        else:
            packet = data[offset:offset+PACKET_SIZE]
        socket.sendall(packet)

import asyncio

async def async_receive_one_line(socket):
    """Receives a line of text from the given WebSocket.

    This function will receive a single line of text. If data is
    currently unavailable, it will block until data becomes available or
    the sender has closed the connection (in which case it will return None).

    The string should not contain any newline characters, but if it does then
    only the first line will be returned.

    Args:
        socket: a WebSocket object.

    Returns:
        A string representing a single line or None if the connection has been closed.
    """
    data = ""  # Initialize as an empty string
    
    while True:
        try:
            packet = await socket.recv()
            print(f"packet의 타입을 찍어보겠다. {type(packet)}")  # 디버깅용 출력
            if not packet:  # Connection closed
                return None
            data += packet  # 문자열로 결합
            print("data도 문자열로 결합됨")
            # print(f"Received packet: {repr(packet)}")
            if '\n' in data or '\0' in data:  # 문자열에서 줄바꿈 또는 널 문자 확인
                print('heyhehehehehe')
                break
        except Exception as e:
            print(f"Error receiving data: {e}")
            return None

    
    # 이제 data는 문자열입니다. '\0' 제거하고, '\n' 기준으로 잘라서 첫 번째 줄을 반환합니다.
    text = data.strip('\0')
    
    lines = text.split('\n')
    return lines[0]  # 첫 번째 줄 반환

def receive_lines(socket):
    try:
        data = socket.recv(PACKET_SIZE)
    except BlockingIOError:
        return []
    if data is None:  # Connection has been closed.
        return None
    # TODO Is there a better way of handling bad input than 'replace'?
    text = data.decode('utf-8', errors='replace').strip('\0')
    lines = text.split('\n')
    if len(lines)==1 and not lines[0]:
        return None
    return lines