from django import forms

from main.models import AdmBotMessage


class SendForm(forms.Form):
    message = forms.ModelChoiceField(queryset=AdmBotMessage.objects.all(), label='', disabled=True)

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['message'].initial = AdmBotMessage.objects.get(pk=pk)

    class Meta:
        model = AdmBotMessage
        fields = ('message',)
        widgets = {'message': forms.HiddenInput, }
