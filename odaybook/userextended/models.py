# -*- coding: UTF-8 -*-

from datetime import timedelta, datetime
import pytils
import time
import random

from django.db import models
from django.db.models import Q
from django.db.models.aggregates import Avg
from django.contrib.auth.models import User, UserManager
from django.db.models.signals import post_save, post_syncdb
from django.dispatch import receiver

from odaybook.rest.models import RestModel, RestModelManager
from odaybook.utils import PlaningError
import logging

logger = logging.getLogger(__name__)

class School(RestModel):
    u'Модель для школы'
    name = models.CharField(u"Имя учебного заведения", max_length = 100)
#    prefix = models.CharField(u"Префикс для логина", max_length = 5)
    saturday = models.BooleanField(verbose_name = u'Шестидневка', default = True)
    url = models.URLField(verbose_name = u'Веб-сайт', null = True, blank = True)
    address = models.CharField(verbose_name = u'Адрес школы', max_length = 255)
    phone = models.CharField(verbose_name = u'Телефон школы', max_length = 255)
#    gate_use = models.BooleanField(verbose_name = u'Использовать шлюз', default = False)
#    gate_id = models.CharField(verbose_name = u'ID для SMS-шлюза', max_length = 255, blank = True, null = True)
#    gate_password  = models.CharField(verbose_name = u'Пароль для SMS-шлюза', max_length = 255, blank = True, null = True)
#    gate_url = models.URLField(verbose_name = u'URL SMS-шлюза', blank = True, null = True, default = 'http://gate.school-record-book.ru')
    max_mark = models.IntegerField(verbose_name = u'Максимальный балл', default = 5)
    gapps_use = models.BooleanField(verbose_name = u'Использовать Google Apps', default = False)
    gapps_login = models.CharField(max_length = 255, default = '', verbose_name = u'Логин для Google Apps', blank = True, null = True)
    gapps_password = models.CharField(max_length = 255, default = '', verbose_name = u'Пароль для Google Apps', blank = True, null = True)
    gapps_domain = models.CharField(max_length = 255, default = '', verbose_name = u'Домен для Google Apps', blank = True, null = True)
    private_domain = models.CharField(max_length = 255, verbose_name = u'Система привязана к домену', null = True, blank = True)
    private_salute = models.CharField(max_length = 255, verbose_name = u'Персональное приветствие', null = True, blank = True)

    serialize_fields = ['id', 'name', 'saturday']
    serialize_name = 'school'
    
    def __init__(self, *args, **kwargs):
        '''
            Список доступных настроек
        '''
        
        from odaybook.curatorship.models import Connection
        result = super(School, self).__init__(*args, **kwargs)
        
        grades = Grade.objects.filter(school = self).count() > 0
        teachers = Teacher.objects.filter(school = self).count() > 0
        marks = Connection.objects.filter(teacher__school = self).count() > 0
        show = {}
        show['teachers'] = show['staff'] = show['subjects'] = show['grades'] = show['cams'] = show['options'] = show['ringtimetable'] = True
        show['pupils'] = grades
        show['resultdates'] = grades
        show['connections'] = teachers
        show['deliveryes'] = marks
        show['timetables'] = teachers
        show['marks'] = marks
        self.show = show
        
        return result
    
    def __unicode__(self):
        return self.name
    def get_workdays(self):
        if self.saturday:
            days = 6
        else:
            days = 5
        return xrange(1, days+1)

    def save(self, *args, **kwargs):
        u'''
            Начальная инициализация школы. Добавление предметов
        '''
        pk = self.pk
        super(School, self).save(*args, **kwargs)
        if not pk:
            subjects = [u'Русский язык', u'Физкультура', u'Информатика', 
                        u'Обществознание', u'Литература', u'География', 
                        u'Химия', u'Физика', u'Биология', u'История', 
                        u'ОБЖ', u'Алгебра', u'Геометрия', u'Ин. яз.']
            
            for subject in subjects: Subject(school = self, name = subject).save()

class Option(models.Model):
    key = models.CharField(max_length = 255, verbose_name = u'Ключ')
    key_ru = models.CharField(max_length = 255, verbose_name = u'Настройка')
    value = models.CharField(max_length = 255, verbose_name = u'Значение', null = True, blank = True)
    school = models.ForeignKey(School, verbose_name = u'Школа', null = True, blank = True)

def SystemInitCallback(sender, **kwargs):
    options = [
        {'key': 'vnc_link', 'key_ru': u'Ссылка на приложение ТП', 'value': Null},
    ]
    for option in options:
        Option(**option).save()

post_syncdb.connect(SystemInitCallback, sender = Option)

class Grade(RestModel):
    u'Классы в школах'
    number = models.IntegerField(verbose_name = u'Порядковый номер')
    long_name = models.CharField(u"Длинное имя", max_length = 100)
    small_name = models.CharField(u"Короткое имя", max_length = 10, blank = True)
    school = models.ForeignKey(School, verbose_name = "Школа")

    serialize_fields = ['id', 'long_name', 'school_id']
    serialize_name = 'grade'
    
    def __unicode__(self):
        if self.number:
            return "%d %s" % (self.number, self.long_name)
        else:
            return self.long_name

    def get_subjects(self):
        u'''
            Получение списка всех предметов, которые ведут в этом классе
        '''
        from odaybook.curatorship.models import Connection
        return [c.subject for c in Connection.objects.filter(grade = self)]

    def get_subjects_queryset(self):
        u'''
            Получение queryset всех предметов, которые ведут в этом классе
        '''
        return Subject.objects.filter(id__in = [s.id for s in self.get_subjects()])
        
    def delete(self):
        if Pupil.objects.filter(grade = self).count() == 0:
            for teacher in Teacher.objects.filter(grade = self):
                teacher.grade = None
                teacher.save()
            for teacher in Teacher.objects.filter(grades = self):
                teacher.grades.remove(self)
                teacher.save()
            super(Grade, self).delete()
        else:
            raise PlaningError(u"В классе числятся ученики")
        
    def save(self, *args, **kwargs):
        self.long_name = self.long_name.lower()
        self.small_name = self.small_name.lower()
        super(Grade, self).save(*args, **kwargs)
    class Meta:
        ordering = ['number']
    
    def get_pupils_for_teacher_and_subject(self, teacher, subject):
        from odaybook.curatorship.models import Connection
        conn = Connection.objects.filter(teacher = teacher, grade = self, subject = subject)
        if not conn: raise PlaningError(u'нет учеников')
        conn = conn[0]
        if conn.connection == '0':
            self.pupils = Pupil.objects.filter(grade = self)
        else:
            pupil_connections = PupilConnection.objects.filter(pupil__grade = self, subject = subject, value = conn.connection)
            self.pupils = Pupil.objects.filter(id__in = [c.pupil.id for c in pupil_connections])

class Subject(RestModel):
    u'Учебная дисциплина'
    name = models.CharField(u"Наименование", max_length = 100)
    school = models.ForeignKey(School, verbose_name = "Школа")
    groups = models.CharField(max_length = 1, blank = True, null = True, verbose_name = u'Количество групп')

    serialize_fields = ['id', 'name', 'school_id']
    serialize_name = 'subject'
    
    def __unicode__(self):
        return self.name
    def delete(self):
        for teacher in Teacher.objects.filter(subjects = self):
            teacher.subjects.remove(self)
            teacher.save()
        super(Subject, self).delete()
    class Meta:
        ordering = ['name']

class SearchManager(models.Manager):
    def __init__(self, search_fields = []):
        self.search_fields = search_fields
        models.Manager.__init__(self)
    def search(self, str):
        search_query_list = [Q(**{s + '__icontains': str}) for s in self.search_fields]
        search_query = reduce(lambda x, y: x | y, search_query_list)
        return self.filter(search_query)

class ClerkManager(RestModelManager, UserManager, SearchManager):
    pass

class BaseClerk(models.Model):
    # FIXME: прозрачное удаление, добавление ролей etc
    # FIXME: REST
#    objects = ClerkManager(['last_name', 'first_name', 'middle_name'])
    middle_name = models.CharField(u"Отчество", max_length = 30)
    cart = models.CharField(u'Карта', max_length = 10, null = True, blank = True)
    phone = models.CharField(max_length = 20, verbose_name = u'Номер телефона', null = True, blank = True)
    roles = models.ManyToManyField('BaseUser', null = True, blank = True, related_name = '%(app_label)s_%(class)s_related_roles_related')
    current_role = models.ForeignKey('BaseUser', null = True, blank = True, related_name = '%(app_label)s_%(class)s_related_role_related')
    sync_timestamp = models.IntegerField()

    _sync_timestamp_set = False

    school = None

    def get_roles(self):
        result = []
        for role in self.roles.all():
            if role.type == 'Superuser': Object = Superuser
            elif role.type == 'Superviser': Object = Superviser
            elif role.type == 'Teacher': Object = Teacher
            elif role.type == 'Pupil': Object = Pupil
            elif role.type == 'Parent': Object = Parent
            result.append(Object.objects.get(id = role.id))
        return result

    def save(self, *args, **kwargs):
        if not self._sync_timestamp_set:
            self.sync_timestamp = random.randint(1, 10000000)
            self._sync_timestamp_set = True
        if hasattr(self, 'type'): t = self.type
        else: t = 'Clerk'
        super(BaseClerk, self).save(*args, **kwargs)
        logger.info(u'Сохранён Baseclerk#%d с synctimestamp=%d, synctimeset=%d, type=%s' % (self.id, self.sync_timestamp, self._sync_timestamp_set, t))

    def __unicode__(self):
        return ' '.join((self.last_name, self.first_name, self.middle_name))

    def fio(self):
        if self.last_name or self.first_name or self.middle_name:
            return self.last_name + ' ' + self.first_name + ' ' + self.middle_name
        else:
            return u'Имя не указано'

    def fi(self):
        u'''Вывод строки "Фамилия Имя"'''
        return self.last_name + ' ' + self.first_name

    def if_(self):
        u'''Вывод строки "Имя Фамилия"'''
        return self.first_name + ' ' + self.last_name

    def get_fio(self):
        return "%s %s %s" % (self.last_name, self.first_name, self.middle_name)

    def gen_username(self, school = False):
        # Генерация буквенного имени пользователя
        def _clean_name(name):
            u'''Чистка строки от инородных символов и транслитерация'''
            name = pytils.translit.translify(self.name.lower())
            name = name.replace("'","")
            name = name.replace("`","").strip()
            name = name.replace(' ', '_')

        username = self.prefix + "."
        # Удаление нехороших символов и транслитерация
        last_name, first_name = map(_clean_name, self.last_login, self.first_name)

        # FXIME:
        #Проверки на допустимость
        if len(last_name)+len(first_name)+prefix>28:
            if len(last_name)>25-prefix:
                last_name = last_name[:25-prefix]
                first_name = first_name[:3]
            else:
                if len(last_name)>len(first_name):
                    last_name = last_name[:28-len(first_name)-prefix]
                else:
                    first_name = first_name[:28-len(first_name)-prefix]
        return username + last_name + '.' + first_name

    def get_role_display(self, role = None):
        roles = {
            'Pupil': u'Ученик',
            'Teacher': u'Учитель',
            'Superuser': u'Технический администратор системы',
            'Parent': u'Родитель',
            'Superviser': 'Специалист УОН',
            'Staff': u'Персонал',
            'EduAdmin': u'Учебный администратор',
            'Curator': u'Классный руководитель',
        }
        if role: return roles[role]
        else: return roles[self.current_role.__class__.__name__]

    def get_base_roles_list(self):
        u'''
            Возвращает список базовых ролей.
            Каждая роль представляется списком с полями:
              - название
              - код (латиница)
              - id BaseUser если таковой имеется
              - роль является текущей (bool)
              - экземпляр класса роли
        '''
        result = []
        for role in self.roles.all():
            result.append([self.get_role_display(role.type), role.type, role.id, self.current_role == role, role])
        return result

    def get_roles_list(self):
        '''
            Возвращает список ролей.
            Каждая роль представляется списком с полями:
              - название
              - код (латиница)
              - id BaseUser если таковой имеется
              - роль является текущей (bool)
              - экземпляр класса роли
        '''
        result = []
        for role in self.get_roles():
            result.append([self.get_role_display(role.type), role.type, role.id, self.current_role == role, role])
            if role.type == 'Teacher':
                if role.edu_admin:
                    result.append([self.get_role_display('EduAdmin'), 'EduAdmin', role.id, self.current_role == role, role])
                if role.grade:
                    result.append([self.get_role_display('Curator'), 'Curator', role.id, self.current_role == role, role])
        return result

    def get_base_roles_list_simple(self):
        '''
            Список ролей, возожных для данного пользователя
        '''
        result = []
        for role in self.roles.all():
            result.append(role.type)
        return result

    def get_roles_list_simple(self):
        '''
            Список ролей, возожных для данного пользователя
        '''
        result = []
        for role in self.get_roles():
            result.append(role.type)
            if role.type == 'Teacher':
                if role.edu_admin: result.append('EduAdmin')
                if role.grade: result.append('Curator')
        return result

    def get_role_obj(self, role, school = None):
        if role not in self.get_roles_list_simple(): raise self.DoesNotExist
        result = []
        for r in self.get_roles():
            if role in r.types:
                if not school or r.school == school:
                    result.append(r)
        if len(result) == 0: raise self.DoesNotExist
        else: return result

    def has_role(self, role, school = None):
        if role not in self.get_roles_list_simple():
            return False
        else:
            try:
                return bool(len(self.get_role_obj(role, school)))
            except self.DoesNotExist:
                return False
        return False

    def get_current_role_cyrillic(self):
        return self.get_role_display(self.current_role.type)

    def set_current_role(self, id):
        # FIXME: exceptions
        try:
            baseuser = BaseUser.objects.get(id = id)
        except BaseUser.DoesNotExist:
            raise BaseUser.DoesNotExist
        if baseuser not in self.roles.all():
            raise
        self.current_role = baseuser
        self.sync_timestamp = random.randint(1, 10000000)
        self.save()
        logger.info(u'Установлен current_role %s#%d для baseuser#%d' % (baseuser.type, baseuser.id, self.id))

    class Meta:
        abstract = True

class Clerk(User, RestModel, BaseClerk):

    objects = ClerkManager(['last_name', 'first_name', 'middle_name', 'username'])

    def save(self, init = False, safe = False, *args, **kwargs):

        if not self.pk or init:
            if not self.username:
                from random import randint
                username = str(randint(10**6, 9999999))
                while User.objects.filter(username = username):
                    username = str(randint(10**6, 9999999))
                self.username = username
            password = None
            if not self.password:
                password = User.objects.make_random_password(10, '1234567890')
                self.set_password(password)
            if self.email:
                from django.core.mail import EmailMessage
                from django.template.loader import render_to_string
                from django.conf import settings
                email  = EmailMessage(
                        u'Вы зарегистрировались в системе электронных дневников',
                        render_to_string('~userextended/registration_mail.html', {'user': self, 'password': password}),
                        settings.DEFAULT_FROM_EMAIL,
                        [self.email])
                email.content_subtype = 'html'
                email.send()
            super(Clerk, self).save(*args, **kwargs)
        super(Clerk, self).save(*args, **kwargs)

#        self._sync_timestamp_set = False

    def add_role(self, role):
        self.roles.add(role)
        self.save()
    
    def create_role(self, Role):
        role = Role()
        role.set_clerk(self)
        role.save()
        return role

    def get_current_role(self):
        return eval(self.current_role.type).objects.get(id = self.current_role.id)

    def reset_password(self):
        if self.email:
            from django.core.mail import EmailMessage
            from django.template.loader import render_to_string
            from django.conf import settings
            password = User.objects.make_random_password(10, '123456789')
            self.set_password(password)
            email  = EmailMessage(
                    u'Вы сбросили пароль в системе электронных дневников',
                    render_to_string('~userextended/password_reset_force_mail.html', {'user': self, 'password': password}),
                    settings.DEFAULT_FROM_EMAIL,
                    [self.email])
            email.content_subtype = 'html'
            email.send()
        self.save()
        return password

    class Meta:
        ordering = ['last_name', 'first_name', 'middle_name']

class BaseUser(BaseClerk):
    clerk = models.ForeignKey(Clerk, null = True, blank = True)
    type = models.CharField(max_length = 15)
    username = models.CharField(max_length=30, null = True)
    first_name = models.CharField(max_length=30, null = True, default = '')
    last_name = models.CharField(max_length=30, null = True, default = '')
    email = models.EmailField(null = True, blank = True)

    # FIXME:
    is_staff = models.BooleanField('staff status', default=False, help_text= ("Designates whether the user can log into this admin site."))
    is_active = models.BooleanField('active', default=True, help_text=("Designates whether this user should be treated as active. Unselect this instead of deleting accounts."))
    is_superuser = models.BooleanField('superuser status', default=False, help_text=("Designates that this user has all permissions without explicitly assigning them."))
    last_login = models.DateTimeField(('last login'), default=datetime.now)
    date_joined = models.DateTimeField(('date joined'), default=datetime.now)
    password = models.CharField('password', max_length=128)

    def is_authenticated(self):
        return True

    _append_to_clerk = False

    def __init__(self, *args, **kwargs):
        super(BaseUser, self).__init__(*args, **kwargs)
        self.types = [self.type, ]
        if self.__class__.__name__ != 'BaseUser':
#            self.types.append(self.type)
#            if self.type == 'Teacher': Object = Teacher
#            elif self.type == 'Parent': Object = Parent
#            elif self.type == 'Pupil': Object = Pupil
#            elif self.type == 'Superviser': Object = Superviser
#            obj = Object.objects.get(id = self.id)
            if self.type == 'Teacher':
                if self.edu_admin: self.types.append('EduAdmin')
                if self.grade: self.types.append('Curator')

    def save(self, *args, **kwargs):
        pk = self.pk
        if self.__class__.__name__ != 'BaseUser':
            self.type = self.__class__.__name__
        if not self.clerk:
            clerk = Clerk(last_name = self.last_name,
                          first_name = self.first_name,
                          middle_name = self.middle_name,
                          email = self.email,
            )
            clerk.save()
            self.username = clerk.username
            self.clerk = clerk
            self._append_to_clerk = True

        if not pk:
            self.password = self.clerk.password
            super(BaseUser, self).save(*args, **kwargs)

        if self._append_to_clerk:
            self.clerk.roles.add(self)

        super(BaseUser, self).save(*args, **kwargs)

#        if not self._sync_timestamp_set:
#            self.sync_timestamp = int(time.time())
#            self._sync_timestamp_set = True

        if self.sync_timestamp != self.clerk.sync_timestamp and not self._sync_timestamp_set:
            self.clerk._sync_timestamp_set = True
            self.clerk.sync_timestamp = self.sync_timestamp
            self.send_to_clerk()
            self.send_roles_to_clerk()
            self.clerk.save()

    def set_clerk(self, clerk):
        '''
            Устанавливает базового клерка. Копирует из него основные поля кроме ролей!
        '''
        self.clerk = clerk
        self._append_to_clerk = True
        for prop in ['last_name', 'first_name', 'middle_name', 'username', 'email', 'current_role', 'password']:
            setattr(self, prop, getattr(clerk, prop))

    def set_roles(self, clerk):
        '''
            Копирование прав доступа из базового клерка.
        '''
        for role in clerk.roles.all():
            self.roles.add(role)

    def send_to_clerk(self):
        '''
            Устанавливает базового клерка. Копирует из него основные поля кроме ролей!
        '''
        for prop in ['last_name', 'first_name', 'middle_name', 'username', 'email', 'current_role', 'password']:
            setattr(self.clerk, prop, getattr(self, prop))
        logger.info(u'От %s#%d скопированы данные в clerk#%d' % (self.type, self.id, self.clerk.id))

    def send_roles_to_clerk(self):
        '''
            Копирование прав доступа из базового клерка.
        '''
        for role in self.roles.all():
            self.clerk.roles.add(role)

@receiver(post_save, sender = Clerk)
def BaseUser_update(sender, instance, **kwargs):
    logger.info(u'Сигнал для копирования из clerk начал работать')
    for role in instance.get_roles():
        if role.sync_timestamp != instance.sync_timestamp:
            role.set_clerk(instance)
            role.set_roles(instance)
            role.sync_timestamp = instance.sync_timestamp
            role.save()
    logger.info(u'Сигнал для копирования из clerk отработал')

@receiver(post_save, sender = User)
def Clerk_update(sender, instance, **kwargs):
    logger.info(u'Сигнал для копирования в clerk начал работать')
    try:
        clerk = Clerk.objects.get(id = instance.id)
    except Clerk.DoesNotExist:
        return
    clerk.password = instance.password
    clerk.save()
    logger.info(u'Сигнал для копирования в clerk отработал')

class Scholar(models.Model):
    school = models.ForeignKey(School, null = True, blank = True)
    class Meta:
        abstract = True

class Teacher(Scholar, BaseUser):

    objects = SearchManager(['last_name', 'first_name', 'middle_name'])

    # Завуч/директор
    edu_admin = models.BooleanField(u"Учебный администратор", default = False)
    # Технический администратор
    tech_admin = models.BooleanField(u"Технический администратор", default = False)
    # Какие предметы ведёт
    subjects = models.ManyToManyField(Subject, verbose_name = u"Предметы", related_name = 'subjects', blank = True, null = True)
    # В каких классах ведёт
    grades = models.ManyToManyField(Grade, blank = True, verbose_name = u"Классы", related_name = "grades", null = True)
    # Есть ли классное руководство
    grade = models.ForeignKey(Grade, verbose_name="Класс", blank = True, related_name = 'grade', null = True)
    # Выбранный предмет в инструменте выставления отметок
    current_subject = models.ForeignKey(Subject, blank = True, related_name = 'current_subject', null = True)
    # Выбранный класс в инструменте выставления отметок
    current_grade = models.ForeignKey(Grade, blank = True, related_name = 'current_grade', null = True)

    serialize_fields = ['id', 'last_name', 'first_name', 'middle_name', 'grade_id', 'school_id', 'grades', 'subjects']
    serialize_name = 'teacher'
    
    def get_grades(self):
        from odaybook.curatorship.models import Connection
        return list(set([conn.grade for conn in Connection.objects.filter(teacher = self)]))

    def get_grades_for_marks(self):
        from odaybook.attendance.models import UsalTimetable
        return list(set([grade for grade in self.get_grades() if UsalTimetable.objects.filter(grade = grade, subject = self.current_subject)]))

    class Meta:
        unique_together = ('grade', )

class Parent(BaseUser):
    pupils = models.ManyToManyField('Pupil', related_name = 'userextended_pupils_related')
    current_pupil = models.ForeignKey('Pupil', related_name = 'userextended_pupil_related', null = True)

class Pupil(BaseUser, Scholar):

    objects = SearchManager(['last_name', 'first_name', 'middle_name', 'username', 'grade__number', 'grade__long_name', 'grade__small_name'])

    grade = models.ForeignKey(Grade, verbose_name = u"Класс", null=True)
    sex = models.CharField(max_length = 1, choices = (('1', u'Юноша'), ('2', u'Девушка')), verbose_name = u'Пол')
    special = models.BooleanField(verbose_name = u'Специальная группа')
    health_group = models.CharField(null = True, blank = False, default = '1', choices=(('1', '1'),
                                                                                        ('2', '2'),
                                                                                        ('3', '3'),
                                                                                        ('4', '4'),
                                                                                        ),
                                    max_length = 1, verbose_name = u'Группа здоровья')
    health_note = models.CharField(null = True, blank = True, default='', max_length = 255, verbose_name = u'Примечание')
    order = models.CharField(null = True, max_length = 100, verbose_name = u'Социальная группа', choices = (
        ('0', u'полноценная семья'),
        ('1', u'мать-одиночка'),
        ('2', u'малообеспеченные'),
        ('3', u'неблагополучная семья'),
        ('4', u'беженцы'),
        ('5', u'ребенок-инвалид'),
    ), default = '0')
    # TODO: примечение (см. ТЗ)
    parent_1 = models.CharField(max_length = 255, verbose_name = u'Родитель 1', blank = True, null = True)
    parent_2 = models.CharField(max_length = 255, verbose_name = u'Родитель 2', blank = True, null = True)
    parent_phone_1 = models.CharField(max_length = 255, verbose_name = u'Телефон родителя 1', blank = True, null = True)
    parent_phone_2 = models.CharField(max_length = 255, verbose_name = u'Телефон родителя 2', blank = True, null = True)
    insurance_policy = models.TextField(verbose_name = u'Страховой полис', null = True, blank = True)
    
    serialize_fields = ['id', 'cart', 'account', 'last_name', 'first_name', 'middle_name', 'grade_id', 'group', 'school_id']
    serialize_name = 'pupil'

    groups = {}
    
    def get_curator(self):
        teacher = Teacher.objects.filter(grade = self.grade)
        if teacher:
            return teacher[0]
        else:
            return Teacher(grade = self.grade, last_name = '', first_name = '', middle_name = '')

    def get_marks_avg(self, delta = timedelta(weeks = 4)):
        from odaybook.marks.models import Mark
        temp = Mark.objects.filter(pupil = self, absent = False, lesson__date__gte = datetime.now()-delta).aggregate(Avg('mark'))['mark__avg']
        if not temp:
            temp = 0
        return "%.2f" % temp

    def get_marks_avg_type(self, delta = timedelta(weeks = 4)):
        mark = self.get_marks_avg(delta)
        if mark<3:
            return "bad"
        elif mark>=4:
            return "good"
        else:
            return "normal"

    def get_groups(self):
        self.groups = {}
        for subject in self.get_subjects():
            try:
                connection = PupilConnection.objects.get(pupil = self, subject = subject)
            except PupilConnection.DoesNotExist:
                connection = PupilConnection(value = '0', pupil = self, subject = subject)
            connection.group = connection.value
            self.groups[subject.id] = connection

#    def get_teacher_connections(self):
#        # FIXME
#        from odaybook.curatorship.models import Connection
#        return [
#                connection for connection in Connection.objects.filter(grade = self.grade)
#                    if connection.connection == '0' or connection.connection == self.group
#                ]

    def get_connections(self):
        from odaybook.curatorship.models import Connection
        result = []
        for connection in Connection.objects.filter(grade = self.grade):
            pupilconnections = PupilConnection.objects.filter(pupil = self, subject = connection.subject)
            if not pupilconnections or pupilconnections.filter(value = connection.connection) or (connection.connection == '0' and pupilconnections):
                result.append(connection)
        return result

    def get_teacher(self, subject):
        from odaybook.curatorship.models import Connection
        if not len(self.groups): self.get_groups()
        try:
            return Connection.objects.get(
                    subject = subject,
                    grade = self.grade,
                    connection = self.groups[subject.id].group
                   ).teacher
        except KeyError:
            return None
        except Connection.DoesNotExist:
            return None

    def get_teachers(self):
        # FIXME
        return set([connection.teacher for connection in self.get_connections()])

    def get_subjects(self):
        # FIXME
        return set([connection.subject for connection in self.get_connections()])

    class Meta:
        ordering = ['last_name', 'first_name', 'middle_name']

class Staff(BaseUser, Scholar):
    '''
    Модель персонала
    '''
#    objects = SearchManager(['last_name', 'first_name', 'middle_name'])
    
    # Завуч/директор 
    edu_admin = models.BooleanField(u"Администратор", default = False)
    # Технический администратор
    tech_admin = models.BooleanField(u"Технический администратор", default = False)

class Superviser(BaseUser):
    pass

class Superuser(BaseUser):
    pass

# FIXME: WTF??
class Achievement(models.Model):
    title = models.CharField(verbose_name = u'Достижение', max_length = 255)
    description = models.TextField(verbose_name = u'Описание достижения')
    date = models.DateField(verbose_name = u'Дата')
    pupil = models.ForeignKey(Pupil)

# FIXME: WTF?
class Permission(models.Model):
    user_id = models.IntegerField()
    user_type = models.CharField(max_length = 1, choices = (('p', 'p'), ('t', 't'), ('s', 's')))
    permission = models.CharField(max_length = 255)

    def user(self):
        if self.user_type == 'p': Model = Pupil
        elif self.user_type == 't': Model = Teacher
        elif self.user_type == 's': Model = Staff
        return Model.objects.get(id = self.user_id)

class PupilConnection(models.Model):
    pupil = models.ForeignKey(Pupil)
    subject = models.ForeignKey(Subject)
    value = models.CharField(null = True, blank = True, max_length = 1)
    class Meta:
        unique_together = (('pupil', 'subject'), )

class Notify(models.Model):
    timestamp = models.DateTimeField(auto_now_add = True)
    user = models.ForeignKey(Teacher, null = True)
    type = models.CharField(max_length = 1, choices = ( ('1', u'Дневник не заполняется'),
                                                        ('2', u'Система не используется'),
                                                        ('3', u'Привязки не одобряются'),
                                                        ),
                            null = True)
    for_eduadmin = models.BooleanField(default = True)
    for_superviser = models.BooleanField(default = False)
    notify_start = models.DateTimeField(null = True)
    def save(self, *args, **kwargs):
        if self.user.email and self.type!='2':
            from django.core.mail import EmailMessage
            from django.template.loader import render_to_string
            from django.conf import settings
            email  = EmailMessage(
                    u'Уведомление в системе электронных дневников',
                    render_to_string('~userextended/notify_%s_mail.html' % self.type, {'user': self.user}),
                    settings.DEFAULT_FROM_EMAIL,
                    [self.email])
            email.content_subtype = 'html'
            email.send()
    def get_timedelta(self):
        if self.notify_start:
            return datetime.now() - self.notify_start
        else:
            return None