### This file discusses backend routes and database schemas

## Backend Routes

1. **/user** : contains methods for login, logout, editing profile, etc. -- login allowed with email and password, or phone and password.
2. **/product** : contains methods for posting/removing product, retrieving information, checking stock, etc.
3. **/cart** : viewing items, adding items, checkout, removing items, etc.
4. **/orders** : view previous / current orders, track current orders, etc
5. **/search** : search for products


## Database Schemas

#### user
* id: int Primary Key
* name: varchar
* email: varchar Unique
* password: text
* phone: varchar Unique
* address: list[text]
* is_admin: boolean default = false
* created_at: timestamp default = now()

#### product
* id: int Primary Key
* name: varchar
* description: text
* price: float or decimal(10,2)
* stock: int
* image: blob
* brand: varchar
* created_at: timestamp default = now()

#### categories
* id: int Primary Key
* name: varchar
* parent_category: int Foreign Key (self)

removed <!-- * category: list[category_id]: Foreign Keys --> from product table to allow multiple categories per product

#### product_categories
* id: int Primary Key // not required if using product_id and category_id as composite key
* product_id: int Foreign Key (product)
* category_id: int Foreign Key (categories)


#### cart
<!-- * id: int Primary Key // not required if using user_id as FK as one user may use only one cart -->
* user_id: int Foreign Key (user) and Primary Key
* product_id: int Foreign Key (product)
* quantity: int

#### orders
* id: int Primary Key
* user_id: int Foreign Key (user)
* total_amount: float or decimal(10,2)
* status: varchar (e.g., 'pending', 'shipped', 'delivered', 'cancelled')
* created_at: timestamp default = now()

#### order_items
* id: int Primary Key // not required if using order_id and product_id as composite key
* order_id: int Foreign Key (orders)
* product_id: int Foreign Key (product)
* quantity: int
* price: float or decimal(10,2) // price at the time of order

#### reviews
* id: int Primary Key
* product_id: int Foreign Key (product)
* user_id: int Foreign Key (user)
* rating: int (1-5)
* description: text
* created_at: timestamp default = now()