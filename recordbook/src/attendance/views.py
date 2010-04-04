# -*- coding: UTF-8 -*-

from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test

from src import settings
from src.userextended.models import Grade, Subject, School

from models import UsalTimetable, SpecicalTimetable, Holiday
from utils import TimetableDay

@login_required
def index(request):
    render = {}
    if request.user.prefix == 'p':
        render['timetables'] = [TimetableDay(grade = request.user.grade, group = request.user.group, workday = workday) for workday in request.user.school.get_workdays()]
    return render_to_response('attendance/page_pupil.html', render, context_instance = RequestContext(request))

@login_required
@user_passes_test(lambda u: u.prefix=='a')
def timetableSelect(request, school = 0):
    render = {}
    if school:
        school = get_object_or_404(School, id = school)
    else:
        school = request.user.school
    render['school'] = school
    render['grades'] = Grade.objects.filter(school = school)
    return render_to_response('attendance/timetableSelect.html', render, context_instance = RequestContext(request))
    
@login_required
@user_passes_test(lambda u: u.prefix=='a')
def timetableSet(request, id, school = 0):
    from forms import TempForm
    from django import forms
    render = {}
    if school:
        school = get_object_or_404(School, id = school)
    else:
        school = request.user.school
    render['school'] = school
    grade = get_object_or_404(Grade, id = id, school = school)
    aaa = dir(grade)
    form = TempForm()
    for day in settings.WORKDAYS:
        if not school.saturday and day[0] == 6: continue 
        for lesson in settings.LESSON_NUMBERS:
            for i in xrange(1, 3):
                room = ''
                subject = None
                if UsalTimetable.objects.filter(grade = grade, number = lesson[0], group = i, school = school, workday = day[0]).count() != 0:
                    u = UsalTimetable.objects.get(grade = grade, number = lesson[0], group = i, school = school, workday = day[0])
                    room = u.room
                    subject = u.subject.id
                form.fields['l_r_%s_%s_%d' % (day[0], lesson[0], i)] = forms.CharField(initial = room, required = False)
                form.fields['l_s_%s_%s_%d' % (day[0], lesson[0], i)] = forms.ModelChoiceField(initial = subject, queryset = grade.get_subjects(), required = False)
    if request.method == 'POST':
        form.initial = request.POST
        for day in settings.WORKDAYS:
            if not school.saturday and day[0] == 6: continue 
            for lesson in settings.LESSON_NUMBERS:
                for i in xrange(1, 3):
                    subject = request.POST.get('l_s_%s_%s_%d' % (day[0], lesson[0], i), '')
                    if subject == '': continue
                    subject = get_object_or_404(Subject, id = subject, school = school)
                    if UsalTimetable.objects.filter(grade = grade, number = lesson[0], group = i, school = school, workday = day[0]).count() == 0:
                        tt = UsalTimetable(grade = grade, number = lesson[0], group = i, school = school, workday = day[0])
                    else:
                        tt = UsalTimetable.objects.get(grade = grade, number = lesson[0], group = i, school = school, workday = day[0])
                    tt.subject = subject
                    tt.room = request.POST.get('l_r_%s_%s_%d' % (day[0], lesson[0], i), '')
                    tt.save()
    render['form'] = form
    return render_to_response('attendance/timetableSet.html', render, context_instance = RequestContext(request))

@login_required
@user_passes_test(lambda u: u.prefix=='t')
@user_passes_test(lambda u: u.is_administrator())
def ringtimetableList(request):
    render = render_to_response(request)
    return render_to_response('attendance/ringtimetableList.html', render)