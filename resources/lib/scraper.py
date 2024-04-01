# -*- coding: utf-8 -*-
#
# Advanced Kodi Launcher scraping engine for GameFAQs.

# Copyright (c) 2020-2021 Chrisism
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

# --- Python standard library ---
from __future__ import unicode_literals
from __future__ import division

import typing
import logging
import re

from urllib.parse import urlencode

# --- AKL packages ---
from akl import constants, platforms, settings
from akl.utils import io, net, kodi, text
from akl.scrapers import Scraper
from akl.api import ROMObj

# ------------------------------------------------------------------------------------------------
# GameFAQs online scraper.
#
# | Site     | https://gamefaqs.gamespot.com/ |
# | API info | GameFAQs has no API            |
# ------------------------------------------------------------------------------------------------
class GameFAQs(Scraper):
    # --- Class variables ------------------------------------------------------------------------
    supported_metadata_list = [
        constants.META_TITLE_ID,
        constants.META_YEAR_ID,
        constants.META_GENRE_ID,
        constants.META_DEVELOPER_ID,
        constants.META_PLOT_ID,
    ]
    supported_asset_list = [
        constants.ASSET_TITLE_ID,
        constants.ASSET_SNAP_ID,
        constants.ASSET_BOXFRONT_ID,
        constants.ASSET_BOXBACK_ID,
    ]

    base_url = "https://gamefaqs.gamespot.com"

    # --- Constructor ----------------------------------------------------------------------------
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        self.regex_candidates = re.compile(r'<tr><td>(.*?)</td><td><a class="log_search" data-row="[0-9]+" data-col="1" data-pid="([0-9]+)" href="(.*?)">(.*?)</a></td><td>(.*?)</td><td>(.*?)</td></tr>')
        self.regex_meta_year = re.compile(r'<div class="content"><b>Release:</b> <a href=".*?">(.*?)</a></div>')
        self.regex_meta_genre = re.compile(r'<div class="content"><b>Genre:</b> <a href=".*?">(.*?)</a>')
        self.regex_meta_dev_a = re.compile(r'<div class="content"><b>Developer/Publisher: </b><a href=".*?">(.*?)</a></div>')
        self.regex_meta_dev_b = re.compile(r'<div class="content"><b>Developer: </b><a href=".*?">(.*?)</a></div>')
        self.regex_meta_plot = re.compile(r'<div class="game_desc">(.*?)</div>')
        self.regex_meta_rating = re.compile(r'<div class="gamespace_rate_half" title="Average: (.*?) stars from \d*? users">')
        self.regex_meta_esrb = re.compile(r'<div class="esrb"><p><span title=".*?" class="esrb_logo (.*?)"></span></p></div>')
        self.regex_meta_nplayers = re.compile(r'<div class="content"><span class="bold">Local Players:</span>&nbsp;<span>(.*?)</span></div>')
        self.regex_meta_nplayers_online = re.compile(r'<div class="content"><span class="bold">Online Players:</span>&nbsp;<span>(.*?)</span></div>')
        
        self.regex_num_of_player = re.compile(r'\d+\-(\d+)')

        self.regex_assets = re.compile(r'<div class="head"><h2 class="title">(.+?)</h2></div>(<div class="contrib_jumper">.+?</div>)?<div class="body"><ol class="list flex col5 .*?">(.*?)</ol></div>')
        self.regex_asset_links = re.compile(r'<a href="(?P<lnk>.+?)"><img class="(img100\s)?imgboxart" src="(?P<thumb>.+?)" (alt="(?P<alt>.*?)")?\s?/></a>')
        self.regex_asset_urls = re.compile(r'<img (class="full_boxshot imgboxart cte"\s\s?)?data-img-width="\d+" data-img-height="\d+" data-img="(?P<url>.+?)" (class="full_boxshot imgboxart cte"\s\s?)?src=".+?" alt="(?P<alt>.+?)"(\s/)?>')
        self.regex_metacritic = re.compile(r'<div class="metacritic"><div title="Metacritic" class="title"> </div><a href="(.*?)"><div class="score score_.*?" title="Metascore .*?">(\d*?)</div></a><a href=".*?">.*?</a></div>')

        self.cache_candidates = {}
        self.cache_metadata = {}
        self.cache_assets = {}
        self.all_asset_cache = {}
        
        cache_dir = settings.getSettingAsFilePath('scraper_cache_dir')
        super(GameFAQs, self).__init__(cache_dir)

    # --- Base class abstract methods ------------------------------------------------------------    
    def get_name(self):
        return 'GameFAQs'

    def get_filename(self):
        return 'GameFAQs'

    def supports_disk_cache(self):
        return True

    def supports_search_string(self):
        return True

    def supports_metadata_ID(self, metadata_ID):
        return True if metadata_ID in GameFAQs.supported_metadata_list else False

    def supports_metadata(self):
        return True

    def supports_asset_ID(self, asset_ID):
        return True if asset_ID in GameFAQs.supported_asset_list else False

    def supports_assets(self):
        return True
    
    # GameFAQs does not require any API keys. By default status_dic is configured for successful
    # operation so return it as it is.
    def check_before_scraping(self, status_dic):
        return status_dic

    def get_candidates(self, search_term: str, rom: ROMObj, platform, status_dic) -> typing.List[dict]:
        # --- If scraper is disabled return immediately and silently ---
        if self.scraper_disabled:
            # If the scraper is disabled return None and do not mark error in status_dic.
            self.logger.debug('GamesFaq.get_candidates() Scraper disabled. Returning empty data.')
            return None
        
        #def get_candidates(self, search_term, rom_FN:io.FileName, rom_checksums_FN, platform, status_dic):
        scraper_platform = convert_AKL_platform_to_GameFaqs(platform)
        self.logger.debug('GameFAQs.get_candidates() search_term      "{0}"'.format(search_term))
        self.logger.debug('GameFAQs.get_candidates() rom identifier   "{0}"'.format(rom.get_identifier()))
        self.logger.debug('GameFAQs.get_candidates() platform         "{0}"'.format(platform))
        self.logger.debug('GameFAQs.get_candidates() scraper_platform "{0}"'.format(scraper_platform))

        # Order list based on score
        game_list = self._get_candidates_from_page(search_term, platform, scraper_platform)
        game_list.sort(key = lambda result: result['order'], reverse = True)

        return game_list

    # --- Example URLs ---
    # https://gamefaqs.gamespot.com/snes/519824-super-mario-world
    def get_metadata(self, status_dic):
        # --- If scraper is disabled return immediately and silently ---
        if self.scraper_disabled:
            self.logger.debug('GameFAQs.get_metadata() Scraper disabled. Returning empty data.')
            return self._new_gamedata_dic()

        # --- Check if search term is in the cache ---
        if self._check_disk_cache(Scraper.CACHE_METADATA, self.cache_key):
            self.logger.debug('GameFAQs.get_metadata() Metadata cache hit "{}"'.format(self.cache_key))
            return self._retrieve_from_disk_cache(Scraper.CACHE_METADATA, self.cache_key)

        # --- Grab game information page ---
        cid = self.candidate['id']
        self.logger.debug(f'GameFAQs._scraper_get_metadata() Get metadata from {cid}')
        page_data, http_code = net.get_URL(f'{GameFAQs.base_url}/{cid}')
        self._dump_file_debug('GameFAQs_get_metadata.html', page_data)
        page_data = page_data.replace("\t", "").replace("\n", "")

        # --- Parse data ---
        game_year = self._parse_year(page_data)
        game_genre = self._parse_genre(page_data)
        game_developer = self._parse_developer(page_data)
        game_plot = self._parse_plot(page_data)
        game_esrb = self._parse_esrb(page_data)
        game_metacritics = self._parse_metacritics(page_data)
        game_rating = self._parse_rating(page_data)

        # get data page
        data_page_data, http_code = net.get_URL(f'{GameFAQs.base_url}/{cid}/data')
        data_page_data = data_page_data.replace("\t", "").replace("\n", "")

        game_nplayers = self._parse_nplayers(data_page_data)
        game_nplayers_online = self._parse_nplayers_online(data_page_data)

        # --- Build metadata dictionary ---
        game_data = self._new_gamedata_dic()
        game_data['title'] = self.candidate['game_name']
        game_data['year'] = game_year
        game_data['genre'] = game_genre
        game_data['developer'] = game_developer
        game_data['rating'] = game_rating
        game_data['nplayers'] = game_nplayers
        game_data['nplayers_online'] = game_nplayers_online
        game_data['esrb'] = game_esrb
        game_data['plot'] = game_plot
        game_data['extra']['gamefaq_id'] = cid 
        game_data['extra'].update(game_metacritics)

        # --- Put metadata in the cache ---
        self.logger.debug(f'GameFAQs.get_metadata() Adding to metadata cache "{self.cache_key}"')
        self._update_disk_cache(Scraper.CACHE_METADATA, self.cache_key, game_data)

        return game_data

    def get_assets(self, asset_info_id: str, status_dic):
         # --- If scraper is disabled return immediately and silently ---
        if self.scraper_disabled:
            self.logger.debug('GameFAQs.get_assets() Scraper disabled. Returning empty data.')
            return []

        # Get all assets for candidate. _scraper_get_assets_all() caches all assets for a candidate.
        # Then select asset of a particular type.
        all_asset_list = self._retrieve_all_assets(self.candidate, status_dic)
        if not status_dic['status']:
            return None
        
        asset_list = [asset_dic for asset_dic in all_asset_list if asset_dic['asset_ID'] == asset_info_id]
        self.logger.debug(f'GameFAQs: Total assets {len(all_asset_list)} / Returned assets {len(asset_list)}')

        return asset_list

    # In GameFAQs the candidate['url'] field is the URL of the image page.
    # For screenshots, the image page contains one image (the screenshot).
    # For boxart, the image page contains boxfront, boxback and spine.
    #
    # Boxart examples:
    # https://gamefaqs.gamespot.com/snes/519824-super-mario-world/images/158851
    # https://gamefaqs.gamespot.com/snes/588741-super-metroid/images/149897
    #
    # Screenshot examples:
    # https://gamefaqs.gamespot.com/snes/519824-super-mario-world/images/21
    # https://gamefaqs.gamespot.com/snes/519824-super-mario-world/images/29
    def resolve_asset_URL(self, selected_asset, status_dic):
        url = f"{GameFAQs.base_url}{selected_asset['url']}"
        asset_id = selected_asset['asset_ID']
        self.logger.debug(f'GameFAQs._scraper_resolve_asset_URL() Get image from "{url}" for asset type {asset_id}')
        page_data, http_code = net.get_URL(url)
        
        self._dump_json_debug('GameFAQs_scraper_resolve_asset_URL.html', page_data)
        page_data = page_data.replace("\t", "").replace("\n", "")

        images_on_page = self.regex_asset_urls.finditer(page_data)
        for image_data in images_on_page:
            image_on_page = image_data.groupdict()
            image_asset_ids = self._parse_asset_type(image_on_page['alt'])
            self.logger.debug('Found "{}" of types {} with url {}'.format(image_on_page['alt'], image_asset_ids, image_on_page['url']))
            if asset_id in image_asset_ids:
                self.logger.debug('GameFAQs._scraper_resolve_asset_URL() Found match {}'.format(image_on_page['alt']))
                return image_on_page['url'], image_on_page['url']
        self.logger.debug('GameFAQs._scraper_resolve_asset_URL() No correct match')

        return '', ''

    # NOT IMPLEMENTED YET.
    def resolve_asset_URL_extension(self, selected_asset, image_url, status_dic):
        return io.get_URL_extension(image_url)

    # --- This class own methods -----------------------------------------------------------------
    def _parse_asset_type(self, header):
        if 'Screenshots' in header:
            return [constants.ASSET_SNAP_ID, constants.ASSET_TITLE_ID]
        elif 'Box Back' in header:
            return [constants.ASSET_BOXBACK_ID]
        elif 'Box Front' in header:
            return [constants.ASSET_BOXFRONT_ID]
        elif 'Box' in header:
            return [constants.ASSET_BOXFRONT_ID, constants.ASSET_BOXBACK_ID]
        elif 'Video' in header:
            return None

        return [constants.ASSET_SNAP_ID]

    # Deactivate the recursive search with no platform if no games found with platform.
    # Could be added later.
    def _get_candidates_from_page(self, search_term, platform, scraper_platform, url = None, session = None):
        # --- Get URL data as a text string ---
        if session is None:
            session = net.start_http_session()
            session.headers.update({ 'User-Agent': net.USER_AGENT })
            session.cookies.set('OptanonConsent', 'AwaitingReconsent=false', domain=".gamespot.com")

        if url is None:
            url = f'{GameFAQs.base_url}/search_advanced?game={search_term}'
            page_data, http_code = net.get_URL(url, session=session)

            data = urlencode({'game_type': 0, 'game': search_term, 'platform': scraper_platform})
            page_data, http_code = net.post_URL(url, data, session=session)
        else:
            page_data, http_code = net.get_URL(url, session=session)
        
        if http_code != 200:
            self.logger.error(f"Failure retrieving URL {url}")

        self._dump_file_debug('GameFAQs_get_candidates.html', page_data)
        page_data = page_data.replace("\t", "").replace("\n", "")
        # --- Parse game list ---
        # --- First row ---
        # <div class="sr_cell sr_platform">Platform</div>
        # <div class="sr_cell sr_title">Game</div>
        # <div class="sr_cell sr_release">Release</div>
        #
        # --- Game row ---
        # <div class="sr_cell sr_platform">SNES</div>
        # <div class="sr_cell sr_title"><a class="log_search" data-row="1" data-col="1" data-pid="519824" href="/snes/519824-super-mario-world">Super Mario World</a></div>
        # <div class="sr_cell sr_release">1990</div>
        regex_results = self.regex_candidates.findall(page_data, re.MULTILINE)
        game_list = []
        for result in regex_results:
            game = self._new_candidate_dic()
            game_platform = result[0]
            alt_game_platform = result[2].split('/')[1]
            game_year = result[4]
            game_name = text.unescape_HTML(result[3])
            if game_platform.lower() in AKL_compact_platform_GameFaqs_mapping:
                platform_id = AKL_compact_platform_GameFaqs_mapping[game_platform.lower()]
            elif alt_game_platform in AKL_compact_platform_GameFaqs_mapping:
                platform_id = AKL_compact_platform_GameFaqs_mapping[alt_game_platform]
            else:
                platform_id = 0

            game['id']               = result[1]
            game['display_name']     = f"{game_name} ({game_year}) / {game_platform}"
            game['platform']         = platform_id
            game['scraper_platform'] = scraper_platform
            game['order']            = 1
            game['game_name']        = game_name # Additional GameFAQs scraper field
            
            # Increase search score based on our own search.
            # In the future use an scoring algortihm based on Levenshtein distance.
            title = game_name
            if title.lower() == search_term.lower():
                game['order'] += 1
            if title.lower().find(search_term.lower()) != -1:
                game['order'] += 1
            if scraper_platform > 0 and platform_id == scraper_platform:
                game['order'] += 1
            game_list.append(game)

        # --- Recursively load more games ---
        # Deactivate for now, just get all the games on the first page which should be
        # more than enough.
        # next_page_result = re.findall('<li><a href="(\S*?)">Next Page\s<i', page_data, re.MULTILINE)
        # if len(next_page_result) > 0:
        #     link = next_page_result[0].replace('&amp;', '&')
        #     new_url = 'https://gamefaqs.gamespot.com' + link
        #     game_list = game_list + self._get_candidates_from_page(search_term, no_platform, new_url)

        # --- Sort game list based on the score ---
        game_list.sort(key = lambda result: result['order'], reverse = True)
        return game_list
              
    #
    # Functions to parse metadata from game web page.
    #
    def _parse_year(self, page_data):
        # <li><b>Release:</b> <a href="/snes/519824-super-mario-world/data">August 13, 1991</a></li>
        # <li><b>Release:</b> <a href="/snes/588699-street-fighter-alpha-2/data">November 1996</a></li>
        m_date = self.regex_meta_year.search(page_data)
        game_year = ''
        if m_date:
            # Matches the year in the date string.
            date_str = m_date.group(1)
            m_year = re.search('\d\d\d\d', date_str)
            if m_year:
                game_year = m_year.group(0)

        return game_year
    
    def _parse_genre(self, page_data):
        # Parse only the first genre. Later versions will parse all the genres and return a list.
        # <li><b>Genre:</b> <a href="/snes/category/163-action-adventure">Action Adventure</a> &raquo; <a href="/snes/category/292-action-adventure-open-world">Open-World</a>
        m_genre = self.regex_meta_genre.search(page_data)
        if m_genre:
            return m_genre.group(1)
        return ''

    def _parse_developer(self, page_data):
        # --- Developer and publisher are the same
        # <li><b>Developer/Publisher: </b><a href="/company/2324-capcom">Capcom</a></li>
        # --- Developer and publisher separated
        # <li><b>Developer:</b> <a href="/company/45872-intelligent-systems">Intelligent Systems</a></li>
        # <li><b>Publisher:</b> <a href="/company/1143-nintendo">Nintendo</a></li>
        m_dev_a = self.regex_meta_dev_a.search(page_data)
        m_dev_b = self.regex_meta_dev_b.search(page_data)
        if m_dev_a:
            game_developer = m_dev_a.group(1)
        elif m_dev_b:
            game_developer = m_dev_b.group(1)
        else:
            game_developer = ''
        return game_developer

    def _parse_plot(self, page_data):
        # <script type="application/ld+json">
        # {
        #     "name":"Super Metroid",
        #     "description":"Take on a legion of Space Pirates ....",
        #     "keywords":"" }
        # </script>
        m_plot = self.regex_meta_plot.search(page_data)
        if m_plot:
            plot_str = m_plot.group(1)
            plot_str = text.remove_HTML_tags(plot_str)
            return plot_str
        return ''
            
    def _parse_nplayers(self, page_data):
        # <div class="content">
        #     <span class="bold">Local Players:</span>&nbsp;
        #     <span>1 Player</span>
        # </div>
        m_players = self.regex_meta_nplayers.search(page_data)
        if not m_players:
            return constants.DEFAULT_META_NPLAYERS
        
        nplayers_str = m_players.group(1)
        nplayers_str = nplayers_str.replace(' Players', '')
        nplayers_str = nplayers_str.replace(' Player', '')

        if nplayers_str.isnumeric():
            return nplayers_str

        match = self.regex_num_of_player.search(nplayers_str)
        if match is None:
            return constants.DEFAULT_META_NPLAYERS
        nplayers_str = match.group(1)

        return nplayers_str
    
    def _parse_nplayers_online(self, page_data):
        # <div class="content">
            # <span class="bold">Online Players:</span>&nbsp;
            # <span>Up to 18 Players</span>
        # </div>
        m_players = self.regex_meta_nplayers_online.search(page_data)
        if not m_players:
            return constants.DEFAULT_META_NPLAYERS
        
        nplayers_str = m_players.group(1)
        nplayers_str = nplayers_str.replace(' Players', '')
        nplayers_str = nplayers_str.replace(' Player', '')
        nplayers_str = nplayers_str.replace('Up to ', '')

        if nplayers_str.isnumeric():
            return nplayers_str

        match = self.regex_num_of_player.search(nplayers_str)
        if match is None:
            return constants.DEFAULT_META_NPLAYERS
        nplayers_str = match.group(1)
        return nplayers_str

    def _parse_esrb(self, page_data):
        # <div class="esrb">
		#	<p><span title="Content is generally suitable for ... language." class="esrb_logo esrb_logo_e"></span></p>
		# </div>
        m_esrb = self.regex_meta_esrb.search(page_data)
        game_esrb = constants.ESRB_PENDING
        if m_esrb:
            esrb_code = m_esrb.group(1)
            esrb_code = esrb_code.replace('esrb_logo_', '')
            if esrb_code == 'e':
                game_esrb = constants.ESRB_EVERYONE
            elif esrb_code == 'ec':
                game_esrb = constants.ESRB_EARLY
            elif esrb_code == 'e10':
                game_esrb = constants.ESRB_EVERYONE_10
            elif esrb_code == 't':
                game_esrb = constants.ESRB_TEEN
            elif esrb_code == 'ao':
                game_esrb = constants.ESRB_ADULTS_ONLY
            elif esrb_code == 'm':
                game_esrb = constants.ESRB_MATURE
            else:
                game_esrb = constants.ESRB_PENDING
                
        return game_esrb
    
    def _parse_rating(self, page_data):
        # <div class="gamespace_rate_half" title="Average: 3.37 stars from 150 users">
        m_rating = self.regex_meta_rating.search(page_data)
        if not m_rating:
            return None
        
        return m_rating.group(1)
        
    def _parse_metacritics(self, page_data):
        # <div class="metacritic">
		# 	<div title="Metacritic" class="title"> </div>
		# 	<a href="https://www.metacritic.com/game/pc/cities-skylines?ftag=MCD-06-10aaa1c">
		# 		<div class="score score_high" title="Metascore from 60 critics">85</div>
		# 	</a>
		#	<a href="/pc/404404-cities-skylines-hotels-and-retreats/reviews#mc">more »</a>
		#</div>
        m_critics = self.regex_metacritic.search(page_data)
        if m_critics:
            critics_lnk = m_critics.group(1)
            critics_score = m_critics.group(2)
            return {
                'metacritics_link': critics_lnk,
                'metacritics': critics_score
            }
        return {}
    
    # Get ALL available assets for game.
    # Cache the results because this function may be called multiple times for the
    # same candidate game.
    def _retrieve_all_assets(self, candidate, status_dic):
        cache_key = str(candidate['id'])
        if cache_key in self.all_asset_cache:
            self.logger.debug('GameFaqs._retrieve_all_assets() Cache hit "{0}"'.format(cache_key))
            asset_list = self.all_asset_cache[cache_key]
        else:
            self.logger.debug('GameFaqs._retrieve_all_assets() Cache miss "{0}"'.format(cache_key))
            asset_list = self._load_assets_from_page(candidate)
            self.logger.debug('A total of {0} assets found for candidate ID {1}'.format(
                len(asset_list), candidate['id']))
            self.all_asset_cache[cache_key] = asset_list

        return asset_list
    
    # Load assets from assets web page.
    # The Game Images URL shows a page with boxart and screenshots thumbnails.
    # Boxart can be diferent depending on the ROM/game region. Each region has then a 
    # separate page with the full size artwork (boxfront, boxback, etc.)
    #
    # TODO In the assets web page only the Boxfront is shown. The Boxback and Spine are in the
    #      image web page. Currently I do not know how to solve this...
    #      The easiest thing to do is to support only Boxfront.
    #
    # https://gamefaqs.gamespot.com/snes/519824-super-mario-world/images
    # https://gamefaqs.gamespot.com/snes/588741-super-metroid/images
    # https://gamefaqs.gamespot.com/genesis/563316-chakan/images
    #
    # <div class="pod game_imgs">
    #   <div class="head"><h2 class="title">Game Box Shots</h2></div>
    #   <div class="body">
    #   <table class="contrib">
    #   <tr>
    #     <td class="thumb index:0 modded:0 iteration:1 modded:1">
    #       <div class="img boxshot">
    #         <a href="/genesis/563316-chakan/images/145463">
    #           <img class="img100 imgboxart" src="https://gamefaqs.akamaized.net/box/3/1/7/2317_thumb.jpg" alt="Chakan (US)" />
    #         </a>
    #         <div class="region">US 1992</div>
    #       </div>
    #     </td>
    #   ......
    #     <td></td>
    #   </tr>
    #   </table>
    #   </div>
    #   <div class="head"><h2 class="title">GameFAQs Reader Screenshots</h2></div>
    #   <div class="body"><table class="contrib">
    #   <tr>
    #     <td class="thumb">
    #     <a href="/genesis/563316-chakan/images/21">
    #       <img class="imgboxart" src="https://gamefaqs.akamaized.net/screens/f/c/b/gfs_45463_1_1_thm.jpg" />
    #     </a>
    #   </td>
    def _load_assets_from_page(self, candidate):
        cid = candidate['id']
        url = f'{GameFAQs.base_url}/{cid}/images'
        self.logger.debug('GameFAQs._load_assets_from_page() Get asset data from {}'.format(url))
        page_data, http_code = net.get_URL(url)

        self._dump_file_debug('GameFAQs_load_assets_from_page.html', page_data)
        page_data = page_data.replace("\t", "").replace("\n", "")

        # --- Parse all assets ---
        # findall() returns a list of strings OR a list of tuples of strings (re with groups).
        # This RE picks the contents inside the screenshoots tables.
        m_asset_blocks = self.regex_assets.findall(page_data)
        assets_list = []
        for asset_block in m_asset_blocks:
            asset_table_title = asset_block[0]
            asset_table_data = asset_block[2]
            self.logger.debug('Collecting assets from "{}"'.format(asset_table_title))
            
            # --- Depending on the table title select assets ---
            asset_infos = self._parse_asset_type(asset_table_title)
            
            if asset_infos is None:
                continue

            # --- Parse all image links in table ---
            # <a href="/nes/578318-castlevania/images/135454">
            # <img class="img100 imgboxart" src="https://gamefaqs.akamaized.net/box/2/7/6/2276_thumb.jpg" alt="Castlevania (US)" />
            # </a>
            block_items = self.regex_asset_links.finditer(asset_table_data)
            for m in block_items:
                image_data = m.groupdict()
                for asset_id in asset_infos:
                    # Title is usually the first or first snapshots in GameFAQs.
                    if asset_id == constants.ASSET_TITLE_ID and '&amp;img=1' not in image_data['lnk']:
                        continue
                    if asset_id == constants.ASSET_SNAP_ID and '&amp;img=1' in image_data['lnk']:
                        continue

                    asset_data = self._new_assetdata_dic()
                    asset_data['asset_ID']     = asset_id
                    asset_data['display_name'] = image_data['alt'] if image_data['alt'] else ''
                    asset_data['url_thumb']    = image_data['thumb']
                    asset_data['url']          = image_data['lnk']
                    asset_data['is_on_page']   = True
                    assets_list.append(asset_data)

        # --- Recursively load more image pages ---
        # Deactivated for now. Images on the first page should me more than enough.
        # next_page_result = re.findall('<li><a href="(\S*?)">Next Page\s<i', page_data, re.MULTILINE)
        # if len(next_page_result) > 0:
        #     new_url = 'https://gamefaqs.gamespot.com{}'.format(next_page_result[0])
        #     assets_list = assets_list + self._load_assets_from_url(new_url)

        return assets_list
    
# ------------------------------------------------------------------------------------------------
# GameFaqs supported platforms mapped to AKL platforms.
# ------------------------------------------------------------------------------------------------
DEFAULT_PLAT_GAMEFAQS = 0

def convert_AKL_platform_to_GameFaqs(platform_long_name) -> int:
    matching_platform = platforms.get_AKL_platform(platform_long_name)
    if matching_platform.compact_name in AKL_compact_platform_GameFaqs_mapping:
        return AKL_compact_platform_GameFaqs_mapping[matching_platform.compact_name]
    
    if matching_platform.aliasof is not None and matching_platform.aliasof in AKL_compact_platform_GameFaqs_mapping:
        return AKL_compact_platform_GameFaqs_mapping[matching_platform.aliasof]
        
    # Platform not found.
    return DEFAULT_PLAT_GAMEFAQS


def convert_GameFaqs_platform_to_AKL_platform(moby_platform) -> platforms.Platform:
    if moby_platform in GameFaqs_AKL_compact_platform_mapping:
        platform_compact_name = GameFaqs_AKL_compact_platform_mapping[moby_platform]
        return platforms.get_AKL_platform_by_compact(platform_compact_name)
        
    return platforms.get_AKL_platform_by_compact(platforms.PLATFORM_UNKNOWN_COMPACT)

AKL_compact_platform_GameFaqs_mapping = {
    '3do': 61,
    'cpc': 46,
    'a2600': 6,
    'a5200': 20,
    'a7800': 51,
    'jaguar': 72,
    'jaguarcd': 82,
    'lynx': 58,
    'atari-st': 38,
    'wswan': 90,
    'wswancolor': 95,
    'cvision': 29,
    'c64': 24,
    'amiga': 39,
    'cd32': 70,
    'vic20': 11,
    'fmtmarty': 55,
    'vectrex': 34,
    'odyssey2': 9,
    platforms.PLATFORM_MAME_COMPACT: 2,
    'ivision': 16,
    'msdos': 19,
    'msx': 40,
    'msx2': 40,
    'windows': 19,
    'xbox': 98,
    'xbox360': 111,
    'xboxone': 121,
    'pce': 53,
    'pcecd': 56,
    'pcfx': 79,
    'sgx': 53,
    'n3ds': 116,
    'n64': 84,
    'n64dd': 92,
    'nds': 108,
    'ndsi': 108,
    'fds': 47,
    'gb': 59,
    'gba': 91,
    'gbcolor': 57,
    'gamecube': 99,
    'nes': 41,
    'snes': 63,
    'switch': 124, 
    'vb': 83,
    'wii': 114, 
    'wiiu': 118,
    '32x': 74,
    'dreamcast': 67,
    'gamegear': 62,
    'sms': 49,
    'megadrive': 54,
    'genesis': 54,
    'megacd': 65,
    'saturn': 76,
    'sg1000': 43,
    'x68k': 52,
    'spectrum': 35,
    'neocd': 68,
    'ngpcolor': 89,
    'psx': 78,
    'ps2': 94,
    'ps3': 113,
    'ps4': 120,
    'psp': 109,
    'psvita': 117    
}

GameFaqs_AKL_compact_platform_mapping = {}
for key, value in AKL_compact_platform_GameFaqs_mapping.items():
    GameFaqs_AKL_compact_platform_mapping[value] = key