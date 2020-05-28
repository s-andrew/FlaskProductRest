import datetime
import json

import pytest
from flask import url_for, Response

from app.models.products import Brand, Category, Product, products_categories


AUTO_FEATURED_BY_RATING_CASES = [
    (8, None, False),
    (8, False, False),
    (8, True, True),
    (8.1, None, True),
    (8.1, False, True),
    (8.1, True, True),
]


CATEGORIES_COUNT_CASES = [
    ([1], False),
    ([1, 2, 3, 4, 5], False),
    ([1, 2, 3, 4, 5, 6], True),
]


@pytest.fixture(scope='function')
def setup_data(session):
    Brand.query.delete()
    Category.query.delete()
    Product.query.delete()
    session.execute(products_categories.delete())
    session.commit()
    brands = [
        Brand(id=1, name='KEK', country_code='US'),
        Brand(id=2, name='LOL', country_code='DE'),
    ]
    categories = [
        Category(id=1, name='A'),
        Category(id=2, name='B'),
        Category(id=3, name='C'),
        Category(id=4, name='D'),
        Category(id=5, name='E'),
        Category(id=6, name='F'),
    ]
    exist_product = Product(
        id=1,
        name='Foo',
        rating=5,
        brand_id=1,
        categories=categories[:3],
        items_in_stock=666,
    )
    session.add_all(brands)
    session.add_all(categories)
    session.add(exist_product)
    session.commit()


@pytest.fixture(scope='function')
def minimal_product_data(setup_data):
    """Valid product data (only required fields)"""
    return {
        'name': 'Bar',
        'rating': .5,
        'brand_id': 1,
        'categories_ids': [1],
        'items_in_stock': 111,
    }


def get_expiration_date_string(days_before_expiration):
    expiration_date = datetime.datetime.utcnow() + datetime.timedelta(days=days_before_expiration)
    # TODO: Сделать mock datetime.datetime.utcnow и настроить сериализацию дат. Затем убрать все танцы с форматами дат
    expiration_date = expiration_date.replace(microsecond=0)
    return datetime.datetime.strftime(expiration_date, '%Y-%m-%d %H:%M:%S')


@pytest.fixture(scope='function')
def full_product_data(minimal_product_data):
    """Valid product data (all fields includes)"""
    minimal_product_data.update({
        'featured': True,
        'expiration_date': get_expiration_date_string(100),
        'receipt_date': get_expiration_date_string(0),
    })
    return minimal_product_data


def test_create_product_minimal(client, minimal_product_data):
    response = client.post(url_for('products.create_product'), json=minimal_product_data)
    assert response.status_code == 201
    result = json.loads(response.get_data())['result']
    assert response.headers['Location'] == url_for('products.get_product', product_id=result['id'])

    assert minimal_product_data['name'] == result['name']
    assert minimal_product_data['rating'] == result['rating']
    assert minimal_product_data['brand_id'] == result['brand']['id']
    assert minimal_product_data['categories_ids'] == [category['id'] for category in result['categories']]
    assert minimal_product_data['items_in_stock'] == result['items_in_stock']
    assert not result['featured']


def test_create_product_full(client, full_product_data):
    response = client.post(url_for('products.create_product'), json=full_product_data)
    assert response.status_code == 201
    result = json.loads(response.get_data())['result']
    assert response.headers['Location'] == url_for('products.get_product', product_id=result['id'])

    assert full_product_data['name'] == result['name']
    assert full_product_data['rating'] == result['rating']
    assert full_product_data['featured'] == result['featured']
    assert full_product_data['brand_id'] == result['brand']['id']
    assert full_product_data['categories_ids'] == [category['id'] for category in result['categories']]
    assert full_product_data['items_in_stock'] == result['items_in_stock']

    result_expiration_date = datetime.datetime.strptime(result['expiration_date'], '%a, %d %b %Y %H:%M:%S %Z')
    assert result_expiration_date == datetime.datetime.strptime(
        full_product_data['expiration_date'], '%Y-%m-%d %H:%M:%S'
    )

    result_receipt_date = datetime.datetime.strptime(result['receipt_date'], '%a, %d %b %Y %H:%M:%S %Z')
    assert result_receipt_date == datetime.datetime.strptime(
        full_product_data['receipt_date'], '%Y-%m-%d %H:%M:%S'
    )


@pytest.mark.parametrize('rating, featured, expect_featured', AUTO_FEATURED_BY_RATING_CASES)
def test_create_product_featured(client, minimal_product_data, rating, featured, expect_featured):
    minimal_product_data['rating'] = rating
    if featured is not None:
        minimal_product_data['featured'] = featured

    response = client.post(url_for('products.create_product'), json=minimal_product_data)
    assert response.status_code == 201
    result = json.loads(response.get_data())['result']
    assert result['rating'] == rating
    assert result['featured'] == expect_featured


@pytest.mark.parametrize('rating, featured, expect_featured', AUTO_FEATURED_BY_RATING_CASES)
def test_update_product_rating_and_featured(client, rating, featured, expect_featured):
    update_data = {'rating': rating}
    if featured is not None:
        update_data['featured'] = featured

    response = client.patch(url_for('products.update_product', product_id=1), json=update_data)

    assert response.status_code == 200
    result = json.loads(response.get_data())['result']
    assert result['rating'] == rating
    assert result['featured'] == expect_featured


@pytest.mark.parametrize(
    'days_before_expiration, error_expected', [
        (29, True),
        (30, False),
    ]
)
def test_create_product_expiration_date(client, minimal_product_data, days_before_expiration, error_expected):

    minimal_product_data['expiration_date'] = get_expiration_date_string(days_before_expiration)

    response = client.post(url_for('products.create_product'), json=minimal_product_data)
    assert error_expected == (response.status_code == 400)

    if error_expected:
        errors = json.loads(response.get_data())['errors']
        assert errors['expiration_date'][0].startswith('"expiration_date" should expire not less than')


@pytest.mark.parametrize(
    'days_before_expiration, error_expected', [
        (29, True),
        (30, False),
    ]
)
def test_update_product_expiration_date(client, days_before_expiration, error_expected):
    # TODO: настроить сериализацию дат и убрать пляски с форматами
    expiration_date = get_expiration_date_string(days_before_expiration)
    response = client.patch(url_for('products.update_product', product_id=1), json={'expiration_date': expiration_date})
    assert error_expected == (response.status_code == 400)
    if not error_expected:
        result_expiration_date = datetime.datetime.strptime(
            json.loads(response.get_data())['result']['expiration_date'],
            '%a, %d %b %Y %H:%M:%S %Z'
        )
        assert result_expiration_date == datetime.datetime.strptime(expiration_date, '%Y-%m-%d %H:%M:%S')


@pytest.mark.parametrize(
    'name, error_expected', [
        ('Normal Length Name', False),
        ('Too Long Name' * 100, True),
    ]
)
def test_update_product_name(client, name, error_expected):
    response = client.patch(url_for('products.update_product', product_id=1), json={'name': name})
    assert error_expected == (response.status_code == 400)

    if not error_expected:
        assert json.loads(response.get_data())['result']['name'] == name


@pytest.mark.parametrize('categories_ids, error_expected', CATEGORIES_COUNT_CASES)
def test_create_products_categories(client, minimal_product_data, categories_ids, error_expected):
    minimal_product_data['categories_ids'] = categories_ids
    response = client.post(url_for('products.create_product'), json=minimal_product_data)

    if not error_expected:
        assert response.status_code == 201
        result = json.loads(response.get_data())['result']
        assert [category['id'] for category in result['categories']] == categories_ids
    else:
        assert response.status_code == 400


@pytest.mark.parametrize('categories_ids, error_expected', CATEGORIES_COUNT_CASES)
def test_update_products_categories(client, categories_ids, error_expected):
    response = client.patch(url_for('products.update_product', product_id=1), json={'categories_ids': categories_ids})

    if not error_expected:
        assert response.status_code == 200
        result = json.loads(response.get_data())['result']
        assert [category['id'] for category in result['categories']] == categories_ids
    else:
        assert response.status_code == 400


def test_create_products_categories_not_found(client, minimal_product_data):
    minimal_product_data['categories_ids'] = [747]
    response = client.post(url_for('products.create_product'), json=minimal_product_data)
    assert response.status_code == 404


def test_update_products_categories_not_found(client):
    response = client.patch(url_for('products.update_product', product_id=1), json={'categories_ids': [747]})
    assert response.status_code == 404


def test_create_products_brand_not_found(client, minimal_product_data):
    minimal_product_data['brand_id'] = [747]
    response = client.post(url_for('products.create_product'), json=minimal_product_data)
    assert response.status_code == 404


def test_update_products_brand_not_found(client):
    response = client.patch(url_for('products.update_product', product_id=1), json={'brand_id': [747]})
    assert response.status_code == 404


def test_delete_product(client):
    response = client.delete(url_for('products.delete_product', product_id=1))
    assert response.status_code == 204


def test_delete_product_not_found(client):
    response = client.delete(url_for('products.delete_product', product_id=747))
    assert response.status_code == 404
