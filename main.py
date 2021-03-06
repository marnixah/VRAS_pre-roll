from splash import splash
from moviepy.editor import *
import subprocess
import shutil
import glob
from pathlib import Path
from random import shuffle
import os

# Paths / prefixes
font = "./font.ttf"
magick_convert = ["convert"]
ffmpeg = ["ffmpeg"]
ffprobe = ["ffprobe"]

if os.name == 'nt':
    magick_convert = ["magick"] + magick_convert

# Pre-run checks
def check_dir(dir):
    if not os.path.isdir(dir):
        os.mkdir(dir)
        pass
    pass
check_dir('./tmp')
check_dir('./tmp/splash')
check_dir('./tmp')
check_dir('./tmp/Trailers')
check_dir('./output')
check_dir('./Posters')
check_dir('./Sessions')
check_dir('./Trailers')

# Required programs

def check_program(cmd):
    file = shutil.which(cmd)
    if str(file) == "None":
        sys.exit(cmd + " was not found on your system.")
        pass
    pass

check_program(ffprobe[0])
check_program(ffmpeg[0])
check_program(magick_convert[0])

if not os.path.isfile(font):
    sys.exit("Font " + font + " was not found on your system.")
    pass

def clean_dir(dir):
    files = glob.glob(dir + "/*", recursive=True)
    for file in files:
        try:
            os.remove(file)
        except IsADirectoryError:
            pass
        pass
    pass
clean_dir('./tmp/splash/')
clean_dir('./tmp/Trailers/')
clean_dir('./tmp/')


# Stage 1 generating still frame 
splash().save_frame('./tmp/posters.png')

# Stage 2 Overlaying trailers over still frame
trailers = glob.glob('Trailers/*.mp4')

if len(trailers) == 0:
    sys.exit("Please add trailer in the Trailers directory.")
    pass

for trailer in trailers:
    p = subprocess.Popen(ffmpeg + ["-i", "./tmp/posters.png", "-i", "./{0}".format(trailer), "-c:a","copy", "-filter_complex", "[1:v:0]scale=900:506,setsar=1[a];[0:v:0][a] overlay=1020:574", "-map", "1:a", "-shortest", "-y", "./tmp/{0}".format(trailer)])
    p.wait()
    pass
# Stage 3 generating still frame with current session poster
sessions = glob.glob('Sessions/*')
if len(sessions) == 0:
    sys.exit("Please add sessions in the Sessions directory.")
    pass

for session in sessions:
    poster_array = []
    current = []
    for poster in glob.glob(glob.escape(session) + '/*'):
        p = Path(poster)
        name = p.stem
        current.append(name)
        poster_array.append("./tmp/{}.png".format(name))
        cmd = magick_convert + [poster,"-resize","320x450!","./tmp/{}.png".format(name)]
        p = subprocess.Popen(cmd)
        p.wait()
        pass
    cmd = magick_convert + poster_array + ["+append","./tmp/lineup.png"]
    p = subprocess.Popen(cmd)
    p.wait()

    cmd = magick_convert + ["./tmp/posters.png","-gravity","center","-fill","white","-pointsize","40","-font",font,"-annotate","+480+40","This session:\n" + " & ".join(current), "./tmp/text.png"]
    p = subprocess.Popen(cmd)
    p.wait()

    cmd = magick_convert + ["./tmp/text.png","./tmp/lineup.png", "-gravity","center","-geometry","+480+315","-composite", "./tmp/splash/{}.png".format("+".join(current))]
    p = subprocess.Popen(cmd)
    p.wait()
# Stage 4 concatenating stage 2 + 3

for splash in glob.glob("./tmp/splash/*"):
    concat_list = []
    p = Path(splash)
    current_session = p.stem.split("+")

    cmd = ffmpeg + ["-f","lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-loop", "1", "-i", os.path.realpath(splash), "-c:v", "libx264", "-t", "20", "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080", "-y", "./tmp/splash.mp4"]
    p = subprocess.Popen(cmd)
    p.wait()

    g = glob.glob("./tmp/Trailers/*")
    shuffle(g)
    for trailer in g:
        p = Path(trailer)
        current_trailer = p.stem
        # Don't want to show a trailer of the show that we're currently showing
        if current_trailer in current_session:
            print("Not showing " + current_trailer + " trailer because current session is " + "+".join(current_session))
            continue
        concat_list.append(  trailer.replace("\\","/") )
        concat_list.append( './tmp/splash.mp4') 
        
        pass
    filter=""
    i=0
    length=0
    cmd = ffmpeg
    if len(concat_list) == 0:
        continue
    for video in concat_list:
        filter = filter + "[{0}:v] [{0}:a]".format(i)
        cmd.append("-i")
        cmd.append(video)
        
        process = subprocess.Popen(ffprobe + ["-loglevel", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", video],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = process.communicate()
        length = length + float(out[0])

        i+=1
        
        pass
    filter = filter + " concat=n={0}:v=1:a=1 [b] [a]; [b] drawtext=fontfile={2}:text='%{{eif\\:trunc(mod((({1}-t)/60),60))\\:d\\:2}}\\:%{{eif\\:trunc(mod({1}-t\\,60))\\:d\\:2}}':fontcolor=white:fontsize=72:x=w-tw-10:y=10:box=1:boxcolor=black@0.5:boxborderw=10,format=yuv420p [v]".format(len(concat_list), length, font)
    cmd = cmd + ["-filter_complex",filter,"-map","[v]","-map","[a]","-y","./output/00 {}.mp4".format("+".join(current_session))]
    print(" ".join(cmd))
    p = subprocess.Popen(cmd)
    p.wait()
    pass
