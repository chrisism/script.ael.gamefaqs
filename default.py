# -*- coding: utf-8 -*-
#
# GameFaqs Scraper for AKL
#
# --- Python standard library ---
from __future__ import unicode_literals
from __future__ import division

import sys
import argparse
import logging
import json
    
# --- Kodi stuff ---
import xbmcaddon

# AKL main imports
from akl import constants
from akl.utils import kodilogging, io, kodi
from akl.scrapers import ScraperSettings, ScrapeStrategy

# Local modules
from resources.lib.scraper import GameFAQs

kodilogging.config()
logger = logging.getLogger(__name__)

# --- Addon object (used to access settings) ---
addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_version = addon.getAddonInfo('version')


# ---------------------------------------------------------------------------------------------
# This is the plugin entry point.
# ---------------------------------------------------------------------------------------------
def run_plugin():
    os_name = io.is_which_os()
    
    # --- Some debug stuff for development ---
    logger.info('------------ Called Advanced Kodi Launcher Plugin: GameFAQs Scraper ------------')
    logger.info(f'addon.id         "{addon_id}"')
    logger.info(f'addon.version    "{addon_version}"')
    logger.info(f'sys.platform     "{sys.platform}"')
    logger.info(f'OS               "{os_name}"')
    
    for i in range(len(sys.argv)):
        logger.info(f'sys.argv[{i}] "{sys.argv[i]}"')

    parser = argparse.ArgumentParser(prog='script.akl.mobygames')
    parser.add_argument('--cmd', help="Command to execute", choices=['launch', 'scan', 'scrape', 'configure'])
    parser.add_argument('--type', help="Plugin type", choices=['LAUNCHER', 'SCANNER', 'SCRAPER'], default=constants.AddonType.LAUNCHER.name)
    parser.add_argument('--server_host', type=str, help="Host")
    parser.add_argument('--server_port', type=int, help="Port")
    parser.add_argument('--rom_id', type=str, help="ROM ID")
    parser.add_argument('--romcollection_id', type=str, help="ROM Collection ID")
    parser.add_argument('--source_id', type=str, help="Source ID")
    parser.add_argument('--entity_id', type=str, help="Entity ID")
    parser.add_argument('--entity_type', type=int, help="Entity Type (ROM|ROMCOLLECTION|SOURCE)")
    parser.add_argument('--akl_addon_id', type=str, help="Addon configuration ID")
    parser.add_argument('--settings', type=json.loads, help="Specific run setting")
    
    try:
        args = parser.parse_args()
    except Exception as ex:
        logger.error('Exception in plugin', exc_info=ex)
        kodi.dialog_OK(text=parser.usage)
        return
        
    if args.type == constants.AddonType.SCRAPER.name and args.cmd == 'scrape':
        run_scraper(args)
    else:
        kodi.dialog_OK(text=parser.format_help())
        
    logger.debug('Advanced Kodi Launcher Plugin: GameFAQs Scraper -> exit')


# ---------------------------------------------------------------------------------------------
# Scraper methods.
# ---------------------------------------------------------------------------------------------
def run_scraper(args):
    logger.debug('========== run_scraper() BEGIN ==================================================')
    pdialog = kodi.ProgressDialog()
    
    settings = ScraperSettings.from_settings_dict(args.settings)
    scraper_strategy = ScrapeStrategy(
        args.server_host,
        args.server_port,
        settings,
        GameFAQs(),
        pdialog)
    
    if args.entity_type == constants.OBJ_ROM:
        scraped_rom = scraper_strategy.process_single_rom(args.entity_id)
        pdialog.endProgress()
        pdialog.startProgress('Saving ROM in database ...')
        scraper_strategy.store_scraped_rom(args.akl_addon_id, args.entity_id, scraped_rom)
        pdialog.endProgress()
    else:
        scraped_roms = scraper_strategy.process_roms(args.entity_type, args.entity_id)
        pdialog.endProgress()
        pdialog.startProgress('Saving ROMs in database ...')
        scraper_strategy.store_scraped_roms(args.akl_addon_id, args.entity_type, args.entity_id, scraped_roms)
        pdialog.endProgress()


# ---------------------------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------------------------
try:
    run_plugin()
except Exception as ex:
    logger.fatal('Exception in plugin', exc_info=ex)
    kodi.notify_error("General failure")
