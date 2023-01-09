import os, sys
import time
import threading
import logging as log

from auth.oauth import login
from auth.scopes import ALL_PLAYLIST_MODIFY_SCOPES, ALL_PLAYLIST_READ_SCOPES

from spotipy.client import SpotifyException

class PlaylistWatcher:
    def __init__(self, source, destination=None):
        log.basicConfig(
            level=log.INFO,
            format="[%(levelname)s] [%(asctime)s] %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
        )
        self.source = source
        self.destination = destination
        self.tracks_added = set()
        self.client = None
    
    def start(self):
        while True:
            self.monitor()
            time.sleep(60)

    def monitor(self):
        log.debug("Begin monitor")
        if not self.client:
            self.client = login(
                " ".join([ALL_PLAYLIST_MODIFY_SCOPES, ALL_PLAYLIST_READ_SCOPES])
            )
        if not self.client:
            log.error("Authorization Error")
            sys.exit(-1)
        if not self.destination:
            # First run, create a new playlist
            self.destination = create_watcher_playlist(self.client, self.source)
            self.tracks_added = set()

        destination_playlist = None
        for i in range(3):
            try:
                destination_playlist = self.client.playlist(self.destination)
                break
            except SpotifyException as e:
                log.error(e)
                continue

        if not destination_playlist:
            # Playlist has been deleted, create new one
            self.destination = create_watcher_playlist(self.client, self.source)
            self.tracks_added = set()

        log.debug("Fetching destination track ids")
        destination_track_ids = set(
            get_playlist_track_ids(self.client, self.destination)
        )
        log.debug("Fetching source track ids")
        source_track_ids = set(get_playlist_track_ids(self.client, self.source))

        new_items = source_track_ids - destination_track_ids
        destination_extras = destination_track_ids - source_track_ids
        try:
            if len(new_items) > 0:
                log.info(
                    f"Adding tracks {[self.client.track(x)['name'] for x in new_items]}"
                )
                self.client.playlist_add_items(self.destination, new_items)
                self.tracks_added = self.tracks_added.union(new_items)
            else:
                log.debug("No new tracks found")
            if len(destination_extras) > 0:
                log.info(f"Found {len(destination_extras)} extra tracks")
                # Only remove tracks we have added
                tracks_to_remove = destination_extras.intersection(self.tracks_added)
                if len(tracks_to_remove) > 0:
                    log.info(
                        f"Removing tracks {[self.client.track(x)['name'] for x in tracks_to_remove]}"
                    )
                    self.client.playlist_remove_all_occurrences_of_items(
                        self.destination, tracks_to_remove
                    )
        except SpotifyException as e:
            log.error(f"{e}")
        self.client = None
        log.debug("End monitor")

def _paged_results(sp, results):
    temp = results["items"]
    while results["next"]:
        results = sp.next(results)
        temp.extend(results["items"])
    return temp

def get_playlist_track_ids(sp, playlist_id):
    try:
        track_ids = [
            track["track"]["id"]
            for track in _paged_results(sp, sp.playlist_items(playlist_id))
        ]
        log.debug(f"Found {len(track_ids)} playlist tracks")
        return track_ids
    except SpotifyException as e:
        log.error(f"{e}")
        return []

def create_watcher_playlist(client, source):
    try:
        source_playlist = client.playlist(source)
        source_playlist_name = source_playlist.get('name')
        destination_playlist_name = source_playlist_name + ' watcher'
        destination_playlist_id = client.user_playlist_create(
            client.me()["id"],
            name=destination_playlist_name
        ).get("id")
        log.info(f"Created playlist {destination_playlist_name} with id {destination_playlist_id}")
        return destination_playlist_id
    except SpotifyException as e:
        log.error(f"{e}")
        return None

source_id = os.environ.get("SOURCE_ID")
if not source_id:
    log.error("$SOURCE_ID variable is not set. Aborting")
    sys.exit(1)
destination_id = os.environ.get("DESTINATION_ID")

pw = PlaylistWatcher(source_id, destination=destination_id)
pw.start()