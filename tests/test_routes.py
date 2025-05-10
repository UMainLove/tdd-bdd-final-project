######################################################################
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
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product, Category
from tests.factories import ProductFactory
from urllib.parse import quote_plus

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        #init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    #
    # ADD YOUR TEST CASES HERE
    #
    def test_get_product(self):
        """It should Get a single Product"""
        # Arrange: create one product in the DB
        test_product = self._create_products(1)[0]

        # Act: issue GET /products/<id>
        response = self.client.get(f"{BASE_URL}/{test_product.id}")

        # Assert: success status and correct payload
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)
        self.assertEqual(data["description"], test_product.description)
        self.assertEqual(Decimal(data["price"]), test_product.price)
        self.assertEqual(data["available"], test_product.available)
        self.assertEqual(data["category"], test_product.category.name)

    def test_get_product_not_found(self):
        """It should not Get a Product that's not found"""
        # Act: ask for a product id that can’t exist
        response = self.client.get(f"{BASE_URL}/0")

        # Assert: service responds with 404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    # ----------------------------------------------------------
    # TEST UPDATE  (will fail until the route is coded)
    # ----------------------------------------------------------
    def test_update_product(self):
        """It should Update an existing Product"""
        # ---------- Arrange ----------
        # create a product so we have something to update
        test_product = ProductFactory()
        resp = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_product = resp.get_json()

        # ---------- Act ----------
        # change one field and send PUT /products/<id>
        new_description = "unknown"
        new_product["description"] = new_description
        resp = self.client.put(
            f"{BASE_URL}/{new_product['id']}", json=new_product
        )

        # ---------- Assert ----------
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        updated_product = resp.get_json()
        self.assertEqual(updated_product["description"], new_description)

    # ----------------------------------------------------------
    # TEST DELETE  (will fail until route is coded)
    # ----------------------------------------------------------
    def test_delete_product(self):
        """It should Delete a Product"""
        # ---------- Arrange ----------
        products = self._create_products(5)
        initial_count = self.get_product_count()
        test_product = products[0]

        # ---------- Act ----------
        resp = self.client.delete(f"{BASE_URL}/{test_product.id}")

        # ---------- Assert ----------
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")

        # the resource is gone
        resp = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # one less in the collection
        self.assertEqual(self.get_product_count(), initial_count - 1)

    # ----------------------------------------------------------
    # TEST LIST ALL
    # ----------------------------------------------------------
    def test_get_product_list(self):
        """It should Get a list of Products"""
        # Arrange: create 5 products
        self._create_products(5)

        # Act: fetch the collection
        resp = self.client.get(BASE_URL)

        # Assert: success and correct count
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)

    # ----------------------------------------------------------
    # TEST LIST BY NAME
    # ----------------------------------------------------------
    def test_query_by_name(self):
        """It should Query Products by name"""
        products = self._create_products(5)

        # name we will filter on
        test_name = products[0].name
        name_count = len([p for p in products if p.name == test_name])

        # call   GET /products?name=<test_name>
        encoded_name = quote_plus(test_name)
        resp = self.client.get(f"{BASE_URL}?name={encoded_name}") 

        # success?
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        self.assertEqual(len(data), name_count)

        # every returned item must have the requested name
        for item in data:
            self.assertEqual(item["name"], test_name)


    # ----------------------------------------------------------
    # TEST LIST BY CATEGORY
    # ----------------------------------------------------------
    def test_query_by_category(self):
        """It should Query Products by category"""
        products = self._create_products(10)

        # pick the category of the first product
        category = products[0].category.name

        # how many of our seed products share this category?
        found_count = len([p for p in products if p.category.name == category])
        logging.debug("Expecting %d products with category %s", found_count, category)

        # make request: GET /products?category=<category>
        resp = self.client.get(f"{BASE_URL}?category={category}")

        # success?
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        self.assertEqual(len(data), found_count)

        # every returned product should match the category
        for item in data:
            self.assertEqual(item["category"], category)


    # ----------------------------------------------------------
    # TEST LIST BY AVAILABILITY
    # ----------------------------------------------------------
    def test_query_by_availability(self):
        """It should Query Products by availability"""
        products = self._create_products(10)

        # how many of the seed products are available?
        available_products = [p for p in products if p.available]
        available_count = len(available_products)
        logging.debug("Expecting %d available products", available_count)

        # request: GET /products?available=true
        resp = self.client.get(f"{BASE_URL}?available=true")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()

        # number matches?
        self.assertEqual(len(data), available_count)

        # every returned product must be marked available
        for item in data:
            self.assertTrue(item["available"])



    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
