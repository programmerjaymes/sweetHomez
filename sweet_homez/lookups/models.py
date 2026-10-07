from django.db import models
from django.utils.translation import get_language


class BilingualNameMixin(models.Model):
    name_en = models.CharField(max_length=150)
    name_sw = models.CharField(max_length=150, blank=True)

    class Meta:
        abstract = True

    @property
    def name(self):
        return self.name_sw or self.name_en if (get_language() or "en").startswith("sw") else self.name_en


class LookupCategory(BilingualNameMixin):
    code = models.SlugField(max_length=60, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "lookup categories"

    def __str__(self):
        return self.name_en


class LookupValue(BilingualNameMixin):
    category = models.ForeignKey(LookupCategory, on_delete=models.PROTECT, related_name="values")
    code = models.SlugField(max_length=60)
    description_en = models.TextField(blank=True)
    description_sw = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "sort_order", "name_en"]
        constraints = [
            models.UniqueConstraint(fields=["category", "code"], name="unique_lookup_category_code")
        ]

    def __str__(self):
        return f"{self.category.code}: {self.name_en}"


class Region(BilingualNameMixin):
    code = models.CharField(max_length=20, unique=True)
    country_code = models.CharField(max_length=2, default="TZ")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en


class District(BilingualNameMixin):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="districts")
    code = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en


class Ward(BilingualNameMixin):
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="wards")
    code = models.CharField(max_length=40, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en


class Locality(BilingualNameMixin):
    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name="localities")
    locality_type = models.ForeignKey(LookupValue, on_delete=models.PROTECT, related_name="localities")
    code = models.CharField(max_length=60, unique=True)
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]
        verbose_name_plural = "localities (villages/streets)"

    def __str__(self):
        return self.name_en
