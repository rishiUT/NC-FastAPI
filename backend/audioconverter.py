from cgi import test
import os
import glob
from pydub import AudioSegment

def downgrade_audio(filename: str, output: str):
    audio = AudioSegment.from_file(filename)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)
    # simple export
    file_handle = audio.export(output, format="mp3")

def downgrade_dir_mp3(directory: str):
    #directory is the name of the directory, inside the cwd, where the files are stored
    #Requires that the destination directory exists, and has the name "downgraded_" + [directory]

    video_dir = os.getcwd()

    os.chdir(video_dir)
    for filename in os.scandir(directory):
        if filename.is_file():
            if filename.path.endswith('.mp3'):
                connector = "/"
                print(video_dir + connector + filename.path)
                downgrade_audio(video_dir + connector + filename.path, video_dir + connector + "downgraded_" + filename.path)
                print("Copied to ", video_dir + connector + "downgraded_" + filename.path)

#downgrade_dir_mp3("recordings")