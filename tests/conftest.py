import shutil

import pytest
import os

from bht_config import yml_settings
from web import create_app, db
from web.config import TestConfig

skip_slow_test = pytest.mark.skipif(
    os.environ.get("BHT_SKIPSLOWTESTS") is not None, reason="Slow test skipping"
)


@pytest.fixture(scope="module", autouse=True)
def app():
    app = create_app(TestConfig)

    app_context = app.app_context()
    app_context.push()
    db.create_all()

    yield app

    # clean up / reset resources here


@pytest.fixture(scope="module")
def tei_for_test():
    test_tei_file = os.path.join(yml_settings["BHT_PAPERS_DIR"], "2016GL069787.tei.xml")
    yield test_tei_file
    if os.path.isfile(test_tei_file):
        os.remove(test_tei_file)


@pytest.fixture(scope="module")
def pdf_for_test():
    test_pdf_file_orig = os.path.join(
        yml_settings["BHT_RESSOURCES_DIR"], "2016GL069787-test.pdf"
    )
    test_pdf_file_dest = os.path.join(
        yml_settings["BHT_PAPERS_DIR"], "2016GL069787-test.pdf"
    )
    shutil.copy(test_pdf_file_orig, test_pdf_file_dest)

    yield test_pdf_file_dest

    if os.path.isfile(test_pdf_file_dest):
        os.remove(test_pdf_file_dest)


@pytest.fixture(scope="module")
def test_client(app):
    yield app.test_client()