# loading in modules
import os

from dotenv import load_dotenv
from os.path import dirname
from os.path import join
from spotdl import Spotdl
from spotdl.types.options import DownloaderOptions
from spotdl.types.song import Song
from ..constants import constants

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

client_id=os.environ.get(constants.SPOTIPY_CLIENT_ID)
client_secret=os.environ.get(constants.SPOTIPY_CLIENT_SECRET)

spotdl_client = Spotdl(client_id=client_id, client_secret=client_secret, no_cache=True)

spotdl_client.downloader.settings["output"] = os.environ.get(constants.SPOTDL_FORMAT, constants.SPOTDL_FORMAT_DEFAULT_VALUE).replace("\"", "")

def download_track(url):
    song = Song.from_url(url)
    spotdl_client.downloader.search_and_download(song)
            
