import re
from glob import glob
from pathlib import Path
from mutagen.flac import FLAC


def get_files():
    home = str(Path.home())  # ~は使えない

    # files = [p for p in glob(home + '/Music/**/*', recursive=True)
    #         if re.search('/*\.(flac|wav)\Z', str(p))]

    files = [p for p in glob(home + '/Music/**/*', recursive=True)
             if re.search('/*\.flac\Z', str(p))]

    artists = dict()
    albums = dict()
    songs = dict()
    for f in files:
        artist = FLAC(f)['artist'][-1]
        album = FLAC(f)['album'][-1]
        title = FLAC(f)['title'][-1]
        
        if (artist not in artists) \
           or (artist in artists and album not in artists[artist]):
            artists.setdefault(artist, []).append(album)
            
        if (album not in albums) \
           or (album in albums and album not in albums[album]):
            albums.setdefault(album, []).append(title)
                
        songs.setdefault(title, f)

    return artists, albums, songs
