import re
from glob import glob
from pathlib import Path
import configparser
from mutagen.flac import FLAC


def get_files():
    conf = configparser.ConfigParser()
    conf.read("setting.ini", encoding="utf-8")

    try:
        root = conf["DEFAULT"]["MUSIC_ROOT"]
    except KeyError:
        root = str(Path.home()) + '/Music'
    
    files = [p for p in glob(root + '/**/*', recursive=True)
             if re.search('/*\.flac\Z', str(p))]

    artists = dict()
    albums = dict()
    songs = dict()
    for f in files:
        tags = FLAC(f)
        artist = get_attribute(tags, 'albumartist')
        if artist == None:
            artist = get_attribute(tags, 'artist')

        album = get_attribute(tags, 'album')
        title = get_attribute(tags, 'title')
        
        if (artist not in artists) \
           or (artist in artists and album not in artists[artist]):
            artists.setdefault(artist, []).append(album)
            
        if (album not in albums) \
           or (album in albums and album not in albums[album]):
            albums.setdefault(album, []).append(title)
                
        songs.setdefault(title, f)

    return artists, albums, songs


def get_attribute(tags, key):
    try:
        attr = tags[key][-1]
    except KeyError:
        attr = None

    return attr

if __name__ == "__main__":
    print(get_files())
