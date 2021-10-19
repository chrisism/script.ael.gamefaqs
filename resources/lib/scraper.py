# -*- coding: utf-8 -*-
#
# Advanced Emulator Launcher scraping engine for GameFAQs.

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

import logging
import re

# --- AEL packages ---
from ael import constants, settings
from ael.utils import io, net
from ael.scrapers import Scraper

logger = logging.getLogger(__name__)

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

    # --- Constructor ----------------------------------------------------------------------------
    def __init__(self):
        self.cache_candidates = {}
        self.cache_metadata = {}
        self.cache_assets = {}
        self.all_asset_cache = {}
        
        cache_dir = settings.getSetting('scraper_cache_dir')
        super(GameFAQs, self).__init__(cache_dir)

    # --- Base class abstract methods ------------------------------------------------------------
    
    def get_name(self): return 'GameFAQs'

    def get_filename(self): return 'GameFAQs'

    def supports_disk_cache(self): return True

    def supports_search_string(self): return True

    def supports_metadata_ID(self, metadata_ID):
        return True if metadata_ID in GameFAQs.supported_metadata_list else False

    def supports_metadata(self): return True

    def supports_asset_ID(self, asset_ID):
        return True if asset_ID in GameFAQs.supported_asset_list else False

    def supports_assets(self): return True
    
    # GameFAQs does not require any API keys. By default status_dic is configured for successful
    # operation so return it as it is.
    def check_before_scraping(self, status_dic): return status_dic

    def get_candidates(self, search_term, rom_FN:io.FileName, rom_checksums_FN, platform, status_dic):
        scraper_platform = AEL_platform_to_GameFAQs(platform)
        rombase_noext = rom_FN.getBaseNoExt()
        logger.debug('GameFAQs.get_candidates() search_term      "{0}"'.format(search_term))
        logger.debug('GameFAQs.get_candidates() rombase_noext    "{0}"'.format(rombase_noext))
        logger.debug('GameFAQs.get_candidates() platform         "{0}"'.format(platform))
        logger.debug('GameFAQs.get_candidates() scraper_platform "{0}"'.format(scraper_platform))

        # Order list based on score
        game_list = self._get_candidates_from_page(search_term, platform, scraper_platform)
        game_list.sort(key = lambda result: result['order'], reverse = True)

        return game_list

    # --- Example URLs ---
    # https://gamefaqs.gamespot.com/snes/519824-super-mario-world
    def get_metadata(self, status_dic):
        # --- Grab game information page ---
        logger.debug('GameFAQs._scraper_get_metadata() Get metadata from {}'.format(self.candidate['id']))
        url = 'https://gamefaqs.gamespot.com{}'.format(self.candidate['id'])
        page_data = net.get_URL(url)
        self._dump_file_debug('GameFAQs_get_metadata.html', page_data)

        # --- Parse data ---
        game_year      = self._parse_year(page_data)
        game_genre     = self._parse_genre(page_data)
        game_developer = self._parse_developer(page_data)
        game_plot      = self._parse_plot(page_data)

        # --- Build metadata dictionary ---
        game_data = self._new_gamedata_dic()
        game_data['title']     = self.candidate['game_name']
        game_data['year']      = game_year
        game_data['genre']     = game_genre
        game_data['developer'] = game_developer
        game_data['nplayers']  = ''
        game_data['esrb']      = ''
        game_data['plot']      = game_plot

        return game_data

    def get_assets(self, asset_info, status_dic):
        # logger.debug('GameFAQs::_scraper_get_assets() asset_ID = {0} ...'.format(asset_ID))
        # Get all assets for candidate. _scraper_get_assets_all() caches all assets for a candidate.
        # Then select asset of a particular type.
        all_asset_list = self._scraper_get_assets_all(candidate, status_dic)
        asset_list = [asset_dic for asset_dic in all_asset_list if asset_dic['asset_ID'] == asset_info.id]
        logger.debug('GameFAQs::_scraper_get_assets() Total assets {0} / Returned assets {1}'.format(
            len(all_asset_list), len(asset_list)))

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
    def resolve_asset_URL(self, candidate, status_dic):
        url = 'https://gamefaqs.gamespot.com{}'.format(candidate['url'])
        logger.debug('GameFAQs._scraper_resolve_asset_URL() Get image from "{}" for asset type {}'.format(
            url, asset_info.name))
        page_data = net.get_URL(url)
        self._dump_json_debug('GameFAQs_scraper_resolve_asset_URL.html', page_data)

        r_str = '<img (class="full_boxshot cte" )?data-img-width="\d+" data-img-height="\d+" data-img="(?P<url>.+?)" (class="full_boxshot cte" )?src=".+?" alt="(?P<alt>.+?)"(\s/)?>'
        images_on_page = re.finditer(r_str, page_data)
        for image_data in images_on_page:
            image_on_page = image_data.groupdict()
            image_asset_ids = self._parse_asset_type(image_on_page['alt'])
            logger.debug('Found "{}" of types {} with url {}'.format(image_on_page['alt'], image_asset_ids, image_on_page['url']))
            if asset_info.id in image_asset_ids:
                logger.debug('GameFAQs._scraper_resolve_asset_URL() Found match {}'.format(image_on_page['alt']))
                return image_on_page['url']
        logger.debug('GameFAQs._scraper_resolve_asset_URL() No correct match')

        return '', ''

    # NOT IMPLEMENTED YET.
    def resolve_asset_URL_extension(self, candidate, image_url, status_dic): return None

    # --- This class own methods -----------------------------------------------------------------
    def _parse_asset_type(self, header):
        if 'Screenshots' in header: return [constants.ASSET_SNAP_ID, constants.ASSET_TITLE_ID]
        elif 'Box Back' in header:  return [constants.ASSET_BOXBACK_ID]
        elif 'Box Front' in header: return [constants.ASSET_BOXFRONT_ID]
        elif 'Box' in header:       return [constants.ASSET_BOXFRONT_ID, constants.ASSET_BOXBACK_ID]

        return [constants.ASSET_SNAP_ID]

    # Deactivate the recursive search with no platform if no games found with platform.
    # Could be added later.
    def _get_candidates_from_page(self, search_term, platform, scraper_platform, url = None):
        # --- Get URL data as a text string ---
        if url is None:
            url = 'https://gamefaqs.gamespot.com/search_advanced'
            data = urllib.urlencode({'game': search_term, 'platform': scraper_platform})
            page_data = net_post_URL(url, data)
        else:
            page_data = net_get_URL(url)
        self._dump_file_debug('GameFAQs_get_candidates.html', page_data)

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
        r = r'<div class="sr_cell sr_platform">(.*?)</div>\s*<div class="sr_cell sr_title"><a class="log_search" data-row="[0-9]+" data-col="1" data-pid="[0-9]+" href="(.*?)">(.*?)</a></div>'
        regex_results = re.findall(r, page_data, re.MULTILINE)
        game_list = []
        for result in regex_results:
            game = self._new_candidate_dic()
            game_platform = result[0]
            game_id       = result[1]
            game_name     = text_unescape_HTML(result[2])
            game['id']               = result[1]
            game['display_name']     = game_name + ' / ' + game_platform.capitalize()
            game['platform']         = platform
            game['scraper_platform'] = scraper_platform
            game['order']            = 1
            game['game_name']        = game_name # Additional GameFAQs scraper field
            # Skip first row of the games table.
            if game_name == 'Game': continue
            # Increase search score based on our own search.
            # In the future use an scoring algortihm based on Levenshtein distance.
            title = game_name
            if title.lower() == search_term.lower():          game['order'] += 1
            if title.lower().find(search_term.lower()) != -1: game['order'] += 1
            if platform > 0 and game_platform == platform:    game['order'] += 1
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
        re_str = '<li><b>Release:</b> <a href=".*?">(.*?)</a></li>'
        m_date = re.search(re_str, page_data)
        game_year = ''
        if m_date:
            # Matches the year in the date string.
            date_str = m_date.group(1)
            m_year = re.search('\d\d\d\d', date_str)
            if m_year: game_year = m_year.group(0)

        return game_year
    
    def _parse_genre(self, page_data):
        # Parse only the first genre. Later versions will parse all the genres and return a list.
        # <li><b>Genre:</b> <a href="/snes/category/163-action-adventure">Action Adventure</a> &raquo; <a href="/snes/category/292-action-adventure-open-world">Open-World</a>
        m_genre = re.search('<li><b>Genre:</b> <a href=".*?">(.*?)</a>', page_data)
        if m_genre: game_genre = m_genre.group(1)

        return game_genre

    def _parse_developer(self, page_data):
        # --- Developer and publisher are the same
        # <li><b>Developer/Publisher: </b><a href="/company/2324-capcom">Capcom</a></li>
        # --- Developer and publisher separated
        # <li><b>Developer:</b> <a href="/company/45872-intelligent-systems">Intelligent Systems</a></li>
        # <li><b>Publisher:</b> <a href="/company/1143-nintendo">Nintendo</a></li>
        m_dev_a = re.search('<li><b>Developer/Publisher: </b><a href=".*?">(.*?)</a></li>', page_data)
        m_dev_b = re.search('<li><b>Developer: </b><a href=".*?">(.*?)</a></li>', page_data)
        if   m_dev_a: game_developer = m_dev_a.group(1)
        elif m_dev_b: game_developer = m_dev_b.group(1)
        else:         game_developer = ''

        return game_developer

    def _parse_plot(self, page_data):
        # <script type="application/ld+json">
        # {
        #     "name":"Super Metroid",
        #     "description":"Take on a legion of Space Pirates ....",
        #     "keywords":"" }
        # </script>
        m_plot = re.search('"description":"(.*?)",', page_data)
        if m_plot: game_plot = m_plot.group(1)

        return game_plot
        
    # Get ALL available assets for game.
    # Cache the results because this function may be called multiple times for the
    # same candidate game.
    def _scraper_get_assets_all(self, candidate, status_dic):
        cache_key = str(candidate['id'])
        if cache_key in self.all_asset_cache:
            logger.debug('MobyGames._scraper_get_assets_all() Cache hit "{0}"'.format(cache_key))
            asset_list = self.all_asset_cache[cache_key]
        else:
            logger.debug('MobyGames._scraper_get_assets_all() Cache miss "{0}"'.format(cache_key))
            asset_list = self._load_assets_from_page(candidate)
            logger.debug('A total of {0} assets found for candidate ID {1}'.format(
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
        url = 'https://gamefaqs.gamespot.com{}/images'.format(candidate['id'])
        logger.debug('GameFAQs._scraper_get_assets_all() Get asset data from {}'.format(url))
        page_data = net_get_URL(url)
        self._dump_file_debug('GameFAQs_load_assets_from_page.html', page_data)

        # --- Parse all assets ---
        # findall() returns a list of strings OR a list of tuples of strings (re with groups).
        # This RE picks the contents inside the screenshoots tables.
        r_str = '<div class="head"><h2 class="title">([\w\s]+?)</h2></div><div class="body"><table class="contrib">(.*?)</table></div>'
        m_asset_blocks = re.findall(r_str, page_data)
        assets_list = []
        for asset_block in m_asset_blocks:
            asset_table_title = asset_block[0]
            asset_table_data = asset_block[1]
            logger.debug('Collecting assets from "{}"'.format(asset_table_title))
            
            # --- Depending on the table title select assets ---
            title_snap_taken = True
            if 'Box' in asset_table_title:
                asset_infos = [ASSET_BOXFRONT_ID, ASSET_BOXBACK_ID]
            # Title is usually the first or first snapshots in GameFAQs.
            elif 'Screenshots' in asset_table_title:
                asset_infos = [ASSET_SNAP_ID]
                if not('?page=' in url):
                    asset_infos.append(ASSET_TITLE_ID)
                    title_snap_taken = False

            # --- Parse all image links in table ---
            # <a href="/nes/578318-castlevania/images/135454">
            # <img class="img100 imgboxart" src="https://gamefaqs.akamaized.net/box/2/7/6/2276_thumb.jpg" alt="Castlevania (US)" />
            # </a>
            r_str = '<a href="(?P<lnk>.+?)"><img class="(img100\s)?imgboxart" src="(?P<thumb>.+?)" (alt="(?P<alt>.+?)")?\s?/></a>'
            block_items = re.finditer(r_str, asset_table_data)
            for m in block_items:
                image_data = m.groupdict()
                # log_variable('image_data', image_data)
                for asset_id in asset_infos:
                    if asset_id == ASSET_TITLE_ID and title_snap_taken: continue
                    if asset_id == ASSET_TITLE_ID: title_snap_taken = True
                    asset_data = self._new_assetdata_dic()
                    asset_data['asset_ID']     = asset_id
                    asset_data['display_name'] = image_data['alt'] if image_data['alt'] else ''
                    asset_data['url_thumb']    = image_data['thumb']
                    asset_data['url']          = image_data['lnk']
                    asset_data['is_on_page']   = True
                    assets_list.append(asset_data)
                    # log_variable('asset_data', asset_data)

        # --- Recursively load more image pages ---
        # Deactivated for now. Images on the first page should me more than enough.
        # next_page_result = re.findall('<li><a href="(\S*?)">Next Page\s<i', page_data, re.MULTILINE)
        # if len(next_page_result) > 0:
        #     new_url = 'https://gamefaqs.gamespot.com{}'.format(next_page_result[0])
        #     assets_list = assets_list + self._load_assets_from_url(new_url)

        return assets_list
    