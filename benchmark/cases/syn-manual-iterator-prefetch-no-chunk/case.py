from django.db import connection, models


class Tag(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        app_label = "sessions"


class Note(models.Model):
    text = models.CharField(max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, null=True)

    class Meta:
        app_label = "sessions"


with connection.schema_editor() as editor:
    editor.create_model(Tag)
    editor.create_model(Note)

tag = Tag.objects.create(name="t")

rows = list(Note.objects.prefetch_related("tag").iterator())
rows_ok = list(Note.objects.prefetch_related("tag").iterator(chunk_size=10))
