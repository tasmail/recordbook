from smart_selects.widgets import ChainedSelect, SimpleChainedSelect
from django.forms.models import ModelChoiceField
from django.forms import ChoiceField


class ChainedModelChoiceField(ModelChoiceField):
    def __init__(self, app_name, model_name, chain_field, model_field, initial=None, *args, **kwargs):
        defaults = {
            'widget': ChainedSelect(app_name, model_name, chain_field, model_field),
        }
        defaults.update(kwargs)
        super(ChainedModelChoiceField, self).__init__(initial=initial, *args, **defaults)
    
    #widget = ChainedSelect
    def _get_choices(self):
        self.widget.queryset = self.queryset
        choices = super(ChainedModelChoiceField, self)._get_choices()
        return choices
        if hasattr(self, '_choices'):
            return self._choices
        final = [("", "---------"), ]
        return final
    choices = property(_get_choices, ChoiceField._set_choices)

class SimpleChainedModelChoiceField(ChainedModelChoiceField):
    def __init__(self, app_name, model_name, chain_field, model_field, initial=None, *args, **kwargs):
        defaults = {
            'widget': SimpleChainedSelect(app_name, model_name, chain_field, model_field),
        }
        defaults.update(kwargs)
        super(ChainedModelChoiceField, self).__init__(initial=initial, *args, **defaults)
    
    
class GroupedModelSelect(ModelChoiceField):
    def __init__(self, queryset, order_field, *args, **kwargs):
        self.order_field = order_field
        super(GroupedModelSelect, self).__init__(queryset, *args, **kwargs)
        
    def _get_choices(self):
        # If self._choices is set, then somebody must have manually set
        # the property self.choices. In this case, just return self._choices.
        if hasattr(self, '_choices'):
            return self._choices
        # Otherwise, execute the QuerySet in self.queryset to determine the
        # choices dynamically. Return a fresh QuerySetIterator that has not been
        # consumed. Note that we're instantiating a new QuerySetIterator *each*
        # time _get_choices() is called (and, thus, each time self.choices is
        # accessed) so that we can ensure the QuerySet has not been consumed. This
        # construct might look complicated but it allows for lazy evaluation of
        # the queryset.
        final = [("","---------"),]
        group = None
        for item in self.queryset:
            if not group or group[0] != unicode(getattr(item, self.order_field)):
                if group:
                    final.append(group)
                group = [unicode(getattr(item, self.order_field)), []]
            group[1].append(self.make_choice(item))
        return final
    
    def make_choice(self, obj):
        return (obj.pk, "   "+self.label_from_instance(obj))

    choices = property(_get_choices, ChoiceField._set_choices)


    
