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
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


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
        product = Product(
            name="Fedora",
            description="A red hat",
            price=12.50,
            available=True,
            category=Category.CLOTHS,
        )
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

    def test_list_all_products(self):
        """It should List all Products in the database"""
        products = Product.all()
        self.assertEqual(products, [])
        for _ in range(5):
            product = ProductFactory()
            product.create()
        products = Product.all()
        self.assertEqual(len(products), 5)

    def test_find_by_name(self):
        """It should Find a Product by Name"""
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
        name = products[0].name
        count = len([product for product in products if product.name == name])
        found = Product.find_by_name(name)
        self.assertEqual(found.count(), count)
        for product in found:
            self.assertEqual(product.name, name)

    def test_read_a_product(self):
        """It should Read a Product"""
        product = ProductFactory()  # Step 1: Create a Product
        product.id = None  # Step 2: Ensure the ID is None before creating
        product.create()  # Save the product to the database
        self.assertIsNotNone(product.id)  # Step 3: Ensure an ID is assigned

        # Step 4: Fetch the product from the database
        found_product = Product.find(product.id)

        # Step 5: Verify that the retrieved product matches the original
        self.assertIsNotNone(found_product)
        self.assertEqual(found_product.id, product.id)
        self.assertEqual(found_product.name, product.name)
        self.assertEqual(found_product.description, product.description)
        self.assertEqual(found_product.price, product.price)
        self.assertEqual(found_product.available, product.available)
        self.assertEqual(found_product.category, product.category)

    def test_update_a_product(self):
        """It should Update a Product"""
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        # Log the product before update
        logging.debug("Before Update: %s", product)
        # Change description and update
        product.description = "Updated description"
        original_id = product.id
        product.update()
        # Log the product after update
        logging.debug("After Update: %s", product)
        self.assertEqual(product.id, original_id)
        self.assertEqual(product.description, "Updated description")
        # Fetch the updated product
        products = Product.all()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].id, original_id)
        self.assertEqual(products[0].description, "Updated description")

    def test_delete_a_product(self):
        """It should Delete a Product"""
        product = ProductFactory()
        product.create()
        self.assertEqual(len(Product.all()), 1)
        product.delete()
        self.assertEqual(len(Product.all()), 0)

    def test_find_by_availability(self):
        """It should find products by availability"""
        products = ProductFactory.create_batch(10)
        # Save each product to the database
        for product in products:
            product.create()
        # Retrieve the availability from the first product
        available = products[0].available
        # Count how many products have the same availability
        count = len([product for product in products if product.available == available])
        # Retrieve products from the database with the specified availability
        found = Product.find_by_availability(available)
        self.assertEqual(found.count(), count)
        # Ensure every retrieved product has the expected availability
        for product in found:
            self.assertEqual(product.available, available)

    def test_find_by_category(self):
        """It should find products by category"""
        products = ProductFactory.create_batch(10)
        # Save each product to the database
        for product in products:
            product.create()
        # Retrieve the category from the first product
        category = products[0].category
        # Count how many products have the same category
        count = len([product for product in products if product.category == category])
        # Retrieve products from the database with the specified category
        found = Product.find_by_category(category)
        self.assertEqual(found.count(), count)
        # Ensure every retrieved product has the expected category
        for product in found:
            self.assertEqual(product.category, category)

    def test_serialize_product(self):
        """It should serialize a Product into a dictionary"""
        product = ProductFactory()
        product.id = 1  # assign an id for testing
        serialized = product.serialize()
        self.assertEqual(serialized["id"], 1)
        self.assertEqual(serialized["name"], product.name)
        self.assertEqual(serialized["description"], product.description)
        self.assertEqual(serialized["price"], str(product.price))
        self.assertEqual(serialized["available"], product.available)
        self.assertEqual(serialized["category"], product.category.name)

    def test_deserialize_product(self):
        """It should deserialize a Product from a dictionary"""
        data = {
            "name": "Test Product",
            "description": "Test Description",
            "price": "19.99",
            "available": True,
            "category": "CLOTHS"
        }
        product = Product()
        product.deserialize(data)
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.description, "Test Description")
        self.assertEqual(product.price, Decimal("19.99"))
        self.assertEqual(product.available, True)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_deserialize_invalid_available(self):
        """It should raise DataValidationError for invalid available field type"""
        data = {
            "name": "Test Product",
            "description": "Test Description",
            "price": "19.99",
            "available": "not a boolean",
            "category": "CLOTHS"
        }
        product = Product()
        with self.assertRaises(DataValidationError) as context:
            product.deserialize(data)
        self.assertIn("Invalid type for boolean", str(context.exception))

    def test_update_without_id_raises_exception(self):
        """It should raise DataValidationError when update is called with no id"""
        product = ProductFactory()
        product.id = None
        with self.assertRaises(DataValidationError) as context:
            product.update()
        self.assertIn("Update called with empty ID field", str(context.exception))

    def test_find_by_price(self):
        """It should find products by price"""
        price_value = Decimal("99.99")
        # Create several products with the known price
        for _ in range(3):
            product = ProductFactory(price=price_value)
            product.create()
        # Create some products with a different price
        for _ in range(2):
            product = ProductFactory(price=Decimal("50.00"))
            product.create()
        found = Product.find_by_price(price_value)
        self.assertEqual(found.count(), 3)
        for product in found:
            self.assertEqual(product.price, price_value)


if __name__ == "__main__":
    unittest.main()
