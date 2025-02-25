import os

import click
import redis
from pathlib import Path
from rq import Connection, Worker
from flask import current_app
from flask_migrate import upgrade
from flask.cli import FlaskGroup
from web import create_app, db
from web.models import catfile_to_db
from web.models import Paper, HpEvent

cli = FlaskGroup(create_app=create_app)


@cli.command("show_config")
def show_config():
    from pprint import pprint

    pprint(current_app.config)
    print(db.engine)


@cli.command("create_db")
def create_db():
    db.create_all()


@cli.command("refresh_events")
def refresh_events():
    """Reparse catalogs txt files

    - delete events
    - readd

    Can be used in conjonction with refresh_papers() that has to be run first.

    This method was first writen to fix the hpevent datetime value in db
    A db bug that was fixed in the commit '6b38c89 Fix the missing hours in hpevent bug'
    """
    # delete all events
    for _e in HpEvent.query.all():
        db.session.delete(_e)
        db.session.commit()
    # then parse catalogs again
    for _p in Paper.query.all():
        _p.push_cat(force=True)
        db.session.commit()

    events = HpEvent.query.all()
    papers = Paper.query.all()
    print(f"Updated {len(events)} events from {len(papers)} papers")


@cli.command("refresh_papers")
def refresh_papers():
    """Parse the files on disk and update db

    - parse disk and re-insert pdf and txt files

    Directory tree structure comes from bht module, and looks like

        DATA/web-upload/
            F6114E906C3A9BA154D5BA772F661E1FC66CB974.pdf
            F6114E906C3A9BA154D5BA772F661E1FC66CB974/
            ├── 10105100046361202038319_bibheliotech_V1.txt
            ├── F6114E906C3A9BA154D5BA772F661E1FC66CB974.pdf
            └── F6114E906C3A9BA154D5BA772F661E1FC66CB974.tei.xml

    where F6114E906C3A9BA154D5BA772F661E1FC66CB974 is the paper name
    and 10105100046361202038319_bibheliotech_V1.txt the output catalog file.

    (here, it is an Istex id)

    """
    # First remove all papers
    for _p in Paper.query.all():
        db.session.delete(_p)
        db.session.commit()
    # Then
    # Search for pdf file in base directory and build corresponding Paper
    for _f in Path(current_app.config["WEB_UPLOAD_DIR"]).glob("*.pdf"):
        pdf_filename = os.path.basename(str(_f))
        paper_name = pdf_filename.split(".")[0]
        pdf_filepath = os.path.join(current_app.config["WEB_UPLOAD_DIR"], pdf_filename)
        _p = Paper(title=paper_name, pdf_path=pdf_filepath)
        # If subdirectory  exists and has txt catalog, update paper accordingly
        cat_filename = None
        paper_dir = os.path.join(current_app.config["WEB_UPLOAD_DIR"], paper_name)
        if os.path.isdir(paper_dir):
            try:
                cat_filename = str(
                    list(Path(paper_dir).glob("*bibheliotech_V1.txt"))[0]
                )
            except IndexError:
                cat_filename = None
        if cat_filename is not None:
            _p.set_cat_path(
                os.path.join(current_app.config["WEB_UPLOAD_DIR"], cat_filename)
            )

        db.session.add(_p)
        db.session.commit()

    papers = Paper.query.all()
    print(f"Updated {len(papers)} papers")


@cli.command("upgrade_db")
def upgrade_db():
    """Upgrade running db with new structure

    - use of the alembic method
    """
    upgrade()


@cli.command("mock_papers")
def mock_papers():
    papers_list = [
        ["aa33199-18", "aa33199-18.pdf", None, None],
        [
            "2016GL069787",
            "2016GL069787.pdf",
            "2016GL069787/1010022016gl069787_bibheliotech_V1.txt",
            None,
        ],
        [
            "5.0067370",
            "5.0067370.pdf",
            "5.0067370/10106350067370_bibheliotech_V1.txt",
            None,
        ],
    ]
    for p_l in papers_list:
        paper = Paper(title=p_l[0], pdf_path=p_l[1], cat_path=p_l[2], task_id=p_l[3])
        db.session.add(paper)
    db.session.commit()


@cli.command("list_papers")
def list_papers():
    for p in Paper.query.all():
        print(p)


@cli.command("list_events")
@click.argument("mission_id", required=False)
def list_events(mission_id=None):
    if mission_id:
        events = HpEvent.query.filter_by(mission_id=mission_id)
    else:
        events = HpEvent.query.all()
    for e in events:
        print(e)


@cli.command("feed_catalog")
@click.argument("catalog_file")
def feed_catalog(catalog_file):
    """From a catalog file, feed db with events"""
    catfile_to_db(catalog_file)


@cli.command("run_worker")
def run_worker():
    redis_url = current_app.config["REDIS_URL"]
    redis_connection = redis.from_url(redis_url)
    with Connection(redis_connection):
        worker = Worker(current_app.config["QUEUES"])
        worker.work()


if __name__ == "__main__":
    cli()
