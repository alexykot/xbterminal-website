from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from ckeditor.fields import RichTextField


class Post(models.Model):

    heading = models.CharField(max_length=200)
    text = RichTextField()
    pub_date = models.DateTimeField('Publication date', default=timezone.now)

    class Meta:
        ordering = ["-pub_date"]

    def __str__(self):
        return self.heading
