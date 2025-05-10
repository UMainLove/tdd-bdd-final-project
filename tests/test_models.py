# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, DataValidationError, db
from service import app
from tests.factories import ProductFactory
from service.common import error_handlers as eh, status as http_status
from service.routes import check_content_type
from werkzeug.exceptions import HTTPException
from service import app as flask_app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

# -------------------------------------------------------------------
# Extra coverage for error paths (unittest + app context friendly)
# -------------------------------------------------------------------

def test_error_handlers_and_bad_deserialize():
    """Covers remaining error-handler branches + deserialize errors"""
    # exercise the error-handler helpers
    with flask_app.app_context():
        assert eh.bad_request("x")[1]             == http_status.HTTP_400_BAD_REQUEST
        assert eh.not_found("x")[1]               == http_status.HTTP_404_NOT_FOUND
        assert eh.method_not_supported("x")[1]    == http_status.HTTP_405_METHOD_NOT_ALLOWED
        assert eh.mediatype_not_supported("x")[1] == http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        assert eh.internal_server_error("x")[1]   == http_status.HTTP_500_INTERNAL_SERVER_ERROR

    # deserialize() negative paths
    prod = Product()
    try:
        prod.deserialize({"name": "Foo"})         # missing fields
    except DataValidationError:
        pass
    else:
        assert False, "deserialize should fail on missing fields"

    bad = {
        "name": "Foo", "description": "Bar", "price": "1.23",
        "available": "yes", "category": "FOOD"    # bad boolean type
    }
    try:
        prod.deserialize(bad)
    except DataValidationError:
        pass
    else:
        assert False, "deserialize should fail on bad boolean type"


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    #
    # ADD YOUR TEST CASES HERE
    #
    def test_read_a_product(self):
        """It should Read a Product"""
        # ------------------------------------------------------------------
        # Arrange: create and save a fake product
        # ------------------------------------------------------------------
        product = ProductFactory()
        product.id = None          # ensure SQLAlchemy assigns the PK
        product.create()
        self.assertIsNotNone(product.id)  # sanity-check it was saved

        # ------------------------------------------------------------------
        # Act: fetch the same product back from the DB
        # ------------------------------------------------------------------
        found_product = Product.find(product.id)

        # ------------------------------------------------------------------
        # Assert: every persisted field matches what we created
        # ------------------------------------------------------------------
        self.assertIsNotNone(found_product)
        self.assertEqual(found_product.id, product.id)
        self.assertEqual(found_product.name, product.name)
        self.assertEqual(found_product.description, product.description)
        self.assertEqual(Decimal(found_product.price), product.price)
        self.assertEqual(found_product.available, product.available)
        self.assertEqual(found_product.category, product.category)
        # ───────────────────────── extra coverage ──────────────────────────
        # exercise the serialize helper
        data_dict = found_product.serialize()
        self.assertEqual(data_dict["id"], found_product.id)
        self.assertEqual(data_dict["name"], found_product.name)


    def test_update_a_product(self):
        """It should Update a Product"""
        product = ProductFactory()
        product.id = None
        product.create()
        original_id = product.id

        # update one field
        new_description = "Updated description for unit-test"
        product.description = new_description
        product.update()

        # verify in DB
        fetched = Product.find(original_id)
        self.assertEqual(fetched.description, new_description)

        # extra: serialize / deserialize round-trip
        clone = Product().deserialize(product.serialize())
        self.assertEqual(clone.name, product.name)

        # extra: bad deserialize triggers DataValidationError
        bad = product.serialize()
        bad["available"] = "yes"          # must be bool
        with self.assertRaises(DataValidationError):
            Product().deserialize(bad)


    def test_delete_a_product(self):
        """It should Delete a Product"""
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertEqual(len(Product.all()), 1)

        product.delete()
        self.assertEqual(len(Product.all()), 0)

        # extra: calling update() on an unsaved object raises error
        with self.assertRaises(DataValidationError):
            Product().update()

        
    def test_list_all_products(self):
        """It should List all Products in the database"""
        self.assertEqual(len(Product.all()), 0)

        for _ in range(5):
            p = ProductFactory()
            p.id = None
            p.create()

        self.assertEqual(len(Product.all()), 5)

        # ── coverage helpers ────────────────────────────────────────────
        
        client = app.test_client()
        self.assertEqual(client.get("/health").status_code, http_status.HTTP_200_OK)
        self.assertEqual(client.get("/").status_code, http_status.HTTP_200_OK)

        # content-type checker good & bad
        with app.test_request_context("/", headers={"Content-Type": "application/json"}):
            check_content_type("application/json")
        with self.assertRaises(HTTPException):
            with app.test_request_context("/", headers={"Content-Type": "text/plain"}):
                check_content_type("application/json")

        # exercise every error-handler function
        with app.app_context():
            self.assertEqual(eh.bad_request("problem")[1], http_status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                eh.request_validation_error(DataValidationError("oops"))[1],
                http_status.HTTP_400_BAD_REQUEST,
            )
            self.assertEqual(eh.not_found("x")[1], http_status.HTTP_404_NOT_FOUND)
            self.assertEqual(
                eh.method_not_supported("x")[1], http_status.HTTP_405_METHOD_NOT_ALLOWED
            )
            self.assertEqual(
                eh.mediatype_not_supported("x")[1],
                http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
            self.assertEqual(
                eh.internal_server_error("x")[1],
                http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    def test_find_by_name(self):
        """It should Find a Product by Name"""
        # -------------------------------------------------------------
        # Arrange: build and save 5 products
        # -------------------------------------------------------------
        products = ProductFactory.create_batch(5)
        for prod in products:
            prod.id = None
            prod.create()

        # choose the name of the first product
        target_name = products[0].name

        # how many of the batch share that name?
        expected_count = len([p for p in products if p.name == target_name])

        # -------------------------------------------------------------
        # Act: query by name
        # -------------------------------------------------------------
        found_products = Product.find_by_name(target_name).all()

        # -------------------------------------------------------------
        # Assert: counts and names match
        # -------------------------------------------------------------
        self.assertEqual(len(found_products), expected_count)
        for prod in found_products:
            self.assertEqual(prod.name, target_name)

    def test_find_by_availability(self):
        """It should Find Products by Availability"""
        # -------------------------------------------------------------
        # Arrange: create and persist a batch of 10 products
        # -------------------------------------------------------------
        products = ProductFactory.create_batch(10)
        for prod in products:
            prod.id = None
            prod.create()

        # choose the availability of the first product (True or False)
        target_available = products[0].available

        # count how many of the batch share that value
        expected_count = len([p for p in products if p.available == target_available])

        # -------------------------------------------------------------
        # Act: query the database by availability
        # -------------------------------------------------------------
        found_products = Product.find_by_availability(target_available).all()

        # -------------------------------------------------------------
        # Assert: counts and availability values match
        # -------------------------------------------------------------
        self.assertEqual(len(found_products), expected_count)
        for prod in found_products:
            self.assertEqual(prod.available, target_available)

    def test_find_by_category(self):
        """It should Find Products by Category"""
        # -------------------------------------------------------------
        # Arrange: create and persist 10 products
        # -------------------------------------------------------------
        products = ProductFactory.create_batch(10)
        for prod in products:
            prod.id = None
            prod.create()

        # pick the category of the first product
        target_category = products[0].category

        # how many in the batch share that category?
        expected_count = len([p for p in products if p.category == target_category])

        # -------------------------------------------------------------
        # Act: query the DB by that category
        # -------------------------------------------------------------
        found_products = Product.find_by_category(target_category).all()

        # -------------------------------------------------------------
        # Assert: counts and categories match
        # -------------------------------------------------------------
        self.assertEqual(len(found_products), expected_count)
        for prod in found_products:
            self.assertEqual(prod.category, target_category)

        # ───────────────────────── extra coverage ──────────────────────────
        target_price = Decimal("42.42")
        ProductFactory(price=target_price).create()
        ProductFactory(price=target_price).create()

        hits = Product.find_by_price(target_price).all()
        self.assertEqual(len(hits), 2)
        for h in hits:
            self.assertEqual(Decimal(h.price), target_price)

