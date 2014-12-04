#!/usr/bin/env python

from re import split
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid4

from simulacra.database import Base, db_session
from simulacra.models import Account, Course, Person, Section, Subject, Term

m_engine = create_engine('mysql://root@127.0.0.1/classes?charset=utf8&use_unicode=0') #, echo=True) #, convert_unicode=True)
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
course = meta.tables['course']
section = meta.tables['section']
section_x_instructor = meta.tables['section_x_instructor']
course_x_attributes = meta.tables['course_x_attributes']
registration_actual = meta.tables['registration_actual']

#SELECT DISTINCT section_id, title, call_number, course.url, course_number, section.url as surl, section_number, description, course.course_id, section.semester, section.year FROM section, course, course_x_attributes WHERE section.status IN ("Yes", "YES", "yes") AND section.course_id = course.course_id AND course_x_attributes.course_id = course.course_id

# Table object c attr is columns
for m in m_db_session.query(course, section, course_x_attributes).with_labels().filter(section.c.course_id == course.c.course_id).filter(course_x_attributes.c.course_id == course.c.course_id).filter(section.c.status.in_(['Yes', 'YES', 'yes'])).all():
    #print('course {}'.format(m.title))
    s = None
    cat_num = None
    if m.course_number is not None:
        fields = split('\.', m.course_number)
        if len(fields) > 0:
            try:
                subj = db_session.query(Subject).filter(Subject.subject == fields[0]).one()
            except NoResultFound:
                # FIXME: correct descriptions of subjects
                # FIXME: ITPG-GTT-GE 2500
                subj = Subject(subject=fields[0], description='NYU Tisch ITP')
        if len(fields) > 1:
            cat_num = fields[1]
    try:
        c = db_session.query(Course).filter(Course.subject_id == subj.id).filter(Course.catalog_num == cat_num).one()
    except NoResultFound:
        c = Course(title=m.title,
            subject=subj,
            catalog_num=cat_num,
            url=m.url,
            description=m.description,
            visibility='public')
        db_session.add(c)
    try:
        t = db_session.query(Term).filter(Term.term == '{} {}'.format(m.semester, m.year)).one()
    except NoResultFound:
        t = Term(term='{} {}'.format(m.semester, m.year),
            term_shortname=m.semester,
            term_year=m.year)
        db_session.add(t)
    try:
        call_num = int(m.call_number)
    except (TypeError, ValueError):
        call_num = None
    try:
        s = db_session.query(Section).filter(Section.section_num == m.section_number).filter(Section.call_num == call_num).filter(Section.course == c).filter(Section.term == t).one()
    except NoResultFound:
        s = Section(section_num = int(m.section_number),
            call_num = call_num,
            course = c,
            term = t) # FIXME: url = m.sectionurl)
        db_session.add(s)
        db_session.commit()
        print(s)
        # SELECT DISTINCT net_id FROM section, registration_actual WHERE registration_actual.section_id = section.section_id AND section.section_id = 
        students = []
        for n in m_db_session.query(registration_actual.c.net_id).join(section, registration_actual.c.section_id==section.c.section_id).filter(section.c.section_id == m.section_id).all():
            print('  {}'.format(n.net_id))
            try:
                p = db_session.query(Account, Person).filter(Account.username == n.net_id).filter(Account.person_id == Person.id).one()
                s.students.append(p.Person)
            except NoResultFound:
                p = Person(official_firstname='Unknown',
                    official_lastname='Unknown',
                    preferred_firstname='Unknown',
                    preferred_lastname='Unknown',
                    gender='u')
                p_a = Account(username=n.net_id,
                    password=str(uuid4()),
                    person=p)
                db_session.add(p)
                db_session.add(p_a)
                db_session.commit()
                s.students.append(p)
        # SELECT DISTINCT net_id FROM section_x_instructor, section WHERE section.section_id = section_x_instructor.section_id AND section.section_id = 
        instructors = []
        for n in m_db_session.query(section_x_instructor.c.net_id).join(section, section_x_instructor.c.section_id == section.c.section_id).filter(section.c.section_id == m.section_id).all():
            try:
                p = db_session.query(Account, Person).filter(Account.username == n.net_id).filter(Account.person_id == Person.id).one()
                s.instructors.append(p.Person)
            except NoResultFound:
                p = Person(official_firstname='Unknown',
                    official_lastname='Unknown',
                    preferred_firstname='Unknown',
                    preferred_lastname='Unknown',
                    gender='u')
                p_a = Account(username=n.net_id,
                    password=str(uuid4()),
                    person=p)
                db_session.add(p)
                db_session.add(p_a)
                db_session.commit()
                s.instructors.append(p)
        db_session.add(s)
        db_session.commit()
