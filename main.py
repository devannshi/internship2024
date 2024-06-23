from lib import *


def main():
    read_from_file = False
    meeting_minutes = "Default prompt, missing information"
    transcript = "meeting_minutes.txt"
    video_file = "recording.mov"
    audio_file = "recording_16kHz_16bit_mono.wav"

    while True:
        video_file = input("Specify meeting recording (video file):")
        if (os.path.isfile(video_file)):
            convert_meeting_video_to_audio(video_file, audio_file)
            meeting_minutes = transcribe_meeting_audio(audio_file)
            break
        else:
            print("Meeting recording file not found!")

    if meeting_minutes == " " or meeting_minutes == "":
        raise ValueError("Meeting minutes cannot be empty!")

    with open("meeting_minutes.txt", "w") as file:
        file.write(meeting_minutes)

    print("Transcribed meeting minutes:")
    print(meeting_minutes)

    proceed = False
    while True:
        response = input("Proceed with making a BRD from these minutes? (Y/N): ").strip().upper()
        if response == 'Y':
            proceed = True
            break
        elif response == 'N':
            proceed = False
            break
    if not proceed:
        return

    # Generate BRD
    context = load_context()
    brd = generate_brd_from_minutes(meeting_minutes, context)
    context.append(brd)
    cache_context(context)

    with open("brd.txt", "w") as file:
        file.write(brd)

    # Generate and save BRD PDF
    create_brd_pdf(brd, "business_requirements.pdf")
    print("BRD PDF generated successfully as 'business_requirements.pdf'.")


if __name__ == "__main__":
    main()