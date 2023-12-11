import socket
import cv2
import numpy as np

def live_streaming():
    try:
        host = 'IP Address'
        port = PORT

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_socket.bind((host, port))

        server_socket.listen()

        print(f"서버가 {host}:{port}에서 대기 중입니다...")

        client_socket, client_address = server_socket.accept()
        print(f"{client_address}가 연결되었습니다.")

        cap = cv2.VideoCapture(0)

        while True:
            ret, frame = cap.read()

            if not ret:
                continue

            _, img_encoded = cv2.imencode('.jpg', frame)
            data = np.array(img_encoded).tobytes()

            client_socket.sendall((str(len(data))).encode().ljust(16) + data)
    except:
        print("CODE 1000: 스트리밍에 문제가 발생하였습니다.")
        client_socket.close()
        server_socket.close()
        cap.release()


