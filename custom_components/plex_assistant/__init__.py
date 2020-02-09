"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant. Play to chromecast from Plex using fuzzy searches for media
and cast device name.
"""
import time
import logging
from plexapi.server import PlexServer
from pychromecast.controllers.plex import PlexController
from .plex_assistant import *
from .process_speech import process_speech
from .localize import *

_LOGGER = logging.getLogger(__name__)

DOMAIN = "plex_assistant"
CONF_URL = "url"
CONF_TOKEN = "token"
CONF_DEFAULT_CAST = "default_cast"
CONF_LANG = "lang"


def setup(hass, config):
    BASEURL = config[DOMAIN].get(CONF_URL)
    TOKEN = config[DOMAIN].get(CONF_TOKEN)
    DEFAULT_CAST = config[DOMAIN].get(CONF_DEFAULT_CAST)
    LANGUAGE = config[DOMAIN].get(CONF_LANG)

    PlexAssistant.setup(PlexAssistant, PlexServer(BASEURL, TOKEN).library)

    def handle_input(call):
        INPUT = process_speech(
            call.data.get("command").lower(),
            PlexAssistant.lib,
            localize[LANGUAGE] or localize["en"]
        )

        PLEX = PlexAssistant.plex
        if PlexAssistant.lib["updated"] < PLEX.search(sort="addedAt:desc")[0].addedAt:
            PlexAssistant.lib = get_libraries(PLEX)

        MEDIA = INPUT["media"]
        if not INPUT["ondeck"]:
            RESULT = find_media(INPUT, MEDIA, PlexAssistant.lib)
            VIDEO_ID = PLEX.section(
                RESULT["library"].title).get(RESULT["media"])
            VIDEO_ID = video_selection(INPUT, VIDEO_ID)
        elif INPUT["library"]:
            VIDEO_ID = PLEX.section(INPUT["library"].title).onDeck()[0]
        else:
            VIDEO_ID = PLEX.onDeck()[0]

        DEVICES = PlexAssistant.devices
        CAST_NAME = INPUT["chromecast"] or DEFAULT_CAST
        NAME = fuzzy(CAST_NAME, PlexAssistant.device_names)[0]
        CAST = next(CC for CC in DEVICES if CC.device.friendly_name == NAME)

        PC = PlexController()
        CAST.wait()
        CAST.register_handler(PC)

        if CAST.status.status_text:
            CAST.quit_app()
        while CAST.status.status_text:
            time.sleep(0.001)

        PC.play_media(VIDEO_ID)
        while PC.status.player_state != 'PLAYING':
            time.sleep(0.001)
        PC.play_media(VIDEO_ID)
        PC.play()

    hass.services.register(DOMAIN, "command", handle_input)
    return True
