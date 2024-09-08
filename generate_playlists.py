import spotipy  
import random
import logging
import os
import sys
import sqlite3
import glob
import time
from spotipy import SpotifyOAuth
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=int(os.environ.get("LOG_LEVEL")),
        datefmt='%Y-%m-%d %H:%M:%S')

client_id=os.environ.get("SPOTIPY_CLIENT_ID")
client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET")
redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI")
scope="user-top-read,user-library-read,user-read-recently-played"

creds = SpotifyOAuth(scope=scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, open_browser=False)
sp = spotipy.Spotify(auth_manager=creds)

music_dir = os.environ.get("MUSIC_DIR")
playlist_dir = os.environ.get("PLAYLIST_DIR")

def run():
    logging.info('Process Start!')
    if os.path.exists(music_dir):
        if not os.path.exists(playlist_dir):
            os.mkdir(playlist_dir)
        
        my_reccommendations()

        artist_names = []

        for dir_name_artist in os.listdir(music_dir):
            artist_names.append(dir_name_artist)

        random.shuffle(artist_names)

        for artist_name in artist_names:
            show_recommendations_for_artist(artist_name)

        get_user_playlists()

        logging.info('Process Done!')

    else:
        logging.error('Music dir not found! Please check your MUSIC_DIR variable inside the .env file')
        logging.info('Process Failed!')


def navidrome_delete_playlist_by_name(playlist_name):
    dbfile =  os.environ.get("NAVIDROME_DB_FILE")
    if os.path.exists(dbfile):
        con = sqlite3.connect(dbfile)
        cur = con.cursor()
        logging.debug('Deleting playlist %s from Navidrome', playlist_name)
        for result in cur.execute("SELECT id FROM playlist where name = '" + playlist_name + "'"):
            cur_delete_tracks = con.cursor()
            cur_delete_tracks.execute("DELETE FROM playlist_tracks where playlist_id = '" + result[0] + "'")
            cur_delete_tracks.close()
            cur_delete_fields = con.cursor()
            cur_delete_fields.execute("DELETE FROM playlist_fields where playlist_id = '" + result[0] + "'")
            cur_delete_fields.close()
            cur_delete_playlist = con.cursor()
            cur_delete_playlist.execute("DELETE FROM playlist where id = '" + result[0] + "'")
            cur_delete_playlist.close()
        cur.close()
        con.commit()
        con.close()
    else:
        logging.warning('Navidrome db file not found. If you are using navidrome make sure to set up the variable NAVIDROME_DB_FILE inside the .env file')

def my_reccommendations(count = None):
    try:
        top_tracks = sp.current_user_top_tracks(limit=50, time_range='long_term')
        logging.info('Loaded your custom top tracks')
        time.sleep(2)
        liked_tracks = sp.current_user_saved_tracks(limit=50)
        logging.info('Loaded your top liked tracks')
        time.sleep(2)
        history = sp.current_user_recently_played(limit=50)
        logging.info('Loaded your played tracks')
        time.sleep(2)
        for i in range(int(os.environ.get("NUM_USER_PLAYLISTS"))):
            if count is None or (count is not None and count == i):
                logging.info('Searching your reccomendations (playlist %s)', str(i+1))
                top_track_ids = [track['id'] for track in top_tracks['items']]
                liked_track_ids = [track['track']['id'] for track in liked_tracks['items']]
                history_track_ids = [track['track']['id'] for track in history['items']]
                seed_track_ids = top_track_ids + liked_track_ids + history_track_ids
                random.shuffle(seed_track_ids)
                results = sp.recommendations(seed_tracks=seed_track_ids[0:5], limit=int(os.environ.get("ITEMS_PER_PLAYLIST")))
                playlist_name = "My Reccomendations - " + str(i+1)
                write_reccomendation_file(playlist_dir + "/" + playlist_name + ".m3u", results)
                navidrome_delete_playlist_by_name(playlist_name)
                if count is not None:
                    break
            time.sleep(10)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)

def get_artist(name):
    results = sp.search(q='artist:' + name, type='artist')
    items = results['artists']['items']
    if len(items) > 0:
        return items[0]
    else:
        return None

def write_reccomendation_file(playlist_path_file, results):
    try:
        reccomendations_array = []
        for track in results['tracks']:
            
            logging.debug('Searching %s - %s in your music library (%s)', track['name'], track['artists'][0]['name'], music_dir)
            artist_path_dir = None
            for artist_name in os.listdir(music_dir):
                if artist_name.lower() ==  track['artists'][0]['name'].lower() or artist_name.lower() in track['artists'][0]['name'].lower() or track['artists'][0]['name'].lower() in artist_name.lower():
                    artist_path_dir = os.path.join(music_dir, artist_name)
                    break
            if artist_path_dir is not None:
                for song_title in glob.iglob(artist_path_dir + '**/**', recursive=True):
                    if not "live" in song_title.lower() and not "acoustic" in song_title.lower():
                        no_extension_title = os.path.splitext(song_title)[0]
                        parsed_song_title = no_extension_title.split("-")[len(no_extension_title.split("-"))-1].strip()
                        if parsed_song_title.strip() != '' and (track['name'].lower() == parsed_song_title.lower() or parsed_song_title.lower() in track['name'].lower() or track['name'].lower() in parsed_song_title.lower()):
                            song_path_file = os.path.join(artist_path_dir, song_title)
                            reccomendations_array.append(song_path_file)
                            break
        if os.path.exists(playlist_path_file):
            os.remove(playlist_path_file)
        if len(reccomendations_array) > 0:
            with open(playlist_path_file, 'a') as opened_playlist_file:
                for reccomendation in reccomendations_array:
                    opened_playlist_file.write(reccomendation + '\n')
                    logging.info('Writing reccomendation %s to playlist (%s)', reccomendation, playlist_path_file)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)



def write_playlist_file(playlist_path_file, track):
    try:
        logging.debug('Searching %s - %s in your music library (%s)', track['name'], track['artists'][0]['name'], music_dir)
        artist_path_dir = None
        song_path_file = None
        for artist_name in os.listdir(music_dir):
            if artist_name.lower() ==  track['artists'][0]['name'].lower() or artist_name.lower() in track['artists'][0]['name'].lower() or track['artists'][0]['name'].lower() in artist_name.lower():
                artist_path_dir = os.path.join(music_dir, artist_name)
                break
        if artist_path_dir is not None:
            for song_paths in glob.iglob(artist_path_dir + '**/**', recursive=True):
                if not "live" in song_paths.lower() and not "acoustic" in song_paths.lower():
                    no_extension_title = os.path.splitext(os.path.basename(song_paths))[0]
                    parsed_song_title = no_extension_title.split("-")[len(no_extension_title.split("-"))-1].strip()
                    if parsed_song_title.strip() != '' and (track['name'].lower() == parsed_song_title.lower() or parsed_song_title.lower() in track['name'].lower() or track['name'].lower() in parsed_song_title.lower()):
                        song_path_file = song_paths
                        break
        if song_path_file is not None:
            with open(playlist_path_file, 'a') as opened_playlist_file:
                opened_playlist_file.write(song_path_file + '\n')
                logging.info('Writing track %s to playlist (%s)', song_path_file, playlist_path_file)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)

def show_recommendations_for_artist(name):
    logging.info('Searching reccomendations for: %s', name)
    artist = get_artist(name)
    results = sp.recommendations(seed_artists=[artist['id']], limit=int(os.environ.get("ITEMS_PER_PLAYLIST")))
    playlist_name = name + " - Reccomendations"
    write_reccomendation_file(playlist_dir + "/" + playlist_name + ".m3u", results)
    navidrome_delete_playlist_by_name(playlist_name)
    time.sleep(10)

def get_playlist_tracks(item, playlist_path_file, offset_tracks = 0):
    response_tracks = sp.playlist_items(item['id'],
        offset=offset_tracks,
        fields='items.track.id,total',
        limit=50,
        additional_types=['track'])
    for track_id in response_tracks['items']:
        track = sp.track(track_id['track']['id'])
        logging.debug('Found %s - %s inside playlist %s', track['name'], track['artists'][0]['name'], item['name'])
        with open(playlist_path_file, 'a') as opened_playlist_file:
            write_playlist_file(playlist_path_file, track)
        time.sleep(5)

    time.sleep(10)
    if len(response_tracks['items']) != 0:
        get_playlist_tracks(item, playlist_path_file, offset_tracks = len(response_tracks['items']) + 50)

def get_user_playlists(offset = 0, single_execution = False):
    playlist_result = sp.current_user_playlists(limit=50, offset = offset)
    for item in playlist_result['items']:
        if item['name'] is not None and item['name'].strip() != '':
            logging.debug('Found playlist: %s', item['name'])
            
            playlist_path_file = playlist_dir + "/" + item['name'] + ".m3u"

            if os.path.exists(playlist_path_file):
                os.remove(playlist_path_file)
            
            get_playlist_tracks(item, playlist_path_file)
            
            navidrome_delete_playlist_by_name(item['name'])
    
    time.sleep(10)
        
    if not single_execution and len(playlist_result['items']) != 0:
        get_user_playlists(len(playlist_result['items']) + 50)