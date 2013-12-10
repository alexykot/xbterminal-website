from django.shortcuts import render

def index(request):
  return render(request,'website/index.html',{})

def landing(request):
  return render(request,'website/landing.html',{})

def landing_faq(request):
  return render(request,'website/faq.html',{})
