from django.contrib.auth.models import User

from django.shortcuts import render, redirect
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy

from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from django.shortcuts import get_object_or_404
from django.views import View
from .models import Task
from django import forms
from datetime import datetime
from django.utils import timezone

class CustomLoginView(LoginView):
    template_name = 'base/login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('tasks')

class RegisterPage(FormView):
    template_name = 'base/register.html'
    form_class = UserCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('tasks')

    def form_valid(self, form):
        # Check if all fields are empty
        if all(not form.cleaned_data[field] for field in form.fields):
            form.add_error(None, "Fields cannot be empty.")
            return self.form_invalid(form)

        # Rest of your existing code
        username = form.cleaned_data['username']
        password1 = form.cleaned_data['password1']
        password2 = form.cleaned_data['password2']

        if User.objects.filter(username=username).exists():
            form.add_error('username', 'This username is already taken.')

        if len(password1) < 8:
            form.add_error('password1', 'This password is too short. It must contain at least 8 characters.')
        if password1 != password2:
            form.add_error('password1', 'Passwords do not match.')
            form.add_error('password2', 'Passwords do not match.')

        if form.errors:
            return self.form_invalid(form)

        user = form.save()
        if user is not None:
            login(self.request, user)
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("tasks")

        return super().dispatch(request, *args, **kwargs)

class TaskList(LoginRequiredMixin, ListView):
    model = Task
    context_object_name = 'tasks'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks'] = context['tasks'].filter(user=self.request.user)
        context['count'] = context['tasks'].filter(complete=False).count()

        sort_by = self.request.GET.get('sort_by', 'complete')
        sort_order = self.request.GET.get('sort_order', 'asc')

        next_sort_order = 'desc' if sort_order == 'asc' else 'asc'

        context['sort_by'] = sort_by
        context['sort_order'] = sort_order
        context['next_sort_order'] = next_sort_order

        search_input = self.request.GET.get('search-area') or ''
        if search_input:
            context['tasks'] = context['tasks'].filter(title__startswith=search_input)

        context['search_input'] = search_input

        return context

    def get_queryset(self):
        queryset = super().get_queryset()

        sort_by = self.request.GET.get('sort_by', 'complete')
        sort_order = self.request.GET.get('sort_order', 'asc')
        status_filter = self.request.GET.get('status', '')
        search_input = self.request.GET.get('search-area', '')

        if status_filter:
            queryset = queryset.filter(complete=(status_filter == 'done'))

        if search_input:
            queryset = queryset.filter(title__icontains=search_input)

        if sort_by == 'title':
            queryset = queryset.order_by('title' if sort_order == 'asc' else '-title')
        elif sort_by == 'created':
            queryset = queryset.order_by('created' if sort_order == 'asc' else '-created')
        elif sort_by == 'complete':
            queryset = queryset.order_by('complete' if sort_order == 'asc' else '-complete')
        else:
            queryset = queryset.order_by('due_date' if sort_order == 'asc' else '-due_date')

        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            queryset = queryset.filter(created__range=[start_date, end_date])

        return queryset
class TaskDetail(LoginRequiredMixin, DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'base/task.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_object()
        context['due_date'] = task.due_date
        return context

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'complete', 'due_date']

        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class TaskCreate(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    success_url = reverse_lazy('tasks')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(TaskCreate, self).form_valid(form)
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(TaskCreate, self).form_valid(form)
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        current_datetime = timezone.now().strftime('%Y-%m-%dT%H:%M')
        form.fields['due_date'].widget = forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'min': current_datetime,
                'format': '%Y-%m-%dT%H:%M',
            }
        )
        return form
class TaskUpdate(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    success_url = reverse_lazy('tasks')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        current_datetime = timezone.now().strftime('%Y-%m-%dT%H:%M')
        form.fields['due_date'].widget = forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'min': current_datetime,
                'format': '%Y-%m-%dT%H:%M',
            }
        )
        return form
class TaskStatusUpdate(View):
    def post(self, request, *args, **kwargs):
        task_id = request.POST.get('task_id')
        task = get_object_or_404(Task, id=task_id)
        new_status = request.POST.get('status')

        if new_status in ('in-progress', 'done'):
            task.complete = (new_status == 'done')
            task.save()

        return redirect('tasks')
class DeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    context_object_name = 'task'
    success_url = reverse_lazy('tasks')

