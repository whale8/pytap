import os
import re
from glob import glob
import configparser
from mutagen.flac import FLAC


class MusicFileNotFoundError(Exception):
    """setting.iniに書いたディレクトリに音楽ファイルがない場合"""
    pass


def get_music_tree():

    music_tree = dict()
    ini = "./setting.ini"
    
    if not os.path.exists(ini):
        raise FileNotFoundError(f"{ini}が見つかりません．")
    
    conf = configparser.ConfigParser()
    conf.read(ini, encoding="utf-8")

    try:
        root = conf["DEFAULT"]["MUSIC_ROOT"]
    except KeyError:
        raise KeyError(f"{ini}にDEFAULTとMUSIC_ROOTが設定されていません．")

    files = [p for p in glob(root + '/**/*', recursive=True)
             if re.search('/*\.flac\Z', str(p))]

    if not files:  # if empty
        message = f"{ini}に記述した{root}以下に音楽ファイルがみつかりません．"
        raise MusicFileNotFoundError(message)

    
    for f in files:
        tags = FLAC(f)
        artist = get_attribute(tags, 'albumartist')
        if artist == "Unknown":
            artist = get_attribute(tags, 'artist')

        album = get_attribute(tags, 'album')
        title = get_attribute(tags, 'title')
        # タグに設定されていない場合 Unknown

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
        attr = "Unknown"

    return attr

if __name__ == "__main__":
    from pprint import pprint
    music_tree = get_music_tree()
    pprint(music_tree)
