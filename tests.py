from datetime import datetime
from pathlib import Path
from pytest import fixture
import sqlite3
import sqlalchemy

import anketa

# BTW: http://flask.pocoo.org/docs/0.12/testing/


@fixture
def test_client():
    return anketa.app.test_client()


def test_render_index(test_client):
    rv = test_client.get('/')
    assert b'Anketa' in rv.data


@fixture
def temp_dir(tmpdir):
    # I like standard pathlib.Path more than py.path :)
    return Path(str(tmpdir))


def test_smoke_sqlite3(temp_dir):
    # just an example of sqlite3 usage from Python docs:
    # https://docs.python.org/3.6/library/sqlite3.html
    conn = sqlite3.connect(str(temp_dir / 'example.db'))
    c = conn.cursor()
    c.execute('''CREATE TABLE stocks
                 (date text, trans text, symbol text, qty real, price real)''')
    c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
    conn.commit()
    conn.close()


def test_smoke_sqlalchemy(temp_dir):
    db_path = temp_dir / 'smoke.db'
    engine = sqlalchemy.create_engine('sqlite:///' + str(db_path), echo=True)
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()
    from sqlalchemy import Column, Integer, String
    class User(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    joe = User(name='Joe Smith')
    session.add(joe)
    session.commit()
    joe = session.query(User).first()
    assert joe.name == 'Joe Smith'
    # overeni pres sqlite3
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('SELECT name FROM users')
    row, = c.fetchall()
    assert row[0] == 'Joe Smith'
    conn.close()


@fixture
def sa_session(temp_dir):
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    db_path = temp_dir / 'test.db'
    engine = sqlalchemy.create_engine('sqlite:///' + str(db_path), echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


def test_workflow_prototype(temp_dir, sa_session):
    anketa.prepare_schema(sa_session)
    sug1_id = anketa.insert_suggestion(
        sa_session, 'Tvorba webu', 'cookie1', date=datetime(2017, 3, 15, 12, 0))
    sug2_id = anketa.insert_suggestion(
        sa_session, 'Statistika', 'cookie1', date=datetime(2017, 3, 15, 13, 0))
    # add some upvotes
    anketa.insert_vote(sa_session, sug1_id, 'cookie1', upvote=True, date=datetime(2017, 3, 15, 13, 0))
    anketa.insert_vote(sa_session, sug1_id, 'cookie2', upvote=True, date=datetime(2017, 3, 15, 13, 0))
    anketa.insert_vote(sa_session, sug1_id, 'cookie3', upvote=False, date=datetime(2017, 3, 15, 13, 0))
    # the most important query :)
    rows = anketa.list_suggestions(sa_session)
    assert rows == [
        {'id': sug1_id, 'title': 'Tvorba webu', 'vote_count': 1},
        {'id': sug2_id, 'title': 'Statistika',  'vote_count': 0},
    ]


def test_prepare_schema_twice(temp_dir, sa_session):
    anketa.prepare_schema(sa_session)
    anketa.prepare_schema(sa_session)
