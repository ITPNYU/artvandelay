#!/usr/bin/env python

from htmlentitydefs import name2codepoint
from random import randint
from re import split, sub
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid4

from simulacra.database import Base, db_session
from simulacra.models import Account, Course, Doc, Person, Project, Section, Subject, Tag, Term, Venue

m_engine = create_engine('mysql://root@127.0.0.1/projects_db?charset=utf8&use_unicode=0')
   #, echo=True) #, convert_unicode=True)
m_db_session = scoped_session(sessionmaker(autocommit=False,
                                           autoflush=False,
                                           bind=m_engine))
m_Base = declarative_base()
m_Base.query = m_db_session.query_property()

def m_init_db():
    m_Base.metadata.create_all(bind=m_engine)

def unescape(s):
    if s is None:
        return None
    else:
        try:
            output = sub('&(%s);' % '|'.join(name2codepoint),
                lambda m: unichr(name2codepoint[m.group(1)]), s)
            output = sub('&#039;', "'", output)
        except UnicodeDecodeError:
            print('ERROR: unicode decode error')
            output = '' # FIXME: currently trashing data with invalid characters
        return output

def parse_keywords(k):
    tags = []
    if k is not None:
        k = k.strip()
        k = k.replace('\n', ',')
        if k.find(',') > -1: # has comma
            for t in k.split(','):
                t = t.strip()
                if t is not None and t != '':
                    tags.append(t.strip())
        else: # doesn't have a comma, assume space separated
            # FIXME: handle quoted tags
            for t in k.split():
                t = t.strip()
                if t is not None and t != '':
                    tags.append(t.strip())
            #if k.find('"') > -1 or k.find("'") > -1: # has multi-word tags 
            #    k = k.replace(' "', ',')
            #    k = k.replace(" '", ',')
            #    tag_pass = k.split(',')
    return tags

# CUT THE CHIT CHAT

meta = MetaData()
meta.reflect(bind=m_engine)
project = meta.tables['project']
userProject = meta.tables['userProject']
tags = meta.tables['tags']
terms = meta.tables['terms']
categories = meta.tables['categories']
venueProject = meta.tables['venueProject']
venue = meta.tables['venue']

for m in m_db_session.query(project).all():
    #print('project {}'.format(m.project_name))
    if m.project_id in [888, 889, 890, 892]: # bogus test entries
        continue
    project_name = m.project_name
    if project_name is None:
        project_name = '' # old schema allows a project with no name
    p = Project(title=unescape(project_name),
        description=unescape(m.description),
        elevator_pitch=unescape(m.elevator_pitch),
        url=m.url,
        audience=unescape(m.audience),
        background=unescape(m.background),
        user_scenario=unescape(m.user_scenario),
        technical_system=unescape(m.technical_system),
        conclusion=unescape(m.conclusion),
        research=unescape(m.project_references),
        personal_statement=unescape(m.personal_statement),
        thesis=bool(m.thesis),
        created_at=m.timestamp,
        modified_at=m.timestamp)
    # PEOPLE
    try:
        people = m_db_session.query(userProject).join(project, userProject.c.project_id==project.c.project_id).filter(userProject.c.project_id==m.project_id).all()
        try:
            persons = []
            print('old project ID {}'.format(m.project_id))
            for pp in people:
                a = db_session.query(Account).filter(Account.username == pp.user_id).one()
                persons.append(a.person)
                if pp.designated == 1:
                    point = a.person_id
                    p.person_id = a.person_id
            if p.person_id is None:
                if len(persons) > 0:
                    p.person_id = persons[0].id
                else:
                    continue # bail on project ID: 2332,
        except NoResultFound:
            print('ERROR: no account for this project? project ID: {}'.format(m.project_id))
            unknown_person = Person(official_firstname=pp.user_id,
                official_lastname='Unknown',
                preferred_firstname='Unknown',
                preferred_lastname='Unknown',
                gender='u')
            db_session.add(unknown_person)
            db_session.commit()
            a = Account(username=pp.user_id,
                password=str(uuid4),
                enabled=False,
                dir_authn=False,
                person_id=unknown_person.id)
            db_session.add(a)
            db_session.commit()
            persons.append(unknown_person)
            p.person_id = a.person_id
        p.persons = persons
        db_session.add(p)
        db_session.commit()
    except NoResultFound:
        print('ERROR: no persons for this project? project ID: {}'.format(m.project_id))
    # TAGS
    for tag in parse_keywords(m.keywords):
        try:
            t = db_session.query(Tag).filter(Tag.tag == tag).one()
        except NoResultFound:
            t = Tag(tag=tag)
            db_session.add(t)
            db_session.commit()
        p.tags.append(t)
        db_session.add(p)
    db_session.commit()
    # VENUES
    try:
        m_venues = m_db_session.query(venueProject).join(venue, venueProject.c.venue_id==venue.c.venue_id).join(project, venueProject.c.project_id==project.c.project_id).filter(venueProject.c.project_id==m.project_id).all()
        for m_v in m_venues:
            try:
                m_venue = m_db_session.query(venue).filter(venue.c.venue_id==m_v.venue_id).one()
            except NoResultFound:
                print('missing venue in original database?')
            # create the term
            try:
                m_term = m_db_session.query(terms).filter(terms.c.term_id==m_venue.term_id).one()
                shortname = m_term.term.split()[0]
                year = m_term.term.split()[1]
                try:
                    term = db_session.query(Term).filter(Term.term==m_term.term).one()
                except NoResultFound:
                    term = Term(term=m_term.term,
                        term_shortname=shortname, # FIXME: term_shortname -> shortname
                        term_year=year)
                    db_session.add(term)
                    db_session.commit()
            except NoResultFound:
                print('error: no term in original database?')
            try:
                v = db_session.query(Venue).filter(Venue.venue==m_venue.venue_name).one()
            except NoResultFound:
                venue_shortname = m_venue.venue_shortname
                if venue_shortname is None or venue_shortname == '':
                    v_c = m_venue.venue_name.split()
                    for c in v_c:
                        if c.isdigit():
                            venue_shortname = venue_shortname + str(c)
                        else:
                            venue_shortname = venue_shortname + c[0]
                    if venue_shortname in ['IGS2007', 'SS2009']:
                        venue_shortname = venue_shortname + str(randint(0,100))
                    venue_shortname = venue_shortname[0:10]
                print('venue name: {}, shortname: {}'.format(m_venue.venue_name, venue_shortname))
                v = Venue(venue=m_venue.venue_name,
                    shortname=venue_shortname,
                    description=m_venue.venue_description,
                    term_id=term.id,
                    active=bool(m_venue.active),
                    map_active=bool(m_venue.map_active),
                    #equipment_active=bool(m_venue.equipment_active),
	            searchable=bool(m_venue.searchable),
                    created_at=m_venue.venue_date,
                    modified_at=m_venue.venue_date)
            db_session.add(v)
            db_session.commit()
            p.venues.append(v)
            db_session.add(p)
        db_session.commit()
    except NoResultFound:
        print('no venues? that might be an error')
        pass

