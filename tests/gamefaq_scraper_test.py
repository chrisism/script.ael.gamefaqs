import unittest, os
import unittest.mock
from unittest.mock import MagicMock, patch

import json
import logging

from fakes import FakeProgressDialog, random_string

logging.basicConfig(format = '%(asctime)s %(module)s %(levelname)s: %(message)s',
                datefmt = '%m/%d/%Y %I:%M:%S %p', level = logging.DEBUG)
logger = logging.getLogger(__name__)

from resources.lib.scraper import GameFAQs
from ael.scrapers import ScrapeStrategy, ScraperSettings

from ael.api import ROMObj
from ael import constants
from ael.utils import net
        
def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def mocked_gamesfaq(url, params = None):

    mocked_html_file = ''

    if '/search' in url:
        mocked_html_file = Test_gamefaq_scraper.TEST_ASSETS_DIR + "\\gamesfaq_search.html"
        
    elif '/578318-castlevania/images/21' in url:
        mocked_html_file = Test_gamefaq_scraper.TEST_ASSETS_DIR + "\\gamesfaq_castlevania_snap.html"
        
    elif '/578318-castlevania/images/135454' in url:
        mocked_html_file = Test_gamefaq_scraper.TEST_ASSETS_DIR + "\\gamesfaq_castlevania_boxfront.html"

    elif '/578318-castlevania/images' in url:
        mocked_html_file = Test_gamefaq_scraper.TEST_ASSETS_DIR + "\\gamesfaq_castlevania_images.html"
        
    elif '/578318-castlevania' in url:
        mocked_html_file = Test_gamefaq_scraper.TEST_ASSETS_DIR + "\\gamesfaq_castlevania.html"

    elif '.jpg' in url:
        print('reading fake image file')
        return read_file(Test_gamefaq_scraper.TEST_ASSETS_DIR + "\\test.jpg")

    if mocked_html_file == '':
        return net.get_URL_oneline(url)

    print ('reading mocked data from file: {}'.format(mocked_html_file))
    return read_file(mocked_html_file)

class Test_gamefaq_scraper(unittest.TestCase):
    
    ROOT_DIR = ''
    TEST_DIR = ''
    TEST_ASSETS_DIR = ''

    @classmethod
    def setUpClass(cls):
        cls.TEST_DIR = os.path.dirname(os.path.abspath(__file__))
        cls.ROOT_DIR = os.path.abspath(os.path.join(cls.TEST_DIR, os.pardir))
        cls.TEST_ASSETS_DIR = os.path.abspath(os.path.join(cls.TEST_DIR,'assets/'))
                
        print('ROOT DIR: {}'.format(cls.ROOT_DIR))
        print('TEST DIR: {}'.format(cls.TEST_DIR))
        print('TEST ASSETS DIR: {}'.format(cls.TEST_ASSETS_DIR))
        print('---------------------------------------------------------------------------')
        
    @patch('resources.lib.scraper.net.get_URL', side_effect = mocked_gamesfaq)
    @patch('resources.lib.scraper.net.post_URL', side_effect = mocked_gamesfaq)
    @patch('ael.api.client_get_rom')
    def test_scraping_metadata_for_game(self, api_rom_mock: MagicMock, mock_post, mock_get):        
        # arrange
        settings = ScraperSettings()
        settings.scrape_metadata_policy = constants.SCRAPE_POLICY_SCRAPE_ONLY
        settings.scrape_assets_policy = constants.SCRAPE_ACTION_NONE
        
        rom_id = random_string(5)
        rom = ROMObj({
            'id': rom_id,
            'filename': Test_gamefaq_scraper.TEST_ASSETS_DIR + '\\castlevania.zip',
            'platform': 'Nintendo NES'
        })
        api_rom_mock.return_value = rom
        
        target = ScrapeStrategy(None, 0, settings, GameFAQs(), FakeProgressDialog())

        # act
        actual = target.process_single_rom(rom_id)
        
        # assert
        self.assertTrue(actual)
        self.assertEqual(u'Castlevania', actual.get_name())
        print(actual.get_data_dic())

    @patch('resources.lib.scraper.net.get_URL', side_effect = mocked_gamesfaq)
    @patch('resources.lib.scraper.net.post_URL', side_effect = mocked_gamesfaq)
    @patch('resources.lib.scraper.net.download_img')
    @patch('resources.lib.scraper.io.FileName.scanFilesInPath', autospec=True)
    @patch('ael.api.client_get_rom')
    def test_scraping_assets_for_game(self, api_rom_mock: MagicMock, scanner_mock, mock_imgs, mock_post, mock_get):
        # arrange
        settings = ScraperSettings()
        settings.scrape_metadata_policy = constants.SCRAPE_ACTION_NONE
        settings.scrape_assets_policy = constants.SCRAPE_POLICY_SCRAPE_ONLY
        settings.asset_IDs_to_scrape = [constants.ASSET_BOXFRONT_ID, constants.ASSET_SNAP_ID ]
        
        rom_id = random_string(5)
        rom = ROMObj({
            'id': rom_id,
            'filename': Test_gamefaq_scraper.TEST_ASSETS_DIR + '\\castlevania.zip',
            'platform': 'Nintendo NES',
            'assets': {key: '' for key in constants.ROM_ASSET_ID_LIST},
            'asset_paths': {
                constants.ASSET_BOXFRONT_ID: '/fronts/',
                constants.ASSET_SNAP_ID: '/snaps/'
            }
        })
        api_rom_mock.return_value = rom
        
        target = ScrapeStrategy(None, 0, settings, GameFAQs(), FakeProgressDialog())

        # act
        actual = target.process_single_rom(rom_id)

        # assert
        self.assertTrue(actual) 
        logger.info(actual.get_data_dic()) 
        
        self.assertTrue(actual.entity_data['assets'][constants.ASSET_BOXFRONT_ID], 'No boxfront defined')
        self.assertTrue(actual.entity_data['assets'][constants.ASSET_SNAP_ID], 'No snap defined')      

if __name__ == '__main__':
    unittest.main()
