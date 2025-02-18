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
from service.models import db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# logging.disable(logging.CRITICAL)

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up previous tests
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
    #  TEST CASES
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

    # ------------------------------
    # TEST CREATE
    # ------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Ensure the Location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Verify the product data
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

    # ------------------------------
    # TEST READ
    # ------------------------------
    def test_get_product(self):
        """It should Get a single Product"""
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

    def test_get_product_not_found(self):
        """It should not Get a Product that's not found"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    # ------------------------------
    # TEST UPDATE
    # ------------------------------
    def test_update_product(self):
        """It should Update an existing Product"""
        test_product = self._create_products(1)[0]
        update_data = test_product.serialize()
        update_data["name"] = "Updated Name"
        response = self.client.put(f"{BASE_URL}/{test_product.id}", json=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], "Updated Name")

    def test_update_product_not_found(self):
        """It should not Update a Product that doesn't exist"""
        test_product = ProductFactory()
        update_data = test_product.serialize()
        update_data["name"] = "Updated Name"
        response = self.client.put(f"{BASE_URL}/0", json=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    # ------------------------------
    # TEST DELETE
    # ------------------------------
    def test_delete_product(self):
        """It should Delete an existing Product"""
        test_product = self._create_products(1)[0]
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Confirm deletion by trying to get the deleted product
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product_not_found(self):
        """It should not Delete a Product that doesn't exist"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    # ------------------------------
    # TEST LIST and FILTERS
    # ------------------------------
    def test_list_products(self):
        """It should List all Products"""
        self._create_products(3)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)

    def test_list_products_by_name(self):
        """It should List Products filtered by name"""
        # Create a product with a unique name
        product_unique = ProductFactory()
        product_unique.name = "UniqueName"
        response = self.client.post(BASE_URL, json=product_unique.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Create another random product
        self._create_products(1)
        # Filter by name (case-insensitive, partial match)
        response = self.client.get(f"{BASE_URL}?name=unique")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "UniqueName")

    def test_list_products_by_category(self):
        """It should List Products filtered by category"""
        # Create a product with a unique category
        product_unique = ProductFactory()
        product_unique.category.name = "Electronics"
        response = self.client.post(BASE_URL, json=product_unique.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Create another product with a different category
        self._create_products(1)
        # Filter by category (exact match)
        response = self.client.get(f"{BASE_URL}?category=Electronics")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertGreaterEqual(len(data), 1)
        for prod in data:
            self.assertEqual(prod["category"], "Electronics")

    def test_list_products_by_availability(self):
        """It should List Products filtered by availability"""
        # Create two products with different availability statuses
        product_available = ProductFactory()
        product_available.available = True
        product_not_available = ProductFactory()
        product_not_available.available = False
        self.client.post(BASE_URL, json=product_available.serialize())
        self.client.post(BASE_URL, json=product_not_available.serialize())
        # Filter available=True
        response = self.client.get(f"{BASE_URL}?available=True")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        for prod in data:
            self.assertTrue(prod["available"])
        # Filter available=False
        response = self.client.get(f"{BASE_URL}?available=False")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        for prod in data:
            self.assertFalse(prod["available"])

    ############################################################
    # Additional Utility functions
    ############################################################
    def get_product_count(self):
        """Return the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        return len(data)
