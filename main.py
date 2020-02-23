#
#
#    Copyright (C) 2020  Alin Cretu
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#

import sys
from urllib import urlencode
from urlparse import parse_qsl
import xbmcgui
import xbmcplugin
import os
import re
import xbmcaddon
import requests
import json
import logging
import logging.handlers
import inputstreamhelper

# The cookielib module has been renamed to http.cookiejar in Python 3
import cookielib
# import http.cookiejar


MyAddon = xbmcaddon.Addon(id='plugin.video.DigiOnline.ro')

# Initialize the Addon data directory 
addon_data_dir = xbmc.translatePath(MyAddon.getAddonInfo('profile'))
if not os.path.exists(addon_data_dir):
    os.makedirs(addon_data_dir)

# Log file name 
addon_logfile_name = os.path.join(addon_data_dir, 'plugin.video.DigiOnline.log')

# Read the stored configuration
_config_DebugEnabled_ = MyAddon.getSetting('DebugEnabled')
_config_ShowTitleInChannelList_ = MyAddon.getSetting('ShowTitleInChannelList')


# Configure logging
if _config_DebugEnabled_ == 'true':
  logging.basicConfig(level=logging.DEBUG)
else:
  logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('plugin.video.DigiOnline.log')
logger.propagate = False

# Create a rotating file handler
# TODO: Extend the settings.xml to allow the user to choose the values for maxBytes and backupCount
# TODO: Set the values for maxBytes and backupCount to values defined in the addon settings
handler = logging.handlers.RotatingFileHandler(addon_logfile_name, mode='a', maxBytes=104857600, backupCount=2, encoding=None, delay=False)
if _config_DebugEnabled_ == 'true':
  handler.setLevel(logging.DEBUG)
else:
  handler.setLevel(logging.INFO)

# Create a logging format to be used
formatter = logging.Formatter('%(asctime)s %(funcName)s %(levelname)s: %(message)s', datefmt='%Y%m%d_%H%M%S')
handler.setFormatter(formatter)

# add the file handler to the logger
logger.addHandler(handler)

logger.debug('[ Addon settings ] _config_DebugEnabled_ = ' + str(_config_DebugEnabled_))
logger.debug('[ Addon settings ] _config_ShowTitleInChannelList_ = ' + str(_config_ShowTitleInChannelList_))

# UserAgent exposed by this addon
userAgent = 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0'

# Kodi uses the following sys.argv arguments:
# [0] - The base URL for this add-on, e.g. 'plugin://plugin.video.demo1/'.
# [1] - The process handle for this add-on, as a numeric string.
# [2] - The query string passed to this add-on, e.g. '?foo=bar&baz=quux'.

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]

# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

# File containing the session cookies
addon_cookiesfile_name = os.path.join(addon_data_dir, 'cookies.txt')
logger.debug('[ Addon cookiefile ] addon_cookiesfile_name = ' + str(addon_cookiesfile_name))

# Start a new requests session and initialize the cookiejar
__session__ = requests.Session()

### WARNING: The cookielib module has been renamed to http.cookiejar in Python 3
cookiejar = cookielib.MozillaCookieJar(addon_cookiesfile_name)
#cookiejar = http.cookiejar.MozillaCookieJar(addon_cookiesfile_name)

# If it doesn't exist already, create a new file where the cookies should be saved
if not os.path.exists(addon_cookiesfile_name):
  cookiejar.save()
  logger.info('[ Addon cookiefile ] Created cookiejar file: ' + str(addon_cookiesfile_name))
  logger.debug('[ Addon cookiefile ] Created cookiejar file: ' + str(addon_cookiesfile_name))

# Put all session cookeis in the cookiejar
__session__.cookies = cookiejar

# Load any cookies saved from the last run
cookiejar.load()
logger.debug('[ Addon cookiejar ] Loaded cookiejar from file: ' + str(addon_cookiesfile_name))


def check_defaults_DigiOnline_account():
    logger.debug('Enter function')

    _config_AccountUser = MyAddon.getSetting('AccountUser')
    while _config_AccountUser == '__DEFAULT_USER__':
        logger.debug('Default settings found.', 'Please configure the Authentication User to be used with this addon.')
        xbmcgui.Dialog().ok('Default settings found.', 'Please configure the Authentication User to be used with this addon.')
        MyAddon.openSettings()
        _config_AccountUser = MyAddon.getSetting('AccountUser')

    _config_AccountPassword = MyAddon.getSetting('AccountPassword')
    while _config_AccountPassword == '__DEFAULT_PASSWORD__':
        logger.debug('Default settings found', 'Please configure the Authenticatin Password to be used with this addon.')
        xbmcgui.Dialog().ok('Default settings found', 'Please configure the Authenticatin Password to be used with this addon.')
        MyAddon.openSettings()
        _config_AccountPassword = MyAddon.getSetting('AccountPassword')

    logger.debug('Exit function')

def do_login():
    global __session__
    global cookiejar

    logger.debug('Enter function')

    # Authentication to DigiOnline is done in two stages:
    # 1 - Send a GET request to https://www.digionline.ro/auth/login ('DOSESSV3PRI' session cookie will be set) 
    # 2 - Send a PUT request to https://www.digionline.ro/auth/login with the credentials in the form-encoded data ('deviceId' cookie will be set)

    logger.debug('============== Stage 1: Start ==============')
    # Setup headers for the first request
    MyHeaders = {
        'Host': 'www.digionline.ro',
        'User-Agent': userAgent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }

    logger.debug('Cookies: ' + str(list(cookiejar)))
    logger.debug('Headers: ' + str(MyHeaders))
    logger.debug('URL: https://www.digionline.ro/auth/login')
    logger.debug('Method: GET')

    # Send the GET request
    _request_ = __session__.get('https://www.digionline.ro/auth/login', headers=MyHeaders)
        
    logger.debug('Received status code: ' + str(_request_.status_code))
    logger.debug('Received cookies: ' + str(list(cookiejar)))    
    logger.debug('Received headers: ' + str(_request_.headers))
    logger.debug('Received data: ' + str(_request_.content))
    logger.debug('============== Stage 1: End ==============')

    # Save cookies for later use.
    cookiejar.save(ignore_discard=True)

    logger.debug('============== Stage 2: Start ==============')

    # Setup headers for second request
    MyHeaders = {
        'Host': 'www.digionline.ro',
        'Origin': 'https://www.digionline.ro',
        'Referer': 'https://www.digionline.ro/auth/login',
        'User-Agent': userAgent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'identity',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }

    # Setup form data to be sent
    _config_AccountUser = MyAddon.getSetting('AccountUser')
    _config_AccountPassword = MyAddon.getSetting('AccountPassword')
    MyFormData = {
      'form-login-email': _config_AccountUser,
      'form-login-password': _config_AccountPassword
        }

    logger.debug('Cookies: ' + str(list(cookiejar)))
    logger.debug('Headers: ' + str(MyHeaders))
    logger.debug('MyFormData: ' + str(MyFormData))
    logger.debug('URL: https://www.digionline.ro/auth/login')
    logger.debug('Method: POST')

    # Send the POST request
    _request_ = __session__.post('https://www.digionline.ro/auth/login', headers=MyHeaders, data=MyFormData)

    logger.debug('Received status code: ' + str(_request_.status_code))
    logger.debug('Received cookies: ' + str(list(cookiejar)))
    logger.debug('Received headers: ' + str(_request_.headers))
    logger.debug('Received data: ' + str(_request_.content))
    logger.debug('============== Stage 2: End ==============')

    # Authentication error. 
    if re.search('<div class="form-error(.+?)>', _request_.content, re.IGNORECASE):
      logger.debug('\'form-error\' found.')

      _ERR_SECTION_ = re.findall('<div class="form-error(.+?)>\n(.+?)<\/div>', _request_.content, re.IGNORECASE|re.DOTALL)[0][1].strip()
      _auth_error_message_ = re.sub('&period;', '.', _ERR_SECTION_, flags=re.IGNORECASE)
      _auth_error_message_ = re.sub('&abreve;', 'a', _auth_error_message_, flags=re.IGNORECASE)

      logger.info('[Authentication error] => Error message: '+ _auth_error_message_)

      logger.debug('_ERR_SECTION_ = ' + str(_ERR_SECTION_))
      logger.debug('_auth_error_message_ = ' + _auth_error_message_)
      logger.debug('[Authentication error] => Error message: '+ _auth_error_message_)

      xbmcgui.Dialog().ok('[Authentication error message]', _auth_error_message_)

      logger.debug('Exit function')

      xbmc.executebuiltin("XBMC.Container.Update(path,replace)")


    else:
      logger.debug('\'form-error\' not found.')

      logger.info('Authentication successfull')
      logger.debug('Authentication successfull')

      # Save cookies for later use.
      cookiejar.save(ignore_discard=True)

      logger.debug('Exit function')
    

def get_url(**kwargs):
    ####
    #
    # Create a URL for calling the plugin recursively from the given set of keyword arguments.
    #
    ####

    logger.debug('Enter function')
    logger.debug('Called with parameters: ' + str(kwargs))

    _call_url_ = '{0}?{1}'.format(_url, urlencode(kwargs))

    logger.debug('_call_url_: ' + str(_call_url_))
    logger.debug('Exit function')

    return _call_url_


def get_categories():
    ####
    #
    # Get the list of video categories.
    #
    # Return: The list of video categories
    #
    ####

    global __session__
    global cookiejar

    logger.debug('Enter function')

    MyHeaders = {
      'Host': 'www.digionline.ro',
      'Referer': 'https://www.digionline.ro/',
      'User-Agent': userAgent,
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US',
      'Accept-Encoding': 'identity',
      'Connection': 'keep-alive',
      'Upgrade-Insecure-Requests': '1',
      'Cache-Control': 'max-age=0'
    }

    logger.debug('Cookies: ' + str(list(cookiejar)))
    logger.debug('Headers: ' + str(MyHeaders))
    logger.debug('URL: https://www.digionline.ro')
    logger.debug('Method: GET')

    # Send the GET request
    _request_ = __session__.get('https://www.digionline.ro', headers=MyHeaders)
    
    logger.debug('Received status code: ' + str(_request_.status_code))    
    logger.debug('Received cookies: ' + str(list(cookiejar)))
    logger.debug('Received headers: ' + str(_request_.headers))
    logger.debug('Received data: ' + str(_request_.content))

    # Get the raw list of categories
    _raw_categories_ = re.findall('<a href=(.+?)class="nav-menu-item-link ">', _request_.content, re.IGNORECASE)
    logger.debug('Found: _raw_categories_ = ' + str(_raw_categories_))

    # Cleanup special characters
    _raw_categories_ = str(_raw_categories_).replace('\\xc8\\x98', 'S')
    _raw_categories_ = str(_raw_categories_).replace('\\xc4\\x83', 'a')
    logger.debug('Cleaned-up _raw_categories_ = ' + str(_raw_categories_))

    # Build the list of categories names and their titles
    _raw_categories_ = re.findall('"/(.+?)" title="(.+?)"',str(_raw_categories_), re.IGNORECASE)
    logger.debug('Found: _raw_categories_ = ' + str(_raw_categories_))

    # Initialize the list of channels
    _categories_list_ = []

    for _cat_ in _raw_categories_:
      logger.info('Found category: ' + _cat_[1])
      logger.debug('Found category: ' + _cat_[1])
      _cat_record_ = {}
      _cat_record_["name"] = _cat_[0]
      _cat_record_["title"] = _cat_[1]
 
      logger.debug('Created: _cat_record_ = ' + str(_cat_record_))
      _categories_list_.append(_cat_record_)

    logger.debug('_categories_list_ = ' + str(_categories_list_))
    logger.debug('Exit function')

    return _categories_list_


def get_channels(category):
    ####
    #
    # Get the list of channels/streams.
    #
    # Parameters:
    #      category: Category name
    #
    # Return: The list of channels/streams in the given category
    #
    ####

    global __session__
    global cookiejar

    logger.debug('Enter function')
    logger.debug('Called with parameters:  category = ' + category)

    logger.info('Looking for channels in category: ' + category)
    logger.debug('Looking for channels in category: ' + category)

    # Get the list of channels in this category
    MyHeaders = {
      'Host': 'www.digionline.ro',
      'Referer': 'https://www.digionline.ro/',
      'User-Agent': userAgent,
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US',
      'Accept-Encoding': 'identity',
      'Connection': 'keep-alive',
      'Upgrade-Insecure-Requests': '1',
      'Cache-Control': 'max-age=0'
    }

    logger.debug('Cookies: ' + str(list(cookiejar)))
    logger.debug('Headers: ' + str(MyHeaders))
    logger.debug('URL: https://www.digionline.ro/' + category)
    logger.debug('Method: GET')

    # Send the GET request
    _request_ = __session__.get('https://www.digionline.ro/' + category, headers=MyHeaders)
        
    logger.debug('Received status code: ' + str(_request_.status_code))
    logger.debug('Received cookies: ' + str(list(cookiejar)))
    logger.debug('Received headers: ' + str(_request_.headers))
    logger.debug('Received data: ' + str(_request_.content))
    
    _raw_channel_boxes_ = re.findall('<div class="box-container">(.+?)<figcaption>', _request_.content, re.IGNORECASE|re.DOTALL) 
    logger.debug('Found _raw_channel_boxes = ' + str(_raw_channel_boxes_))
        
    # Initialize the list of channels
    _channels_ = []

    for _raw_channel_box_ in _raw_channel_boxes_:
      logger.debug('_raw_channel_box_ = ' + str(_raw_channel_box_))

      _channel_record_ = {}

      _channel_endpoint_ = re.findall('<a href="(.+?)" class="box-link"></a>', _raw_channel_box_, re.IGNORECASE)
      _channel_endpoint_ = _channel_endpoint_[0]
      logger.debug('Found: _channel_endpoint_ = ' + _channel_endpoint_)
      
      _channel_logo_ = re.findall('<img src="(.+?)" alt="logo">', _raw_channel_box_, re.IGNORECASE)
      _channel_logo_ = _channel_logo_[0]
      logger.debug('Found: _channel_logo_ = ' + _channel_logo_)

      # Get additional details of the current channel
      MyHeaders = {
        'Host': 'www.digionline.ro',
        'Referer': 'https://www.digionline.ro/' + category,
        'User-Agent': userAgent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
      }

      logger.debug('Cookies: ' + str(list(cookiejar)))
      logger.debug('Headers: ' + str(MyHeaders))
      logger.debug('URL: https://www.digionline.ro' + _channel_endpoint_)
      logger.debug('Method: GET')

      # Send the GET request
      _request_ = __session__.get('https://www.digionline.ro' + _channel_endpoint_, headers=MyHeaders)
        
      logger.debug('Received status code: ' + str(_request_.status_code))
      logger.debug('Received cookies: ' + str(list(cookiejar)))
      logger.debug('Received headers: ' + str(_request_.headers))
      logger.debug('Received data: ' + str(_request_.content))

      _raw_channel_details_box_ = re.findall('<div class="entry-video video-player(.+?)</div>', _request_.content, re.IGNORECASE|re.DOTALL)
      logger.debug('_raw_channel_details_box_ = ' + str(_raw_channel_details_box_))

      _channel_details_box_ = _raw_channel_details_box_[0]
      _channel_details_box_ = _channel_details_box_.replace('\n', '')
      _channel_details_box_ = _channel_details_box_.strip()
      logger.debug('_channel_details_box_ = ' + _channel_details_box_)

      _channel_metadata_ = re.findall('<script type="text/template">(.+?)</script>', _channel_details_box_, re.IGNORECASE)
      _channel_metadata_ = _channel_metadata_[0].strip()
      logger.debug('Found: _channel_metadata_ = ' + str(_channel_metadata_))

      _ch_meta_ = json.loads(_channel_metadata_)
      logger.info('Found channel: ' + _ch_meta_['new-info']['meta']['channelName'])
      logger.debug('Found: _channel_name_ = ' + _ch_meta_['new-info']['meta']['channelName'])
      logger.debug('Found: _channel_streamId_ = ' + str(_ch_meta_['new-info']['meta']['streamId']))

      # Get the EPG details for the current channel
      MyHeaders = {
        'Host': 'www.digionline.ro',
        'Referer': 'https://www.digionline.ro/' + _channel_endpoint_,
        'User-Agent': userAgent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
      }

      logger.debug('Cookies: ' + str(list(cookiejar)))
      logger.debug('Headers: ' + str(MyHeaders))
      logger.debug('URL: https://www.digionline.ro/epg-xhr?channelId=' + str(_ch_meta_['new-info']['meta']['streamId']))
      logger.debug('Method: GET')

      # Send the GET request
      _request_ = __session__.get('https://www.digionline.ro/epg-xhr?channelId=' + str(_ch_meta_['new-info']['meta']['streamId']), headers=MyHeaders)
        
      logger.debug('Received status code: ' + str(_request_.status_code))
      logger.debug('Received cookies: ' + str(list(cookiejar)))
      logger.debug('Received headers: ' + str(_request_.headers))
      logger.debug('Received data: ' + str(_request_.content))

      _channel_epgdata_ = _request_.content
      logger.debug('_channel_epgdata_ = ' + _channel_epgdata_)

      _channel_record_["endpoint"] = _channel_endpoint_
      _channel_record_["name"] = _ch_meta_['new-info']['meta']['channelName']
      _channel_record_["logo"] = _channel_logo_
      _channel_record_["metadata"] = _channel_metadata_
      _channel_record_["epgdata"] = _channel_epgdata_

      logger.debug('Created: _channel_record_ = ' + str(_channel_record_))
      _channels_.append(_channel_record_)

    logger.debug('_channels_ = ' + str(_channels_))
    logger.debug('Exit function')
    return _channels_


def list_categories():
    ####
    #
    # Create the list of video categories in the Kodi interface.
    #
    ####

    logger.debug('Enter function')

    # Set plugin category.
    xbmcplugin.setPluginCategory(_handle, 'DigiOnline.ro')

    # Set plugin content. 
    xbmcplugin.setContent(_handle, 'videos')

    # Get video categories
    categories = get_categories()
    logger.debug('Received categories = ' + str(categories))

    for category in categories:
        logger.debug('category name = ' + category['name'] + '| category title = ' + category['title'])

        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=category['title'])

        # Set additional info for the list item.
        # For available properties see https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
        # 'mediatype' is needed for a skin to display info for this ListItem correctly.
        list_item.setInfo('video', {'title': category['title'],
                                    'genre': category['title'],
                                    'mediatype': 'video'})

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=filme
        url = get_url(action='listing', category=category['name'])
        logger.debug('URL for plugin recursive call: ' + url)

        # This means that this item opens a sub-list of lower level items.
        is_folder = True

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    # See: https://romanvm.github.io/Kodistubs/_autosummary/xbmcplugin.html
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)
    
    logger.debug('Exit function')


def list_channels(category):
    ####
    #
    # Create the list of playable videos in the Kodi interface.
    #
    # Parameters:
    #      category: Category name
    #
    ####

    logger.debug('Enter function')
    logger.debug('Called with parameters:  category = ' + category)

    # Set plugin category.
    xbmcplugin.setPluginCategory(_handle, category)

    # Set plugin content.
    xbmcplugin.setContent(_handle, 'videos')

    # Get the list of videos in the category.
    channels = get_channels(category)
    logger.debug('Received channels: ' + str(channels))

    for channel in channels:
        logger.debug('Channel data => ' +str(channel))
        logger.debug('Channel name: ' + channel['name'])
        logger.debug('Channel logo: ' + channel['logo'])
        logger.debug('Channel endpoint: ' + channel['endpoint'])
        logger.debug('Channel metadata: ' + str(channel['metadata']))
        logger.debug('Channel epgdata: ' + str(channel['epgdata']))

        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=channel['name'])

        ch_epg_data = json.loads(channel['epgdata'])
	logger.debug('ch_epgdata = ' + str(ch_epg_data))

        if ch_epg_data:
          logger.debug('Channel has EPG data')
          logger.debug('Channel EPG data => [title]: ' + ch_epg_data['title'])
          logger.debug('Channel EPG data => [synopsis]: ' + ch_epg_data['synopsis'])

          # Set additional info for the list item.
          # For available properties see https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
          # 'mediatype' is needed for skin to display info for this ListItem correctly.
          if _config_ShowTitleInChannelList_ == 'false':
            list_item.setInfo('video', {'title': channel['name'],
                                        'genre': category,
                                        'plotoutline': ch_epg_data['title'],
                                        'plot': ch_epg_data['synopsis'],
                                        'mediatype': 'video'})          
            
          else:
            list_item.setInfo('video', {'title': channel['name'] + '  [ ' + ch_epg_data['title'] + ' ]',
                                        'genre': category,
                                        'plotoutline': ch_epg_data['title'],
                                        'plot': ch_epg_data['synopsis'],
                                        'mediatype': 'video'})          

        else:
          logger.debug('Channel does not have EPG data')

          list_item.setInfo('video', {'title': channel['name'],
                                      'genre': category,
                                      'mediatype': 'video'})


        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        list_item.setArt({'thumb': channel['logo']})

        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=play&channel_endpoint=/filme/tnt&channel_metadata=...&channel_epgdata=....
        url = get_url(action='play', channel_endpoint=channel['endpoint'], channel_metadata=channel['metadata'], channel_epgdata=channel['epgdata'])
        logger.debug('URL for plugin recursive call: ' + url)

        # This means that this item won't open any sub-list.
        is_folder = False

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

    logger.debug('Exit function')


def play_video(endpoint, metadata, epgdata):
    ####
    #
    # Play a video by the provided path.
    #
    # Parameters:
    #      path: Fully-qualified video URL
    #
    ####

    global __session__
    global cookiejar

    logger.debug('Enter function')
    logger.debug('Called with parameters: endpoint = ' + endpoint)
    logger.debug('Called with parameters: metadata = ' + str(metadata))
    logger.debug('Called with parameters: epgdata = ' + str(epgdata))

    # Set a flag so we know whether to enter in the last "if" clause
    known_video_type = 0

    _channel_metadata_ = json.loads(metadata)
    _channel_epgdata_ = json.loads(epgdata)

    logger.info('Play channel: ' + _channel_metadata_['new-info']['meta']['channelName'])
    logger.debug('Play channel: ' + _channel_metadata_['new-info']['meta']['channelName'])

    logger.debug('_channel_metadata_[\'shortcode\'] = ' + _channel_metadata_['shortcode'])
    

    if _channel_metadata_['shortcode'] == 'livestream':
      logger.debug('Playing a \'livestream\' video.')

      # Set the flag so we won't enter in the last "if" clause
      known_video_type = 1 

      # Get the stream data (contains the URL for the stream to be played)
      MyHeaders = {
        'Host': 'www.digionline.ro',
        'Referer': 'https://www.digionline.ro' + endpoint,
        'Origin':  'https://www.digionline.ro',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': userAgent,
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
      }

      MyPostData = {'id_stream': _channel_metadata_['new-info']['meta']['streamId'], 'quality': 'hq'}

      logger.debug('Cookies: ' + str(list(cookiejar)))
      logger.debug('Headers: ' + str(MyHeaders))
      logger.debug('MyPostData: ' + str(MyPostData))
      logger.debug('URL: https://www.digionline.ro' + _channel_metadata_['new-info']['meta']['streamUrl'])
      logger.debug('Method: POST')

      # Send the POST request
      _request_ = __session__.post('https://www.digionline.ro' + _channel_metadata_['new-info']['meta']['streamUrl'], data=MyPostData, headers=MyHeaders)
        
      logger.debug('Received status code: ' + str(_request_.status_code))
      logger.debug('Received cookies: ' + str(list(cookiejar)))
      logger.debug('Received headers: ' + str(_request_.headers))
      logger.debug('Received data: ' + _request_.content)

      _stream_data_ = json.loads(_request_.content)
      logger.debug('_stream_data_ = ' + str(_stream_data_))

      # Get the host needed to be set in the headers
      _headers_host_ = re.findall('//(.+?)/', _stream_data_['stream_url'], re.IGNORECASE)[0]
      logger.debug('Found: _headers_host_ = ' + _headers_host_)

     # If needed, append the "https:" to the stream_url
      if 'https://' not in _stream_data_['stream_url']:
        _stream_url_ = 'https:' + _stream_data_['stream_url']
        logger.debug('Created: _stream_url_ = ' + _stream_url_)
      else:
        _stream_url_ = _stream_data_['stream_url']
        logger.debug('Found: _stream_url_ = ' + _stream_url_)
      
      # Set the headers to be used with imputstream.adaptive
      _headers_ = ''
      _headers_ = _headers_ + 'Host=' + _headers_host_
      _headers_ = _headers_ + '&User-Agent=' + userAgent
      _headers_ = _headers_ + '&Referer=' + 'https://www.digionline.ro' + endpoint
      _headers_ = _headers_ + '&Origin=https://www.digionline.ro'
      _headers_ = _headers_ + '&Connection=keep-alive'
      _headers_ = _headers_ + '&Accept-Language=en-US'
      _headers_ = _headers_ + '&Accept=*/*'
      _headers_ = _headers_ + '&Accept-Encoding=identity'
      logger.debug('Created: _headers_ = ' + _headers_) 

      # Create a playable item with a path to play.
      # See:  https://github.com/peak3d/inputstream.adaptive/issues/131#issuecomment-375059796
      play_item = xbmcgui.ListItem(path=_stream_url_)
      play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
      play_item.setProperty('inputstream.adaptive.stream_headers', _headers_)
      play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
      play_item.setMimeType('application/vnd.apple.mpegurl')
      play_item.setContentLookup(False)
      
      # Pass the item to the Kodi player.
      xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


    if _channel_metadata_['shortcode'] == 'nagra-livestream':
      logger.debug('Playing a \'nagra-livestream\' video.')

      # Set the flag so we won't enter in the last if clause
      known_video_type = 1

      for cookie in cookiejar:
        if cookie.name == "deviceId":
          _deviceId_ = cookie.value
          logger.debug(' _deviceID_ = ' + _deviceId_ )

      # Get the stream data (contains the URL for the stream to be played)
      MyHeaders = {
        'Host': 'www.digionline.ro',
        'Referer': 'https://www.digionline.ro' + endpoint,
        'Origin':  'https://www.digionline.ro',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': userAgent,
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
      }

      MyPostData = {'id_stream': _channel_metadata_['new-info']['meta']['streamId'], 'quality': 'hq', 'id_device': _deviceId_}

      logger.debug('Cookies: ' + str(list(cookiejar)))
      logger.debug('Headers: ' + str(MyHeaders))
      logger.debug('MyPostData: ' + str(MyPostData))
      logger.debug('URL: https://www.digionline.ro' + _channel_metadata_['new-info']['meta']['streamUrl'])
      logger.debug('Method: POST')

      # Send the POST request
      _request_ = __session__.post('https://www.digionline.ro' + _channel_metadata_['new-info']['meta']['streamUrl'], data=MyPostData, headers=MyHeaders)
        
      logger.debug('Received status code: ' + str(_request_.status_code))
      logger.debug('Received cookies: ' + str(list(cookiejar)))
      logger.debug('Received headers: ' + str(_request_.headers))
      logger.debug('Received data: ' + _request_.content)

      _stream_data_ = json.loads(_request_.content)
      logger.debug('_stream_data_ = ' + str(_stream_data_))

      if _stream_data_['error']['error_code'] == 0:
        logger.debug('_stream_data_[\'error\'][\'error_code\'] = ' + str(_stream_data_['error']['error_code']))

        # Get the host needed to be set in the headers for the manifest file
        _headers_host_ = re.findall('//(.+?)/', _stream_data_['data']['content']['stream.manifest.url'], re.IGNORECASE)[0]
        logger.debug('Found: _headers_host_ = ' + _headers_host_)

       # If needed, append the "https:" to the stream_url
        if 'https://' not in _stream_data_['data']['content']['stream.manifest.url']:
          _stream_manifest_url_ = 'https:' + _stream_data_['data']['content']['stream.manifest.url']
          logger.debug('Created: _stream_manifest_url_ = ' + _stream_manifest_url_)
        else:
          _stream_manifest_url_ = _stream_data_['data']['content']['stream.manifest.url']
          logger.debug('Found: _stream_manifest_url_ = ' + _stream_manifest_url_)

        # Set the headers to be used with imputstream.adaptive
        _headers_ = ''
        _headers_ = _headers_ + 'Host=' + _headers_host_
        _headers_ = _headers_ + '&User-Agent=' + userAgent
        _headers_ = _headers_ + '&Referer=' + 'https://www.digionline.ro' + endpoint
        _headers_ = _headers_ + '&Origin=https://www.digionline.ro'
        _headers_ = _headers_ + '&Connection=keep-alive'
        _headers_ = _headers_ + '&Accept-Language=en-US'
        _headers_ = _headers_ + '&Accept=*/*'
        _headers_ = _headers_ + '&Accept-Encoding=identity'
        logger.debug('Created: _headers_ = ' + _headers_) 

        # Get the host needed to be set in the headers for the DRM license request
        _lic_headers_host_ = re.findall('//(.+?)/', _stream_data_['data']['content']['widevine.proxy'], re.IGNORECASE)[0]
        logger.debug('Found: _lic_headers_host_ = ' + _lic_headers_host_)

        # Set the headers to be used when requesting license key
        _lic_headers_ = ''
        _lic_headers_ = _lic_headers_ + 'Host=' + _lic_headers_host_
        _lic_headers_ = _lic_headers_ + '&User-Agent=' + userAgent
        _lic_headers_ = _lic_headers_ + '&Referer=' + 'https://www.digionline.ro' + endpoint
        _lic_headers_ = _lic_headers_ + '&Origin=https://www.digionline.ro'
        _lic_headers_ = _lic_headers_ + '&Connection=keep-alive'
        _lic_headers_ = _lic_headers_ + '&Accept-Language=en-US'
        _lic_headers_ = _lic_headers_ + '&Accept=*/*'
        _lic_headers_ = _lic_headers_ + '&Accept-Encoding=identity'
        _lic_headers_ = _lic_headers_ + '&verifypeer=false'
        logger.debug('Created: _lic_headers_ = ' + _lic_headers_) 

        # Create a playable item with a path to play.
        ### See:
        ###    https://github.com/peak3d/inputstream.adaptive/wiki 
        ###    https://github.com/peak3d/inputstream.adaptive/wiki/Integration
        ###    https://github.com/emilsvennesson/script.module.inputstreamhelper

        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        if is_helper.check_inputstream():
          play_item = xbmcgui.ListItem(path=_stream_manifest_url_)
          play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
          play_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
          play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
          play_item.setProperty('inputstream.adaptive.license_key', _stream_data_['data']['content']['widevine.proxy'] + '|' + _lic_headers_ + '|R{SSM}|')
          play_item.setMimeType('application/dash+xml')

          # Pass the item to the Kodi player.
          xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

      else:
        # The DigiOnline.ro account configured in the addon's settings is not entitled to play this stream.
        logger.debug('_stream_data_[\'error\'][\'error_code\'] = ' + str(_stream_data_['error']['error_code']))
        logger.debug('_stream_data_[\'error\'][\'error_message\'] = ' + _stream_data_['error']['error_message'])
        
        logger.info('[Error code: ' + str(_stream_data_['error']['error_code']) + ']  => ' + _stream_data_['error']['error_message'])
        logger.debug('[Error code: ' + str(_stream_data_['error']['error_code']) + ']  => ' + _stream_data_['error']['error_message'])

        xbmcgui.Dialog().ok('[Error code: ' + str(_stream_data_['error']['error_code']) + ']', _stream_data_['error']['error_message'])
        

    # A 'catch-all'-type condition to cover for the unknown cases  
    if known_video_type == 0:
      logger.info('Don\'t know (yet ?) how to play a \'' + _channel_metadata_['shortcode'] + '\' video type.')
      logger.debug('Don\'t know (yet ?) how to play a \'' + _channel_metadata_['shortcode'] + '\' video type.')

    logger.debug('Exit function')

def router(paramstring):
    ####
    #
    # Router function that calls other functions depending on the provided paramster
    #
    # Parameters:
    #      paramstring: URL encoded plugin paramstring
    #
    ####
    
    logger.debug('Enter function')

    # Login to DigiOnline for this session
    do_login()

    # Parse a URL-encoded paramstring to the dictionary of {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))

    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            # Display the list of channels in a provided category.
            list_channels(params['category'])
        elif params['action'] == 'play':
            # Play a video from the provided URL.
            play_video(params['channel_endpoint'], params['channel_metadata'], params['channel_epgdata'])
        else:
            # Raise an exception if the provided paramstring does not contain a supported action
            # This helps to catch coding errors,
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters:
        
        # Get the details of the configured DigiOnline.ro account.       
        check_defaults_DigiOnline_account()

        # Display the list of available video categories
        list_categories()

    # TODO: Logout from DigiOnline for this session
    # TODO: do_logout()

    logger.debug('Exit function')


if __name__ == '__main__':
    logger.debug('Enter function')

    # Call the router function and pass the plugin call parameters to it.
    router(sys.argv[2][1:])

    logger.debug('Exit function')


