# -*- coding: utf-8 -*-
'''
    Фильтры, необходимые для красивой отрисовки формы ввода оценок
'''

import logging

from django import template
from django.utils.datastructures import SortedDict

register = template.Library()
LOGGER = logging.getLogger(__name__)

def _get_lesson(lesson_col, pupil):
    LOGGER.info('_get_lesson start')
    pupil.get_groups()
    for lesson in lesson_col:
        if lesson.attendance:
            if lesson.attendance.group == None or lesson.attendance.group == '0' or \
               (lesson.attendance.subject_id in pupil.groups and lesson.attendance.group == pupil.groups[lesson.attendance.subject.id].value):
                LOGGER.info('_get_lesson end')
                return lesson.id
        else:
            return lesson.id
    LOGGER.info('_get_lesson end')
    return None

register.filter('get_lesson', _get_lesson)

@register.simple_tag
def next_date(current, array, pupil):
    '''
        Следующая дата из списка
    '''

    LOGGER.info('next_date started')

    if isinstance(pupil, list):
        pupil = pupil[0]

    new_index = array.index(current) + 1
    if new_index >= len(array):
        LOGGER.info('next_date end1')
        return None

    while not _get_lesson(array[new_index], pupil):
        new_index += 1
        if new_index >= len(array) or len(array[new_index]) == 0:
            LOGGER.info('next_date end2')
            return None

    LOGGER.info('next_date end3')
    return _get_lesson(array[new_index], pupil)

@register.simple_tag
def prev_date(current, array, pupil):
    '''
        Предыдущая дата из списка
    '''
    LOGGER.info('prev_date start')

    new_index = array.index(current) - 1
    if new_index < 0:
        LOGGER.info('prev_date end1')
        return None

    while not _get_lesson(array[new_index], pupil):
        new_index -= 1
        if new_index < 0 or len(array[new_index]) == 0:
            LOGGER.info('prev_date end4')
            return None

    LOGGER.info('prev_date end3')

    return _get_lesson(array[new_index], pupil)

@register.simple_tag
def up_pupil_and_lesson(current, array, lessons):
    '''
        Предыдущий ученик из списка.
    '''
    LOGGER.info('up_pupil_and_lesson start')

    array = list(array)
    new_index = array.index(current) - 1
    if new_index < 0:
        LOGGER.info('up_pupil_and_lesson end1')
        return None
    else:
        if _get_lesson(lessons, array[new_index]):
            LOGGER.info('up_pupil_and_lesson end2')
            return str(array[new_index].id) + '-' + str(_get_lesson(lessons, array[new_index]))
        else:
            LOGGER.info('up_pupil_and_lesson end3')
            return None

@register.filter
def first_pupil(current, array):
    '''
        Первый ученик из списка.
    '''
    return list(array)[0].id

@register.simple_tag
def down_pupil_and_lesson(current, array, lessons):
    '''
        Следующий ученик из списка.
    '''
    LOGGER.info('down_pupil_and_lesson start')
    array = list(array)
    new_index = array.index(current) + 1
    if new_index >= len(array):
        LOGGER.info('down_pupil_and_lesson end1')
        return None
    else:
        if _get_lesson(lessons, array[new_index]):
            LOGGER.info('down_pupil_and_lesson end2')
            return str(array[new_index].id) + '-' + str(_get_lesson(lessons, array[new_index]))
        else:
            LOGGER.info('down_pupil_and_lesson end3')
            return None

@register.filter
def get_mark(pupil, lesson):
    '''
        Вывод оценки данного ученика за данное занятие.
    '''
    from odaybook.marks.models import Mark
    from django.utils.safestring import mark_safe
    LOGGER.info('get_mark start')
    lesson_id = _get_lesson(lesson, pupil)
    if Mark.objects.filter(lesson__id = lesson_id, pupil = pupil):
        mark = Mark.objects.filter(lesson__id = lesson_id, pupil = pupil)[0]
        LOGGER.info('get_mark end1')
        return mark_safe('<div class="mark-%s">%s</div>' % (mark.get_type(), str(mark)))
    else:
        LOGGER.info('get_mark end2')
        return ''



@register.filter(name='sort')
def listsort(value):
    if isinstance(value,dict):
        new_dict = SortedDict()
        key_list = value.keys()
        key_list.sort()
        for key in key_list:
            new_dict[key] = value[key]
        return new_dict
    elif isinstance(value, list):
        new_list = list(value)
        new_list.sort()
        return new_list
    else:
        return value
listsort.is_safe = True

