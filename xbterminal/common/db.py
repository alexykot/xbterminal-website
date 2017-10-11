def refresh_for_update(obj):
    model = obj._meta.model
    return model.objects.select_for_update().get(pk=obj.pk)
