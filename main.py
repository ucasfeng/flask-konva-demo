import base64
import json
import time

import cv2
import threading
from flask import Flask
import flask
import queue

app = Flask("demo", static_folder="./static", template_folder="./static")
Q1 = queue.Queue(maxsize=50)
QUIT = False


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/event")
def update():
    print("event-stream 连接成功")
    return flask.Response(event_proc(), mimetype="text/event-stream")


def cv2_to_base64(image):
    image1 = cv2.imencode('.jpg', image)[1]
    image_code = str(base64.b64encode(image1))[2:-1]
    return "data:image/jpeg;base64," + image_code


def event_proc():
    while True:
        image = Q1.get(block=True)
        if image is not None:
            code = cv2_to_base64(image)
            yield 'data: {}\n\n'.format(json.dumps(({'image': code})))


def worker_read_video(que: queue.Queue):
    global QUIT
    cap = cv2.VideoCapture("./sample_walk.mov")
    if cap.isOpened() is not True:
        print("cap is not opened")
        return
    frame_num = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cnt = 0
    while QUIT is not True:
        r, f = cap.read()
        if r is not True:
            print("read failed")
            break
        cnt += 1
        if cnt == frame_num:
            cnt = 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        if que.full():
            que.get()
        que.put_nowait(f)
        time.sleep(0.015)
    cap.release()


def worker_flask():
    app.run()


def worker_play(que: queue.Queue):
    global QUIT
    window_name = "test"
    cv2.namedWindow(window_name, 0)
    cv2.resizeWindow(window_name, 800, 600)
    while True:
        f = que.get(block=True)
        if f is not None:
            cv2.imshow(window_name, f)
            if cv2.waitKey(10) & 0xFF == ord('q'):
                QUIT = True
                break
        else:
            print("read image from queue error")
            break
    cv2.destroyWindow(window_name)


if __name__ == '__main__':
    ths = [
        threading.Thread(target=worker_read_video, args=(Q1,)),
        threading.Thread(target=worker_flask)
    ]
    [th.start() for th in ths]
    [th.join() for th in ths]
