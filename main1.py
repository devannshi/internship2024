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
    
    Separate each section with two new lines.
    
    What kind of technical stack makes sense for this requirement?

    Assess the accuracy of this Business Requirement Document compared to the meeting minutes on a percentage scale.
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


read_from_file = True
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

# Generate BRD
brd = generate_brd_from_minutes(meeting_minutes)
class BRDTemplate(FPDF):
    def header(self):
        if self.page == 1:
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, "EY Internship 2024 Project 1 Version 7", 0, 1, "C")
            self.cell(0, 10, "Business Requirements", 0, 1, "C")
            self.ln(10)

    def draw_box(self, title, body):
        self.set_font("Arial", "B", 12)
        box_start_y = self.get_y()

        # Draw gray background box for title
        self.set_fill_color(169, 169, 169)  # Light gray color
        self.rect(10, box_start_y, 190, 10, 'F')

        # Draw title text centered over the gray box
        self.set_xy(10, box_start_y + 2)  # Slightly adjust to center vertically
        self.cell(190, 6, title, 0, 1, 'C')

        # Draw content box below the title box
        self.set_xy(10, box_start_y + 12)  # Move down to avoid overlap
        self.set_font("Arial", "", 12)
        self.multi_cell(190, 10, body, border=1)
        self.ln(5)  # Add some space after each box

def create_brd_pdf(brd_text, output_pdf):
    pdf = BRDTemplate()
    pdf.add_page()

    # Extract sections from the BRD text
    sections = brd_text.split("\n\n")
    for section in sections:
        if ":" in section:
            title, body = section.split(":", 1)
            pdf.draw_box(title.strip(), body.strip())

    pdf.output(output_pdf)

# Generate and save BRD PDF
create_brd_pdf(brd, "business_requirements.pdf")
print("BRD PDF generated successfully as 'business_requirements.pdf'.")