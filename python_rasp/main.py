import socket
import threading
import time
import cv2
import numpy as np
import streaming
import serial
import pynmea2
import math
import RPi.GPIO as GPIO
from Motor import Motor

HOST = 'IP Address'
COMMAND_PORT = PORT1
LIVE_STREAMING_PORT = PORT2

socketFlag = False
cur_lat = 0
cur_lon = 0

def handle_client(client_socket, addr):
    global socketFlag
    live_streaming_thread = None

    try:
        print(f'{addr}가 연결되었습니다.')
        socketFlag = True

        gps_thread = threading.Thread(target=send_gps_messages, args=(client_socket,))
        gps_thread.start()

        while socketFlag:
            data = client_socket.recv(1024)
            if not data:
                break
            received_message = data.decode()
            print(f'수신한 데이터: {received_message}')

            response_message = ""

            if received_message == "streaming":
                response_message = "streaming on"
                client_socket.sendall(response_message.encode())
                live_streaming_thread = threading.Thread(target=streaming.live_streaming)
                live_streaming_thread.start()
            elif "moving" in received_message:
                response_message = "moving on"
                client_socket.sendall(response_message.encode())
                move_coordinates_thread = threading.Thread(target=move_coordinates, args=(received_message,))
                move_coordinates_thread.start()
            else:
                response_message = "이해할 수 없는 메시지"
                client_socket.sendall(response_message.encode())
    except socket.error as e:
        print("CODE 2000: 소켓 연결에 문제가 발생하였습니다.")
    except Exception as ex:
        print("CODE 3000: Thread에 문제가 발생하였습니다.")
        print(ex)
    finally:
        socketFlag = False
        if gps_thread.is_alive():
            print("gps_thread.join()")
            gps_thread.join()

        if live_streaming_thread and live_streaming_thread.is_alive():
            print("live_streaming_thread.join()")
            live_streaming_thread.join()

        client_socket.close()


def send_gps_messages(client_socket, interval=5):
    global socketFlag
    global cur_lat
    global cur_lon
    try:
        while socketFlag:
            time.sleep(interval)
            gps_message = get_gps_data()
            formatted_message = f"CurLocation,V01,{gps_message[0]},{gps_message[1]},{gps_message[2]}"
            cur_lat = gps_message[0]
            cur_lon = gps_message[1]

            try:
                client_socket.sendall(formatted_message.encode())
            except BrokenPipeError:
                print("클라이언트 연결이 끊어졌습니다.")
                break
    except Exception as e:
        print("CODE 4000: GPS 전송에 문제가 발생하였습니다.")
    finally:
        client_socket.close()

def parse_gps_data(gps_data):
    try:
        msg = pynmea2.parse(gps_data)

        if isinstance(msg, pynmea2.GGA):
            lat = msg.latitude
            lon = msg.longitude
            alt = msg.altitude

            if lat > 0 and lon > 0:
                return lat, lon, alt

    except pynmea2.ParseError as e:
        pass

def get_gps_data():
    serial_port = "/dev/ttyS0"
    baud_rate = 9600

    with serial.Serial(serial_port, baud_rate, timeout=5) as ser:
        while True:
            gps_data = ser.readline().decode('utf-8')

            gps_info = parse_gps_data(gps_data)
            if gps_info:
                return gps_info

def send_response(client_socket, response_message):
    client_socket.sendall(response_message.encode())

def move_coordinates(received_message):
    global cur_lat
    global cur_lon

    coordinates = received_message.split(',')
    res_lat = coordinates[1]
    res_lon = coordinates[2]

    go_to_coordinates(cur_lat, cur_lon, res_lat, res_lon)

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

def go_to_coordinates(current_lat, current_lon, target_lat, target_lon):
    motor = Motor()
    current_lat = float(current_lat)
    current_lon = float(current_lon)
    target_lat = float(target_lat)
    target_lon = float(target_lon)

    distance_to_target = calculate_distance(current_lat, current_lon, target_lat, target_lon)

    while distance_to_target > 1:
        distance_to_target = calculate_distance(current_lat, current_lon, target_lat, target_lon)

        motor.Car_Run(50, 50)
        time.sleep(1)

    motor.Car_Stop()

if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, COMMAND_PORT))
        server_socket.listen()
        print(f'서버가 연결을 기다립니다... (커맨드 포트: {COMMAND_PORT})')

        try:
            while True:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.start()
        except:
            print("프로그램을 종료합니다.")

