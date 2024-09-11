from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView

from .models import Note, Category
from datetime import timedelta

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists")
        return username

class RegistrationView(FormView):
    template_name = 'register.html'
    form_class = RegistrationForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        messages.success(self.request, 'Registration successful!')
        return super().form_valid(form)

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class LoginView(FormView):
    template_name = 'login.html'
    form_class = LoginForm
    success_url = reverse_lazy('notes')

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(self.request, username=username, password=password)
        if user is not None:
            login(self.request, user)
            messages.success(self.request, 'Login successful!')
            return super().form_valid(form)
        else:
            form.add_error(None, 'Invalid username or password')
            return self.form_invalid(form)

class NoteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Note
        fields = ['title', 'content']

    def save(self, commit=True):
        note = super().save(commit=False)
        if self.request:
            note.user = self.request.user
        if commit:
            note.save()
        return note


class NotesView(LoginRequiredMixin, FormView):
    template_name = 'notes.html'
    form_class = NoteForm
    success_url = reverse_lazy('notes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        week_offset = int(self.request.GET.get('week', 0))

        today = now().date()

        start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=6)

        notes = Note.objects.filter(
            user=self.request.user,
            created_at__date__gte=start_of_week,
            created_at__date__lte=end_of_week
        )

        context['notes_by_category'] = {
            'good_things': notes.filter(category__name='good-things'),
            'bad_things': notes.filter(category__name='bad-things'),
            'interest': notes.filter(category__name='interest'),
            'to_do': notes.filter(category__name='to-do'),
        }

        context['start_of_week'] = start_of_week
        context['end_of_week'] = end_of_week
        context['week_offset'] = week_offset

        return context

@csrf_protect
@login_required
def add_note_view(request):
    if request.method == 'POST':
        form = NoteForm(request.POST, request=request)
        if form.is_valid():
            note = form.save(commit=False)
            category_name = request.POST.get('category')
            category = Category.objects.get_or_create(name=category_name)
            note.category = category
            note.save()
            messages.success(request, 'Note added successfully!')
            return redirect('notes')
        else:
            messages.error(request, 'Error adding note.')
    else:
        form = NoteForm()

    return render(request, 'notes.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@csrf_protect
@login_required
def edit_note_view(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Note updated successfully!')
            return redirect('notes')
        else:
            messages.error(request, 'Error updating note.')
    else:
        form = NoteForm(instance=note)

    return render(request, 'notes.html', {'form': form, 'note': note})

@login_required
def delete_note_view(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted successfully!')
        return redirect('notes')
    return HttpResponseRedirect(reverse_lazy('notes'))