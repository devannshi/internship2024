import azure.cognitiveservices.speech as speechsdk
import os.path
import ffmpeg
from openai import AzureOpenAI
import os
import json
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from fpdf import FPDF
import json

# Define PDF template class
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

def follow_up(areas_lacking, client, deployment_name):
    resolution = []
    for i in areas_lacking:
        print("The following area has insufficient information for the document: ", i)
        print("Please input more information required for generating the BRD")
        r = input()
        resolution.append(r)

    prompt_file = "prompt_followup.txt"
    if not os.path.isfile(prompt_file):
        raise FileNotFoundError

    with open(prompt_file, "r") as f:
        prompt_body = f.read()

    prompt = f"""
        Request: {prompt_body}
        """
    for i in range(0, len(resolution)):
        prompt += f"""\n {areas_lacking[i]}: {resolution[i]}"""

    completion = client.chat.completions.create(
        model=deployment_name,  # e.g. gpt-35-instant
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    text = completion.choices[0].message.content.strip()
    return text

def generate_brd_from_minutes(meeting_minutes, prompt_file="prompt_body.txt", context=[]):
    client = AzureOpenAI(
        api_key="dbc9f078a9164215817bc2096e4f8dd7",
        api_version="2023-05-15",
        azure_endpoint="https://trial102.openai.azure.com/",
        temperature="0.0"
    )

    deployment_name = '35-test'

    prompt_body = ""
    if not os.path.isfile(prompt_file):
        raise FileNotFoundError

    with open(prompt_file, "r") as f:
        prompt_body = f.read()

    # Define the prompt to generate BRD from meeting minutes
    # Disabled the context because it was just causing issues with tokenization
    # The json-file is constantly added to, so when the content is read and used in the prompt
    # it quickly exceeds the max token length
    prompt = f"""
    Meeting Minutes: {meeting_minutes}
    
    Request: {prompt_body}
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
    text = completion.choices[0].message.content.strip()
    jsontext = ""
    areas_lacking = []
    try:
        jsontext = json.loads(text)
        insuf_inf = jsontext['INSUFFICIENT_INFORMATION']
        for i in insuf_inf:
            areas_lacking.append(i)
        text = follow_up(areas_lacking, client, deployment_name)
    except ValueError:
        print("No issues found in text")
        pass
    except KeyError:
        print("Error in parsing as a JSON")
        pass

    return text

# Function to cache context
def cache_context(context, cache_file="context_cache.json"):
    if os.path.exists(cache_file):
        os.remove(cache_file)
    with open(cache_file, "w") as f:
        json.dump(context, f)

# Function to load cached context
def load_context(cache_file="context_cache.json"):
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)
    return []

# Function to check if all key points are covered in BRD
def verify_brd(transcript, brd):
    # Initialize Sentence Transformer model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    transcript_sentences = transcript.split(". ")
    brd_sentences = brd.split(". ")
    transcript_embeddings = model.encode(transcript_sentences)
    brd_embeddings = model.encode(brd_sentences)
    similarity_matrix = cosine_similarity(transcript_embeddings, brd_embeddings)
    covered_points = [max(row) > 0.7 for row in similarity_matrix]
    return all(covered_points), covered_points


def create_brd_pdf(brd_text, output_pdf):
    pdf = BRDTemplate()
    pdf.add_page()
    sections = brd_text.split("\n\n")
    for section in sections:
        if ":" in section:
            title, body = section.split(":", 1)
            pdf.draw_box(title.strip(), body.strip())
    pdf.output(output_pdf)

# Converts video file to audio. No return, side effects on disk.
# Takes video file path and desired audio file path
def convert_meeting_video_to_audio(video_file, audio_file):
    # Crashes if audio file not found
    if not os.path.isfile(video_file):
        raise FileNotFoundError("Video file not found. It is likely not generated.")

    try:
        # Takes input, returns output file
        # Output is at 16 kHz sample rate (ar=16000), mono (ac=1), and 16-bit (s16)
        # Run arguments ensure that output messages and errors are displayed and that
        # the output is overwritten.
        ffmpeg.input(video_file).output(audio_file, ar=16000, ac=1, sample_fmt='s16').run(
            capture_stdout=True, capture_stderr=True, overwrite_output=True
        )
    except ffmpeg.Error as e:
        print(e.stderr)
    if not os.path.isfile(audio_file):
        raise FileNotFoundError("Processed audio file not found. It is likely not generated.")

def transcribe_meeting_audio(audio_file):
    subscription_key = "f08de20be4554129be83e47743c64125"
    service_region = "eastus"

    # Create an instance of a speech config with specified subscription key and service region.
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=service_region)

    done = False

    # Creates a recognizer with the given settings
    audio_input = speechsdk.audio.AudioConfig(filename=audio_file)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    full_transcription = []

    def recognized_cb(evt):
        # print('RECOGNIZED: {}'.format(evt))
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

    # speech_recognizer.recognizing.connect(recognizing_cb)
    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.session_started.connect(start_handled_cb)
    speech_recognizer.session_stopped.connect(stop_handled_cb)
    speech_recognizer.canceled.connect(stop_handled_cb)
    speech_recognizer.start_continuous_recognition()

    while not done:
        pass

    print("Finished recognizing")
    return ' '.join(full_transcription)
