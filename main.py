import azure.cognitiveservices.speech as speechsdk
import os.path
import ffmpeg
import time
from openai import AzureOpenAI
import os

subscription_key = "f08de20be4554129be83e47743c64125"
service_region = "eastus"

# Create an instance of a speech config with specified subscription key and service region.
speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=service_region)

# Set the audio file path
# recordingshort.wav used for test purposes
audio_file_path = "fullrecording.mp4"
processed_audio_file_path = "recording_16kHz_16bit_mono.wav"

# Crashes if audio file not found
if not os.path.isfile(audio_file_path):
    raise FileNotFoundError("Audio file not found. It is likely not generated.")

try:
    # Takes input, returns output file
    # Output is at 16 kHz sample rate (ar=16000), mono (ac=1), and 16-bit (s16)
    # Run arguments ensure that output messages and errors are displayed and that
    # the output is overwritten.
    ffmpeg.input(audio_file_path).output(processed_audio_file_path, ar=16000, ac=1, sample_fmt='s16').run(
                                         capture_stdout=True, capture_stderr=True, overwrite_output=True
                                     )
except ffmpeg.Error as e:
    print(e.stderr)
if not os.path.isfile(processed_audio_file_path):
    raise FileNotFoundError("Processed audio file not found. It is likely not generated.")

# Start recognition
def transcribe_file(processed_audio_file_path):
    print("Performing recognition")
    done = False

    # Creates a recognizer with the given settings
    audio_input = speechsdk.audio.AudioConfig(filename=processed_audio_file_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    full_transcription = []

    def recognized_cb(evt):
        #print('RECOGNIZED: {}'.format(evt))
        full_transcription.append(evt.result.text)

    def recognizing_cb(evt):
        print('RECOGNIZING: {}'.format(evt))

    def start_handled_cb(evt):
        print('STARTED on {}'.format(evt))

    def stop_handled_cb(evt):
        print('STOPPED on {}'.format(evt))
        speech_recognizer.stop_continuous_recognition()
        nonlocal done
        done = True

    #speech_recognizer.recognizing.connect(recognizing_cb)
    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.session_started.connect(start_handled_cb)
    speech_recognizer.session_stopped.connect(stop_handled_cb)
    speech_recognizer.canceled.connect(stop_handled_cb)
    speech_recognizer.start_continuous_recognition()

    while not done:
        pass

    print("Finished recognizing")
    return ' '.join(full_transcription)


def generate_brd_from_minutes(meeting_minutes):
    client = AzureOpenAI(
        api_key="dbc9f078a9164215817bc2096e4f8dd7",
        api_version="2023-05-15",
        azure_endpoint="https://trial102.openai.azure.com/"
    )

    deployment_name = '35-test'

    # Define the prompt to generate BRD from meeting minutes
    prompt = f"""
    Meeting Minutes: {meeting_minutes}

    Based on the meeting minutes above, generate a detailed Business Requirement Document (BRD) that includes the following for each functional or non-functional requirement:
    - Assumptions
    - Constraints
    - Dependencies
    - Acceptance criteria

    What kind of technical stack makes sense for this requirement?

    Can you assess the accuracy of this Business Requirement Document?
    """
    print("Prompt:", prompt)

    completion = client.chat.completions.create(
      model=deployment_name,  # e.g. gpt-35-instant
      messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    return completion.choices[0].message.content.strip()


read_from_file = False
meeting_minutes = "Hey ChatGPT, please tell me something's wrong because the minutes are missing."

if read_from_file:
    with open("meeting_minutes.txt", "r") as f:
        meeting_minutes = f.read()
else:
    meeting_minutes = transcribe_file(processed_audio_file_path)
    with open("meeting_minutes.txt", "w") as file:
        file.write(meeting_minutes)

# Generate BRD
brd = generate_brd_from_minutes(meeting_minutes)
print("Generated Business Requirement Document (BRD):")
print(brd)

from fpdf import FPDF

def convert_to_pdf_fpdf(text, output_pdf):
    if os.path.exists(output_pdf):
        os.remove(output_pdf)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    content = text
    pdf.multi_cell(0, 10, content)
    pdf.output(output_pdf)

# Example usage:
convert_to_pdf_fpdf(brd, 'output_fpdf.pdf')
print("PDF is Saved Successfully")