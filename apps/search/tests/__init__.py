import os
import shutil
import time

from nose import SkipTest
import test_utils

import amo.test_utils
from manage import settings
from search.utils import start_sphinx, stop_sphinx, reindex


class SphinxTestCase(amo.test_utils.ExtraSetup,
                     test_utils.TransactionTestCase):
    """
    This test case type can setUp and tearDown the sphinx daemon.  Use this
    when testing any feature that requires sphinx.
    """

    sphinx = True
    sphinx_is_running = False

    def setUp(self):
        super(SphinxTestCase, self).setUp()

        if not SphinxTestCase.sphinx_is_running:
            if (not settings.SPHINX_SEARCHD or
                not settings.SPHINX_INDEXER):  # pragma: no cover
                raise SkipTest()

            os.environ['DJANGO_ENVIRONMENT'] = 'test'

            if os.path.exists(settings.SPHINX_CATALOG_PATH):
                shutil.rmtree(settings.SPHINX_CATALOG_PATH)
            if os.path.exists(settings.SPHINX_DATA_PATH):
                shutil.rmtree(settings.SPHINX_DATA_PATH)

            os.makedirs('/tmp/data/sphinx')
            os.makedirs('/tmp/log/searchd')
            reindex()
            start_sphinx()
            time.sleep(1)
            SphinxTestCase.sphinx_is_running = True

    @classmethod
    def tearDownClass(cls):
        if SphinxTestCase.sphinx_is_running:
            stop_sphinx()
            SphinxTestCase.sphinx_is_running = False
