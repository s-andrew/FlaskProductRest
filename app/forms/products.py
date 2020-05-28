import datetime

from flask import current_app
from wtforms import (
    Form, Field, StringField, IntegerField, FloatField, DateTimeField, BooleanField, validators, ValidationError, widgets
)


class IntListField(Field):
    widget = widgets.TextInput()

    def _value(self):
        if self.data:
            return u', '.join(map(str, self.data))
        else:
            return u''

    def process_formdata(self, valuelist):
        self.data = valuelist if valuelist else None


class ProductForm(Form):
    name = StringField('name', [validators.length(max=50)])
    rating = FloatField('rating')
    featured = BooleanField('featured')
    expiration_date = DateTimeField('expiration_date')

    brand_id = IntegerField('brand_id')
    categories_ids = IntListField('categories', [
        validators.Length(
            min=1, max=5, message='Expected number of categories between %(min)s to %(max)s but %(length)s found.'
        )
    ])

    items_in_stock = IntegerField('items_in_stock')
    receipt_date = DateTimeField('receipt_date')

    def validate_expiration_date(self, field):
        expiration_date = field.data
        if expiration_date is None:
            return
        today = datetime.datetime.today()
        expires_in = expiration_date - today + datetime.timedelta(days=1)
        if expires_in < current_app.config['PRODUCT_EXPIRATION_TIME_DELTA']:
            raise ValidationError(
                f'"expiration_date" should expire not less than {current_app.config["PRODUCT_EXPIRATION_TIME_DELTA"]} '
                f'days since now but this "expiration_date" should expire in {expires_in.days} days'
            )

    @property
    def calculated_feature(self):
        return (
            self.featured.data or
            self.rating.data > current_app.config['PRODUCT_FEATURED_RATING_THRESHOLD']
        )


product_required_extra = {
    'name': [validators.InputRequired()],
    'rating': [validators.InputRequired()],
    'brand_id': [validators.InputRequired()],
    'categories': [validators.InputRequired()],
    'items_in_stock': [validators.InputRequired()],
}