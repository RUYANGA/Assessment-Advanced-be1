from django.db import models


class RequestItem(models.Model):
    purchase_request = models.ForeignKey(
        "purches.PurchaseRequest", related_name="items", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price
