#!/usr/bin/env python

from re import split
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid4

from simulacra.database import Base, db_session
from simulacra.models import Account, Affiliation, Person

m_engine = create_engine('mysql://root@127.0.0.1/itpdir?charset=utf8&use_unicode=0') #, convert_unicode=True)
m_db_session = scoped_session(sessionmaker(autocommit=False,
                                           autoflush=False,
                                           bind=m_engine))
m_Base = declarative_base()
m_Base.query = m_db_session.query_property()

def m_init_db():
    m_Base.metadata.create_all(bind=m_engine)

# CUT THE CHIT CHAT

meta = MetaData()
meta.reflect(bind=m_engine)
nyu_official = meta.tables['nyu_official']
for m in m_db_session.query(nyu_official).all():
    affiliations = []
    statuses = []
    if m.current_status is not None and m.current_status != '':
        statuses = split(', ', m.current_status)
    if m.classyear is not None and m.classyear != '':
        statuses.append('{} Class'.format(m.classyear))
    # FIXME: implement '2016 Graduate' affiliation somehow
    for s in statuses:
        try:
            a = db_session.query(Affiliation).filter(Affiliation.affiliation == s).one()
        except NoResultFound:
            a = Affiliation(affiliation=s)
            db_session.add(a)
        affiliations.append(a)
    if m.netid is not None:
        try:
            account = db_session.query(Account).filter(Account.username == m.netid).one()
        except NoResultFound:
            account = Account(username=m.netid,
                password=str(uuid4()),
                enabled=True,
                dir_authn=True)
            
    person = Person(official_firstname = m.official_firstname,
        official_middlename = m.official_middlename,
        official_lastname = m.official_lastname,
        preferred_firstname = m.preferred_firstname,
        preferred_middlename = m.preferred_middlename,
        preferred_lastname = m.preferred_lastname,
        gender = m.gender,
        account = [account],
        university_n = m.university_id,
        affiliations = affiliations)
    db_session.add(person)
    db_session.commit()

