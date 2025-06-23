### Proposition 1: Should a field be added to the 'Product' table which stores every specification of that product in json format?

#### Status: Pending

#### Context
we need to have a field in the 'Product' table which describes every information about the product. Best way to represent such info is no-sql json format. This will allow us to store any information about the product without changing the database schema.

#### Options
1. Store specs in a text field in the 'Product' table.
2. Store specs in a blob field in the 'Product' table.