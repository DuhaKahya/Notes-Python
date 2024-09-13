from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
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
        password = form.cleaned_data['password']

        try:
            validate_password(password)
        except ValidationError as e:
            form.add_error('password', e.messages)
            return self.form_invalid(form)
        
        
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
                
        return render(self.request, self.template_name, {
            'form': self.get_form(),
            'account_created': True 
        })
    
    def form_invalid(self, form):
        return render(self.request, self.template_name, {
            'form': form
    })

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
            return super().form_valid(form)
        else:
            form.add_error(None, 'Invalid username or password')
            return self.form_invalid(form)

class NoteForm(forms.ModelForm):
    # Constructor, calls when created an instance of a class
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

        # Get the current week offset for filtering notes
        week_offset = int(self.request.GET.get('week', 0))
        today = now().date()
        start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=6)

        # Filter notes based on the current week and user
        notes = Note.objects.filter(
            user=self.request.user,
            created_at__date__gte=start_of_week,
            created_at__date__lte=end_of_week
        )

        # Dynamically fetch all categories
        categories = Category.objects.all()

        # Create a dictionary to store notes for each category
        notes_by_category = {}
        for category in categories:
            notes_by_category[category.name] = notes.filter(category=category)

        context['categories'] = categories
        context['notes_by_category'] = notes_by_category
        context['start_of_week'] = start_of_week
        context['end_of_week'] = end_of_week
        context['week_offset'] = week_offset

        return context


@login_required
@csrf_protect
def add_note_view(request):
    if request.method == 'POST':
        form = NoteForm(request.POST, request=request)
        if form.is_valid():
            note = form.save(commit=False)
            category_name = request.POST.get('category')

            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                return render(request, 'notes.html', {'form': form})

            note.category = category
            note.save()
            return redirect('notes')
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
            return redirect('notes')
    else:
        form = NoteForm(instance=note)

    return render(request, 'notes.html', {'form': form, 'note': note})

@login_required
def delete_note_view(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if request.method == 'POST':
        note.delete()
        return redirect('notes')
    return HttpResponseRedirect(reverse_lazy('notes'))