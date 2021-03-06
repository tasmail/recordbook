#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
    Файл создает уроки в соответствии с расписанием. 
'''

import os
import sys
from datetime import timedelta, date
import logging

PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, 'libs'))
activate_this = PROJECT_DIR + '/.env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

os.environ['DJANGO_SETTINGS_MODULE'] = 'odaybook.settings'

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    filename='/var/log/odaybook_crontabs.log')
LOGGER = logging.getLogger()

from django.db.models import Q

from odaybook.userextended.models import Teacher
from odaybook.attendance.models import UsalTimetable, Vocation
from odaybook.marks.models import Lesson, ResultDate
from odaybook.curatorship.models import Connection

LOGGER.warning('Lessons create started')

for teacher in Teacher.objects.all():
    for conn in Connection.objects.filter(teacher=teacher):
        args = []
        kwargs = {
            'subject': conn.subject,
            'grade': conn.grade,
        }

        if conn.connection != '0':
            args.append(Q(group=conn.connection) | Q(group="0"))

        date_start = date.today()

        lesson_kwargs = kwargs.copy()
        del lesson_kwargs["grade"]
        del lesson_kwargs["subject"]
        if "group" in lesson_kwargs:
            del lesson_kwargs["group"]
        # FIXME: за последний и текущий дни.
        for i in xrange(14, -1, -1):
            d = date_start - timedelta(days=i)
            kwargs['workday'] = str(d.weekday()+1)
            lesson_kwargs['teacher'] = teacher
            lesson_kwargs['date'] = d
            if Vocation.objects.filter(start__lte=d, end__gte=d, grades=conn.grade):
                continue
            for timetable in UsalTimetable.objects.filter(*args, **kwargs):
                lesson_kwargs['attendance'] = timetable
                if not Lesson.objects.filter(**lesson_kwargs):
                    lesson = Lesson(**lesson_kwargs)
                    lesson.save()
            for resultdate in ResultDate.objects.filter(date=d, grades=kwargs['grade'], school=conn.grade.school):
                kwargs4lesson = {
                    'resultdate': resultdate,
                    'grade': kwargs['grade'],
                    'subject': kwargs['subject'],
                    'teacher': teacher,
#                    "attendance__group": conn.connection,
                }
                if not Lesson.objects.filter(**kwargs4lesson):
                    lesson = Lesson(topic = resultdate.name,
                                    date = resultdate.date,
                                    **kwargs4lesson)
                    lesson.save()
