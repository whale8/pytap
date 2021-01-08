import re
from glob import glob
from pathlib import Path
import configparser
from mutagen.flac import FLAC


def get_music_tree():
    conf = configparser.ConfigParser()
    #conf.read("setting.ini", encoding="utf-8")

    try:
        root = conf["DEFAULT"]["MUSIC_ROOT"]
    except KeyError:
        root = str(Path.home()) + '/Music'

    files = [p for p in glob(root + '/**/*', recursive=True)
             if re.search('/*\.flac\Z', str(p))]

    music_tree = dict()
    
    for f in files:
        tags = FLAC(f)
        artist = get_attribute(tags, 'albumartist')
        if artist == None:
            artist = get_attribute(tags, 'artist')

        album = get_attribute(tags, 'album')
        title = get_attribute(tags, 'title')
        # タグに設定されていない場合 None

        music_tree.setdefault(artist, dict())\
                  .setdefault(album, dict())\
                  .setdefault(title, f)


    return music_tree


def get_attribute(tags, key):
    try:
        attr = tags[key]
        if isinstance(attr, list):
            attr = tags[key][-1]
        elif isinstance(attr, str):
            pass
        else:
            raise TypeError
    except KeyError:
        attr = None

    return attr

if __name__ == "__main__":
    from pprint import pprint
    music_tree = get_music_tree()
    pprint(music_tree)
