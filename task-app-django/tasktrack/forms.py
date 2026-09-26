from django import forms
from tasktrack.domain.enums import (
    TaskPriority,
    RequirementType,
    RequirementPriority,
)

_CTRL = {"class": "form-control"}
_CTRL_TA = lambda h: {"class": "form-control", "style": f"min-height:{h}px;resize:vertical;"}
_SELECT = {"class": "form-select"}


class ContractEditForm(forms.Form):
    title = forms.CharField(
        max_length=120, label="Título",
        widget=forms.TextInput(attrs=_CTRL),
    )
    description = forms.CharField(
        required=False, label="Descrição (Markdown)",
        widget=forms.Textarea(attrs=_CTRL_TA(200)),
    )
    owner_id = forms.ChoiceField(
        label="Proprietário",
        widget=forms.Select(attrs=_SELECT),
    )

    def __init__(self, *args, users=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner_id"].choices = [(str(u.id), u.name) for u in users]


class ProjectEditForm(forms.Form):
    title = forms.CharField(
        max_length=120, label="Título",
        widget=forms.TextInput(attrs=_CTRL),
    )
    description = forms.CharField(
        required=False, label="Descrição (Markdown)",
        widget=forms.Textarea(attrs=_CTRL_TA(200)),
    )
    owner_id = forms.ChoiceField(
        label="Proprietário",
        widget=forms.Select(attrs=_SELECT),
    )

    def __init__(self, *args, users=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner_id"].choices = [(str(u.id), u.name) for u in users]


class TaskEditForm(forms.Form):
    title = forms.CharField(
        max_length=100, min_length=3, label="Título (3 a 100 caracteres)",
        widget=forms.TextInput(attrs=_CTRL),
    )
    description = forms.CharField(
        required=False, label="Descrição (Markdown)",
        widget=forms.Textarea(attrs=_CTRL_TA(400)),
    )
    priority = forms.ChoiceField(
        choices=[(p.value, f"{p.value}") for p in TaskPriority],
        label="Prioridade",
        widget=forms.Select(attrs=_SELECT),
    )
    assignee_id = forms.ChoiceField(
        required=False, label="Responsável",
        widget=forms.Select(attrs=_SELECT),
    )
    due_date = forms.DateField(
        required=False, label="Data de Vencimento",
        widget=forms.DateInput(attrs={**_CTRL, "type": "date"}),
    )
    github_url = forms.URLField(
        max_length=255, required=False, label="URL do GitHub",
        widget=forms.URLInput(attrs={**_CTRL, "placeholder": "https://github.com/..."}),
    )

    def __init__(self, *args, users=(), **kwargs):
        super().__init__(*args, **kwargs)
        choices = [("", "Nenhum")]
        choices += [(str(u.id), u.name) for u in users]
        self.fields["assignee_id"].choices = choices


class RequirementEditForm(forms.Form):
    title = forms.CharField(
        max_length=150, min_length=3, label="Título (3 a 150 caracteres)",
        widget=forms.TextInput(attrs=_CTRL),
    )
    description = forms.CharField(
        required=False, label="Descrição (Markdown)",
        widget=forms.Textarea(attrs=_CTRL_TA(200)),
    )
    type = forms.ChoiceField(
        choices=[(t.value, t.value) for t in RequirementType],
        label="Tipo",
        widget=forms.Select(attrs=_SELECT),
    )
    priority = forms.ChoiceField(
        choices=[(p.value, p.value) for p in RequirementPriority],
        label="Prioridade",
        widget=forms.Select(attrs=_SELECT),
    )
    task_ids = forms.MultipleChoiceField(
        required=False, label="Tarefas Vinculadas",
        widget=forms.CheckboxSelectMultiple,
    )
    actor_ids = forms.MultipleChoiceField(
        required=False, label="Atores Vinculados",
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, tasks=(), actors=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task_ids"].choices = [(str(t.id), t.title) for t in tasks]
        self.fields["actor_ids"].choices = [(str(a.id), a.name) for a in actors]


class ActorEditForm(forms.Form):
    name = forms.CharField(
        max_length=100, min_length=2, label="Nome (2 a 100 caracteres)",
        widget=forms.TextInput(attrs=_CTRL),
    )
    description = forms.CharField(
        required=False, label="Descrição (Markdown)",
        widget=forms.Textarea(attrs=_CTRL_TA(150)),
    )
