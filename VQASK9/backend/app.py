from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import cv2
import pyttsx3
import google.generativeai as genai
import mimetypes
import time
import logging
import boto3

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

genai.configure(api_key="AIzaSyDDPpwkg705zJn4ooFoM7jvJWHnRc6JHsc")

engine = pyttsx3.init()
engine.setProperty('rate', 150)

# Initialize Amazon Polly
polly_client = boto3.Session(
    aws_access_key_id='YOUR_AWS_ACCESS_KEY',
    aws_secret_access_key='YOUR_AWS_SECRET_KEY',
    region_name='us-east-1'  # Replace with your actual AWS region
).client('polly')

def speak_text(text):
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Joanna'
    )
    with open('speech.mp3', 'wb') as file:
        file.write(response['AudioStream'].read())
    os.system("mpg321 speech.mp3")  # Or another method to play the mp3 file

def capture_image():
    try:
        os.makedirs("static/captured_images", exist_ok=True)
        cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cam.isOpened():
            logging.error("Error: Could not open camera.")
            return None
        
        logging.info("Camera opened successfully.")
        time.sleep(2)
        
        ret, frame = cam.read()
        if not ret:
            logging.error("Error: Could not read frame.")
            cam.release()
            return None

        logging.info("Frame read successfully.")
        image_path = "static/captured_images/captured_image.jpg"
        cv2.imwrite(image_path, frame)
        cam.release()

        return image_path
    except Exception as e:
        logging.exception("An error occurred while capturing the image.")
        if cam:
            cam.release()
        return None

def get_gemini_response(input_text, image_path):
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File not found: {image_path}")
        
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            raise ValueError("Could not determine the MIME type of the image.")
        model = genai.GenerativeModel('gemini-1.5-flash')
        image_blob = {"mime_type": mime_type, "data": image_data}
        response = model.generate_content([input_text, image_blob])
        return response.text
    except Exception as e:
        logging.exception("An error occurred while getting the Gemini response.")
        raise

@app.route('/speak', methods=['POST'])
def api_speak():
    data = request.json
    text = data.get('text', '')
    speak_text(text)
    return jsonify({"status": "success"})

@app.route('/capture_image', methods=['POST'])
def api_capture_image():
    image_path = capture_image()
    if image_path:
        return jsonify({"image_path": image_path})
    else:
        return jsonify({"error": "Failed to capture image"}), 500

@app.route('/ask_question', methods=['POST'])
def api_ask_question():
    data = request.json
    question = data.get('question', '')
    image_path = data.get('image_path', '')
    try:
        response = get_gemini_response(question, image_path)
        return jsonify({"response": response})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)