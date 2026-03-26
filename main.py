from gtts import gTTS

text = input("Enter the text to convert to audio: ")
tts = gTTS(text)
tts.save('output.mp3')
print("Audio saved as output.mp3")


import cv2
import time

def record_video(duration=5, output_file='output.avi'):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    fps = 20.0
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
    out = cv2.VideoWriter(output_file, fourcc, fps, (frame_width, frame_height))

    start_time = time.time()
    while int(time.time() - start_time) < duration:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        cv2.imshow('Recording...', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Video saved as {output_file}")