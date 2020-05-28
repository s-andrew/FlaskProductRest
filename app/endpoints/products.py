import json

from flask import Blueprint, jsonify, url_for, request, Response
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import abort as standart_abort

from app import db
from app.forms.products import ProductForm, product_required_extra
from app.models.products import Product, Brand, Category

products_blueprint = Blueprint('products', __name__)


def abort(errors: dict, status: int = 400):
    standart_abort(Response(json.dumps({'errors': errors}), status=status))


def get_categories_by_ids_or_404(categories_ids):
    # TODO: спрятать в BaseQuery категорий
    categories = Category.query.filter(Category.id.in_(categories_ids)).all()
    if len(categories) < len(categories_ids):
        not_found_categories = set(categories_ids) - set(category.id for category in categories)
        abort({'categories': [f'Categories with id in [{", ".join(map(str, not_found_categories))}] not found.']}, 404)
    return categories


def get_brand_or_404(brand_id):
    # TODO: спрятать в BaseQuery
    brand = Brand.query.get(brand_id)
    if brand is None:
        abort({'brand_id': [f'Brand with id={brand_id} not found.']}, 404)
    return brand


def get_product_or_404(product_id):
    brand = Product.query.get(product_id)
    if brand is None:
        abort({'product_id': [f'Brand with id={product_id} not found.']}, 404)
    return brand


@products_blueprint.route('/products', methods=['GET'])
def get_products():
    return jsonify({
        'results': [p.serialized for p in Product.query.all()]
    })


@products_blueprint.route('/products', methods=['POST'])
def create_product():
    product_form = ProductForm(MultiDict(request.json))
    if not product_form.validate(extra_validators=product_required_extra):
        abort(product_form.errors, 400)

    new_product = Product(
        name=product_form.name.data,
        rating=product_form.rating.data,
        featured=product_form.calculated_feature,
        expiration_date=product_form.expiration_date.data,
        brand=get_brand_or_404(product_form.brand_id.data),
        categories=get_categories_by_ids_or_404(product_form.categories_ids.data),
        items_in_stock=product_form.items_in_stock.data,
        receipt_date=product_form.receipt_date.data,
    )
    db.session.add(new_product)
    db.session.commit()
    return (
        jsonify(result=new_product.serialized),
        201,
        {'Location': url_for('products.get_product', product_id=new_product.id)}
    )


@products_blueprint.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    return jsonify(result=get_product_or_404(product_id).serialized)


@products_blueprint.route('/products/<int:product_id>', methods=['PATCH'])
def update_product(product_id):
    product = get_product_or_404(product_id)
    product_form = ProductForm(formdata=MultiDict(request.json), obj=product)
    if product_form.categories_ids.data is None:
        product_form.categories_ids.data = [category.id for category in product.categories]
    product_form.items_in_stock.data = product.items_in_stock

    if not product_form.validate():
        abort(product_form.errors, 400)

    product_form.populate_obj(product)
    if product_form.categories_ids.data is not None:
        product.categories = get_categories_by_ids_or_404(product_form.categories_ids.data)
    if product_form.rating.data is not None:
        product.featured = product_form.calculated_feature
    if product_form.brand_id.data is not None:
        product.brand = get_brand_or_404(product_form.brand_id.data)

    db.session.add(product)
    db.session.commit()

    return jsonify(result=product.serialized)


@products_blueprint.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = get_product_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return '', 204
