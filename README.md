# Smart Fertilizer Finder

Smart Fertilizer Finder is an online fertilizer availability and purchasing system for farmers. A farmer can search fertilizers, compare pack prices, check stock, find a nearby shop, and place an order. An administrator manages the catalog, shops, stock, and order status.

Passwords are stored with Werkzeug’s salted hash. Pages that change data use a session token, and database lookups use parameterised queries.

## Technologies used

- Frontend: HTML5, CSS3, JavaScript, Bootstrap 5
- Backend: Python, Flask
- Database: SQLite

## Project folder structure

```text
├── app.py
├── database.py
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── products.html
│   ├── product_details.html
│   ├── shops.html
│   ├── login.html
│   ├── register.html
│   ├── cart.html
│   ├── orders.html
│   ├── about.html
│   ├── contact.html
│   └── admin/
│       ├── login.html
│       ├── dashboard.html
│       ├── products.html
│       ├── shops.html
│       └── orders.html
├── static/
│   ├── css/style.css
│   ├── js/script.js
│   └── images/
└── instance/
    └── fertilizer.db
```

The database also includes a `usage` column on fertilizers and a `shop_fertilizers` table so each shop can list the products it stocks. Contact messages store a submission time.

## Installation steps

1. Open a terminal in this project folder.
2. Create and activate a virtual environment:

```text
python -m venv venv
venv\Scripts\activate
```

3. Install the dependencies:

```text
pip install -r requirements.txt
```

## How to initialize the database

Run:

```text
python database.py
```

This creates `instance/fertilizer.db`, the tables, an administrator, a demo farmer, eight fertilizers, and six shops. Starting the website also initializes the database when the file is missing. To load the sample records again, stop the app, delete `instance/fertilizer.db`, and run `python database.py`.

## How to run the application

```text
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

A demo farmer account is included:

- Email: `farmer@example.com`
- Password: `Farmer@123`

Register a new farmer from the Register page if you want a separate account. Use at least 6 characters with one letter and one number, and a 10-digit mobile number.

## Admin login instructions

Open [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login), or use the Admin login link in the footer.

- Username: `admin`
- Password: `Admin@123`

From the dashboard the administrator can see registered farmers, add and edit fertilizers, update stock, add and edit shops, read contact messages, and change order status. Cancelling an order returns its quantity to stock. Admin pages redirect to the admin login when nobody is signed in as an administrator.

Change `DEFAULT_ADMIN_PASSWORD` in `database.py` and recreate the database if you want a different admin password. For a public server, set the `SMART_FERTILIZER_SECRET` environment variable before starting the app.
