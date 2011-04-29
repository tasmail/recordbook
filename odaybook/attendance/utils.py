# -*- coding: utf-8 -*-

from datetime import date, timedelta
import pytils

from odaybook.attendance.models import UsalTimetable, UsalRingTimetable

class TimetableDay(object):
    def __init__(self, workday):
        workday = int(workday)
        self.day_n = workday
        self.day_ru = self.numDay2ruday(workday)
#        self.grade = grade
#        self.group = group
#        self.lessons = [lesson for lesson in UsalTimetable.objects.filter(grade = grade, group = group, workday = workday)]
        today = date.today().isoweekday()
        if today == workday:
            self.date = u'Сегодня'
            self.today = True
        elif today == workday - 1:
            self.date = u'Завтра'
        elif today == workday + 1:
            self.date = u'Вчера'
        else:
            self.date = pytils.dt.ru_strftime(u"%d %B", inflected=True, date=date.today() + timedelta(days = (workday - today)))
        self.timestamp = (date.today() + timedelta(days = (workday - today))).isoformat()
        self.rings = {}
#        for ring in UsalRingTimetable.objects.filter(school = grade.school, workday = workday):
#            self.rings[ring.number] = ring
#        if UsalRingTimetable.objects.filter(school = grade.school, workday = workday, number = len(self.lessons)):
#            self.rings['end_of_day'] = UsalRingTimetable.objects.get(school = grade.school, workday = workday, number = len(self.lessons))


    def numDay2ruday(self, workday):
        days = {1: u'Понедельник',
                2: u'Вторник',
                3: u'Среда',
                4: u'Четверг',
                5: u'Пятница',
                6: u'Суббота',
                7: u'Воскресенье',
                }
        return days[int(workday)]

class TimetableDayPupil(TimetableDay):
    def __init__(self, workday, pupil):
        from odaybook.userextended.models import PupilConnection
        super(TimetableDayPupil, self).__init__(workday)
        self.pupil = pupil
        self.lessons = {}
        for lesson in UsalTimetable.objects.filter(grade = pupil.grade, workday = workday):
            try:
                connection = pupil.pupilconnection_set.all().filter(subject = lesson.subject)[0]
            except IndexError:
                connection = PupilConnection(value = '0')
            if connection.value == '0' or connection.value == lesson.group:
                self.lessons[int(lesson.number)] = lesson

