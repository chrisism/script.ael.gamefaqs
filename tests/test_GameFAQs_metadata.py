#!/usr/bin/python -B
# -*- coding: utf-8 -*-

# Test AEL GameFAQs metadata scraper.
#
# --- GameGAQs test URLs ---
# https://gamefaqs.gamespot.com/snes/519824-super-mario-world
# https://gamefaqs.gamespot.com/snes/588741-super-metroid
# https://gamefaqs.gamespot.com/snes/588699-street-fighter-alpha-2
# https://gamefaqs.gamespot.com/genesis/454495-sonic-the-hedgehog

# --- Python standard library ---
from __future__ import unicode_literals
import os
import unittest
import unittest.mock
import logging

logging.basicConfig(format = '%(asctime)s %(module)s %(levelname)s: %(message)s',
                datefmt = '%m/%d/%Y %I:%M:%S %p', level = logging.DEBUG)
logger = logging.getLogger(__name__)

from resources.lib.scraper import GameFAQs
from ael.utils import kodi, io
from ael import constants

# --- Test data -----------------------------------------------------------------------------------
games = {
    # Console games
    'metroid'                : ('Metroid', 'Metroid.zip', 'Nintendo SNES'),
    'mworld'                 : ('Super Mario World', 'Super Mario World.zip', 'Nintendo SNES'),
    'sonic_megaDrive'        : ('Sonic the Hedgehog', 'Sonic the Hedgehog (USA, Europe).zip', 'Sega Mega Drive'),
    'sonic_genesis'          : ('Sonic the Hedgehog', 'Sonic the Hedgehog (USA, Europe).zip', 'Sega Genesis'),
    'chakan'                 : ('Chakan', 'Chakan (USA, Europe).zip', 'Sega MegaDrive'),
    'ff7'                    : ('Final Fantasy VII', 'Final Fantasy VII (USA) (Disc 1).iso', 'Sony PlayStation'),
    'console_wrong_title'    : ('Console invalid game', 'mjhyewqr.zip', 'Sega MegaDrive'),
    'console_wrong_platform' : ('Sonic the Hedgehog', 'Sonic the Hedgehog (USA, Europe).zip', 'mjhyewqr'),

    # MAME games
    'atetris'             : ('Tetris (set 1)', 'atetris.zip', 'MAME'),
    'mslug'               : ('Metal Slug - Super Vehicle-001', 'mslug.zip', 'MAME'),
    'dino'                : ('Cadillacs and Dinosaurs (World 930201)', 'dino.zip', 'MAME'),
    'MAME_wrong_title'    : ('MAME invalid game', 'mjhyewqr.zip', 'MAME'),
    'MAME_wrong_platform' : ('Tetris (set 1)', 'atetris.zip', 'mjhyewqr'),
}

class Test_gamefaq_metadata_and_assets(unittest.TestCase):
    
    def test_gamefaq_metadata(self):   
        # --- main ---------------------------------------------------------------------------------------
        print('*** Fetching candidate game list ********************************************************')

        # --- Create scraper object ---
        scraper_obj = GameFAQs()
        scraper_obj.set_verbose_mode(False)
        scraper_obj.set_debug_file_dump(True, os.path.join(os.path.dirname(__file__), 'assets'))
        status_dic = kodi.new_status_dic('Scraper test was OK')

        # --- Choose data for testing ---
        # search_term, rombase, platform = common.games['metroid']
        # search_term, rombase, platform = common.games['mworld']
        #search_term, rombase, platform = common.games['sonic_megaDrive']
        search_term, rombase, platform = games['sonic_genesis'] # Aliased platform
        # search_term, rombase, platform = common.games['chakan']
        # search_term, rombase, platform = common.games['console_wrong_title']
        # search_term, rombase, platform = common.games['console_wrong_platform']

        # --- Get candidates, print them and set first candidate ---
        rom_FN = io.FileName(rombase)
        rom_checksums_FN = io.FileName(rombase)
        if scraper_obj.check_candidates_cache(rom_FN, platform):
            print('>>>> Game "{}" "{}" in disk cache.'.format(rom_FN.getBase(), platform))
        else:
            print('>>>> Game "{}" "{}" not in disk cache.'.format(rom_FN.getBase(), platform))
        candidate_list = scraper_obj.get_candidates(search_term, rom_FN, rom_checksums_FN, platform, status_dic)
        # pprint.pprint(candidate_list)
        self.assertTrue(status_dic['status'], 'Status error "{}"'.format(status_dic['msg']))
        self.assertIsNotNone(candidate_list, 'Error/exception in get_candidates()')
        self.assertNotEquals(len(candidate_list), 0, 'No candidates found.')
        
        for candidate in candidate_list:
            print(candidate)
            
        scraper_obj.set_candidate(rom_FN, platform, candidate_list[0])

        # --- Print metadata of first candidate ----------------------------------------------------------
        print('*** Fetching game metadata **************************************************************')
        metadata = scraper_obj.get_metadata(status_dic)
        # pprint.pprint(metadata)
        print(metadata)
        scraper_obj.flush_disk_cache()

    def test_gamefaq_assets(self):
        # --- main ---------------------------------------------------------------------------------------
        print('*** Fetching candidate game list ********************************************************')
        
        # --- Create scraper object ---
        scraper_obj = GameFAQs()
        scraper_obj.set_verbose_mode(False)
        scraper_obj.set_debug_file_dump(True, os.path.join(os.path.dirname(__file__), 'assets'))
        status_dic = kodi.new_status_dic('Scraper test was OK')

        # --- Choose data for testing ---
        # search_term, rombase, platform = common.games['metroid']
        # search_term, rombase, platform = common.games['mworld']
        #search_term, rombase, platform = common.games['sonic_megaDrive']
        search_term, rombase, platform = games['sonic_genesis'] # Aliased platform
        # search_term, rombase, platform = common.games['chakan']
        # search_term, rombase, platform = common.games['console_wrong_title']
        # search_term, rombase, platform = common.games['console_wrong_platform']

        # --- Get candidates, print them and set first candidate ---
        rom_FN = io.FileName(rombase)
        rom_checksums_FN = io.FileName(rombase)
        if scraper_obj.check_candidates_cache(rom_FN, platform):
            print('>>>> Game "{}" "{}" in disk cache.'.format(rom_FN.getBase(), platform))
        else:
            print('>>>> Game "{}" "{}" not in disk cache.'.format(rom_FN.getBase(), platform))
        candidate_list = scraper_obj.get_candidates(search_term, rom_FN, rom_checksums_FN, platform, status_dic)
        # pprint.pprint(candidate_list)
        self.assertTrue(status_dic['status'], 'Status error "{}"'.format(status_dic['msg']))
        self.assertIsNotNone(candidate_list, 'Error/exception in get_candidates()')
        self.assertNotEquals(len(candidate_list), 0, 'No candidates found.')
        
        for candidate in candidate_list:
            print(candidate)
            
        scraper_obj.set_candidate(rom_FN, platform, candidate_list[0])

        # --- Print list of assets found -----------------------------------------------------------------
        print('*** Fetching game assets ****************************************************************')
        self.print_game_assets(scraper_obj.get_assets(constants.ASSET_TITLE_ID, status_dic))
        self.print_game_assets(scraper_obj.get_assets(constants.ASSET_SNAP_ID, status_dic))
        self.print_game_assets(scraper_obj.get_assets(constants.ASSET_BOXFRONT_ID, status_dic))
        self.print_game_assets(scraper_obj.get_assets(constants.ASSET_BOXBACK_ID, status_dic))
        scraper_obj.flush_disk_cache()
        
    def print_game_assets(self, assets):
        for asset in assets:
            print(asset)