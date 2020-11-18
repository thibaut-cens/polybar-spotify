#!/usr/bin/env python

import sys
import dbus
import argparse
import traceback
import json

parser = argparse.ArgumentParser()
parser.add_argument(
    '-t',
    '--trunclen',
    type=int,
    metavar='trunclen'
)
parser.add_argument(
    '-f',
    '--format',
    type=str,
    metavar='custom format',
    dest='custom_format'
)
parser.add_argument(
    '--playpause',
    type=str,
    metavar='play-pause indicator',
    dest='play_pause'
)
parser.add_argument(
    '--font',
    type=str,
    metavar='the index of the font to use for the main label',
    dest='font'
)
parser.add_argument(
    '--playpause-font',
    type=str,
    metavar='the index of the font to use to display the playpause indicator',
    dest='play_pause_font'
)
parser.add_argument(
    '-q',
    '--quiet',
    action='store_true',
    help="if set, don't show any output when the current song is paused",
    dest='quiet',
)
parser.add_argument(
    '-p',
    '--player',
    type=str,
    help="Name of the dbus MediaPlayer",
    dest='player',
    default="spotifyd"
)
parser.add_argument(
    '--tmpfile',
    type=str,
    help="Temporary file to store last polled informations ofr use if no metadate are returned",
    dest='player',
    default="/tmp/polybar-play-lastplayed.json"
)

args = parser.parse_args()


def fix_string(string):
    # corrects encoding for the python version used
    if sys.version_info.major == 3:
        return string
    else:
        return string.encode('utf-8')


def truncate(name, trunclen):
    if len(name) > trunclen:
        name = name[:trunclen]
        name += '...'
        if ('(' in name) and (')' not in name):
            name += ')'
    return name


def get_song_info(player: str, tmpfile : str = "/tmp/polybar-spotifyd-lastplayed.json"):
    if player == "mpd":
        from mpd import MPDClient
        client = MPDClient()
        client.connect("localhost", 6600)
        song_info = client.currentsong()
        return song_info["artist"], song_info["title"]
    else:
        bus = dbus.SessionBus()
        try:
            proxy = bus.get_object("org.mpris.MediaPlayer2.%s" % player,
                                   "/org/mpris/MediaPlayer2")

            interface = dbus.Interface(proxy, dbus_interface="org.freedesktop.DBus.Properties")

            properties = interface.GetAll("org.mpris.MediaPlayer2.Player")
            metadata = properties["Metadata"]
        except Exception as e:
            print("[ERROR] " + str(e), file=sys.stderr)
            sys.exit(1)

        if len(metadata) == 0:
            with open(tmpfile, "r") as f:
                metadata = json.load(f)
        else:
            with open(tmpfile, "w+") as f:
                json.dump(metadata, f)
        artist = fix_string(str(metadata['xesam:artist'][0])) if 'xesam:artist' in metadata else ''
        song = fix_string(str(metadata['xesam:title'])) if 'xesam:title' in metadata else ''
        album = fix_string(str(metadata['xesam:album'])) if 'xesam:album' in metadata else ''
        status = properties['PlaybackStatus'] if properties['PlaybackStatus'] else "unknown"
        return status, artist, song, album


# Default parameters
output = fix_string(u'{play_pause} {artist}: {song}')
trunclen = 35
play_pause = fix_string(u'\uf04b,\uf04c,?')  # first character is play, second is paused

label_with_font = '%{{T{font}}}{label}%{{T-}}'
font = args.font
play_pause_font = args.play_pause_font

quiet = args.quiet

# parameters can be overwritten by args
if args.trunclen is not None:
    trunclen = args.trunclen
if args.custom_format is not None:
    output = args.custom_format
if args.play_pause is not None:
    play_pause = args.play_pause

status, artist, song, album = get_song_info(args.player)
# Handle play/pause label

play_pause = play_pause.split(',')

if status == 'Playing':
    play_pause = play_pause[0] if len(play_pause) > 0 else '\uf04b'
elif status == 'Paused':
    play_pause = play_pause[1] if len(play_pause) > 1 else '\uf04c'
elif status == 'unkwnown':
    play_pause = play_pause[2] if len(play_pause) > 2 else '?'
else:
    play_pause = str()

if play_pause_font:
    play_pause = label_with_font.format(font=play_pause_font, label=play_pause)

if (quiet and status == 'Paused') or (not artist and not song and not album):
    print('')
else:
    if font:
        artist = label_with_font.format(font=font, label=artist)
        song = label_with_font.format(font=font, label=song)
        album = label_with_font.format(font=font, label=album)

    # Add 4 to trunclen to account for status symbol, spaces, and other padding characters
    out = output.format(artist=artist,
                        song=song,
                        play_pause=play_pause,
                        album=album)
    print(truncate(out, trunclen + 4))
