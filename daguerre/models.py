import hashlib
import operator
from datetime import date, datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from six.moves import reduce

from daguerre.adjustments import registry


class Area(models.Model):
    """
    Represents an area of an image. Can be used to specify a crop. Also used
    for priority-aware automated image cropping.

    """
    storage_path = models.CharField(max_length=300)

    x1 = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    y1 = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    x2 = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    y2 = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    name = models.CharField(max_length=20, blank=True)
    priority = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                           default=3)

    @property
    def area(self):
        if None in (self.x1, self.y1, self.x2, self.y2):
            return None
        return self.width * self.height

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    def clean_fields(self, exclude=None):
        errors = {}

        if exclude is None:
            exclude = []

        try:
            super(Area, self).clean_fields(exclude)
        except ValidationError as e:
            errors.update(e.message_dict)

        if errors:
            raise ValidationError(errors)

    def clean(self):
        errors = []
        if self.x1 and self.x2 and self.x1 >= self.x2:
            errors.append("X1 must be less than X2.")
        if self.y1 and self.y2 and self.y1 >= self.y2:
            errors.append("Y1 must be less than Y2.")
        if errors:
            raise ValidationError(errors)

    def serialize(self):
        return dict((f.name, getattr(self, f.name))
                    for f in self._meta.fields)

    def __unicode__(self):
        if self.name:
            name = self.name
        else:
            name = u"(%d, %d, %d, %d / %d)" % (self.x1, self.y1, self.x2,
                                               self.y2, self.priority)
        return u"%s for %s" % (name, self.storage_path)

    class Meta:
        ordering = ('priority',)


@receiver(post_save, sender=Area)
@receiver(post_delete, sender=Area)
def delete_adjusted_images(sender, **kwargs):
    """
    If an Area is deleted or changed, delete all AdjustedImages for the
    Area's storage_path which have area-using adjustments.

    """
    storage_path = kwargs['instance'].storage_path
    qs = AdjustedImage.objects.filter(storage_path=storage_path)
    slug_qs = [models.Q(requested__contains=slug)
               for slug, adjustment in registry.items()
               if getattr(adjustment.adjust, 'uses_areas', True)]
    if slug_qs:
        qs = qs.filter(reduce(operator.or_, slug_qs))

    qs.delete()


def upload_to(instance, filename):
    first_dir = settings.DAGUERRE_PATH \
        if hasattr(settings, 'DAGUERRE_PATH') else 'daguerre'
    today = date.today()

    # custom settings whether to build daguerre image dir using date or hash
    # fallback to 'date'
    path_slots = settings.DAGUERRE_PATH_SLOTS_TYPE \
        if hasattr(settings, 'DAGUERRE_PATH_SLOTS_TYPE') else 'date'

    if path_slots == 'hash':
        hash_for_dir = hashlib.md5('{} {}'
            .format(filename, datetime.utcnow())).hexdigest()
        return '{0}/{1}/{2}/{3}'.format(
            first_dir, hash_for_dir[0:2], hash_for_dir[2:4], filename)
    else:
        return '{0}/{1}/{2:02}/{3:02}/{4}'.format(first_dir, today.year,
                                                today.month, today.day,
                                                filename)


class AdjustedImage(models.Model):
    """Represents a managed image adjustment."""
    storage_path = models.CharField(max_length=200)
    # The image name is a 20-character hash, so the max length with a 4-char
    # extension (jpeg) is 45. Maximum length for DAGUERRE_PATH string is 8.
    adjusted = models.ImageField(upload_to=upload_to,
                                 max_length=45)

    requested = models.CharField(max_length=100)

    def __unicode__(self):
        return u"{0}: {1}".format(self.storage_path, self.requested)
