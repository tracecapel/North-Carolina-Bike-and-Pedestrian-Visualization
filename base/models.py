from django.db import models

from django.db import models

class Counter(models.Model):
    counter_id = models.IntegerField(primary_key=True)
    counter_code = models.CharField(max_length=100)
    counter_name = models.CharField(max_length=255)
    vendor = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    counter_notes = models.TextField(blank=True, null=True)

class Datastream(models.Model):
    datastream_id = models.IntegerField(primary_key=True)
    counter = models.ForeignKey(Counter, on_delete=models.CASCADE)
    datastream_type = models.CharField(max_length=100)
    datastream_name = models.CharField(max_length=255)
    datastream_direction = models.CharField(max_length=50)
    datastream_notes = models.TextField(blank=True, null=True)

class Count(models.Model):
    count_id = models.IntegerField(primary_key=True)
    datastream = models.ForeignKey(Datastream, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    raw_count = models.IntegerField(null=True)
    maxday = models.IntegerField(null=True)
    maxhour = models.IntegerField(null=True)
    gap = models.IntegerField(null=True)
    zero = models.IntegerField(null=True)
    stat = models.IntegerField(null=True)
    cleaned_count = models.FloatField(null=True)


