from django.shortcuts import render
from django.views.generic import ListView, DetailView

from blog.models import Post


class IndexView(ListView):

    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'posts'


class PostView(DetailView):

    model = Post
    template_name = 'blog/post.html'
    context_object_name = 'post'
