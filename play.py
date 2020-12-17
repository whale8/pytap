import pydub
from pydub.playback import play
from pathlib import Path


home = str(Path.home())  # ~は使えない

file_name = home + "/Music/大貫妙子＆坂本龍一/UTAU/03 - 大貫妙子＆坂本龍一 - ３びきのくま.flac"
seg = pydub.AudioSegment.from_file(file_name, format='flac')
play(seg)
