from lib import *


def main():
    read_from_file = False
    meeting_minutes = "Default prompt, missing information"
    transcript = "meeting_minutes.txt"
    video_file = "recording.mov"
    prompt_file = "prompt_body.txt"
    audio_file = "recording_16kHz_16bit_mono.wav"

    while True:
        response = input("Read meeting minutes from file? (Y/N): ").strip().upper()
        if response == 'Y' or response == '':
            read_from_file = True
            break
        elif response == 'N':
            read_from_file = False
            break

    if (read_from_file):
        while True:
            transcript = input("Specify meeting minutes file (.txt): ")
            if transcript == '':
                transcript = "meeting_minutes.txt"
            if (os.path.isfile(transcript)):
                with open(transcript, "r") as f:
                    meeting_minutes = f.read()
                break
            else:
                print("Meeting minutes file not found!")
    else:
        while True:
            video_file = input("Specify meeting recording (video file):")
            if video_file == '':
                video_file = "fullrecording.mp4"
            if (os.path.isfile(video_file)):
                convert_meeting_video_to_audio(video_file, audio_file)
                meeting_minutes = transcribe_meeting_audio(audio_file)
                break
            else:
                print("Meeting recording file not found!")

    if meeting_minutes == " " or meeting_minutes == "":
        raise ValueError("Meeting minutes cannot be empty!")

    write_to_file = False
    if not read_from_file:
        while True:
            response = input("Write meeting minutes to file? (Y/N): ").strip().upper()
            if response == 'Y':
                write_to_file = True
            elif response == 'N':
                write_to_file = False
                break
    if write_to_file:
        with open("meeting_minutes.txt", "w") as file:
            file.write(meeting_minutes)
    # Generate BRD

    while True:
        prompt_file = input("Specify prompt file (.txt): ")
        if prompt_file == '':
            prompt_file = "prompt_body.txt"
        if os.path.isfile(prompt_file):
            break
        else:
            print("Prompt file not found!")

    context = load_context()
    brd = generate_brd_from_minutes(meeting_minutes, prompt_file, context)
    context.append(brd)
    cache_context(context)

    with open("brd.txt", "w") as file:
        file.write(brd)

    # Generate and save BRD PDF
    create_brd_pdf(brd, "business_requirements.pdf")
    print("BRD PDF generated successfully as 'business_requirements.pdf'.")


if __name__ == "__main__":
    main()