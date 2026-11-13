"""Exercise the main farmer and admin flows, then leave the sample database clean."""

import os
import re
import sqlite3

from app import app
from database import DB_PATH, DEFAULT_FARMER_EMAIL, DEFAULT_FARMER_PASSWORD

client = app.test_client()


def token_from(response):
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match, response.get_data(as_text=True)[:500]
    return match.group(1)


def expect(path, status=200):
    response = client.get(path)
    assert response.status_code == status, (path, response.status_code)
    return response


for path in ["/", "/products", "/product/1", "/shops", "/about", "/contact", "/login", "/register", "/admin/login"]:
    expect(path)

assert expect("/missing-page", 404).status_code == 404
assert client.get("/cart").status_code == 302
assert client.get("/admin").status_code == 302
assert client.get("/orders").status_code == 302

products = expect("/products?q=urea&category=Nitrogen&sort=price_asc")
assert "Urea" in products.get_data(as_text=True)
shops = expect("/shops?q=Rampura")
assert "Krishi Seva Kendra" in shops.get_data(as_text=True)
assert "Annadata" not in shops.get_data(as_text=True)

login_page = expect("/login")
bad = client.post("/login", data={
    "email": DEFAULT_FARMER_EMAIL,
    "password": "wrong-password",
    "csrf_token": token_from(login_page),
    "next": "",
}, follow_redirects=True)
assert "Invalid email or password." in bad.get_data(as_text=True)

login_page = client.get("/login")
good = client.post("/login", data={
    "email": DEFAULT_FARMER_EMAIL,
    "password": DEFAULT_FARMER_PASSWORD,
    "csrf_token": token_from(login_page),
    "next": "/products",
}, follow_redirects=True)
assert "Welcome" in good.get_data(as_text=True)
assert "Urea" in good.get_data(as_text=True)

detail = client.get("/product/1")
added = client.post("/cart/add/1", data={"csrf_token": token_from(detail), "quantity": "2"}, follow_redirects=True)
assert "added to your cart" in added.get_data(as_text=True)
assert "532.00" in added.get_data(as_text=True)

cart = client.get("/cart")
cart_html = cart.get_data(as_text=True)
update_action = re.search(r'action="(/cart/update/\d+)"', cart_html).group(1)
remove_action = re.search(r'action="(/cart/remove/\d+)"', cart_html).group(1)
token = token_from(cart)
updated = client.post(update_action, data={"csrf_token": token, "quantity": "3"}, follow_redirects=True)
assert "798.00" in updated.get_data(as_text=True)

cart = client.get("/cart")
removed = client.post(remove_action, data={"csrf_token": token_from(cart)}, follow_redirects=True)
assert "empty" in removed.get_data(as_text=True).lower()

detail = client.get("/product/1")
client.post("/cart/add/1", data={"csrf_token": token_from(detail), "quantity": "1"}, follow_redirects=True)
cart = client.get("/cart")
order = client.post("/checkout", data={"csrf_token": token_from(cart)}, follow_redirects=True)
order_html = order.get_data(as_text=True)
assert "Order confirmed" in order_html
order_id = int(re.search(r"Order #(\d+)", order_html).group(1))

client.get("/logout", follow_redirects=True)  # GET should not log out
assert client.get("/orders").status_code == 200

logout_page = client.get("/orders")
client.post("/logout", data={"csrf_token": token_from(logout_page)}, follow_redirects=True)
assert client.get("/orders").status_code == 302

reg = client.get("/register")
rejected = client.post("/register", data={
    "csrf_token": token_from(reg),
    "name": "A",
    "email": "not-an-email",
    "mobile": "123",
    "password": "abc",
    "confirm_password": "xyz",
}, follow_redirects=True)
assert "valid email" in rejected.get_data(as_text=True)

contact = client.get("/contact")
sent = client.post("/contact", data={
    "csrf_token": token_from(contact),
    "name": "Test Farmer",
    "email": "test.farmer@example.com",
    "message": "Please confirm neem cake availability.",
}, follow_redirects=True)
assert "message has been sent" in sent.get_data(as_text=True)

admin_page = client.get("/admin/login")
admin = client.post("/admin/login", data={
    "csrf_token": token_from(admin_page),
    "username": "admin",
    "password": "Admin@123",
    "next": "",
}, follow_redirects=True)
assert "Registered farmers" in admin.get_data(as_text=True)
assert "Test Farmer" in client.get("/admin").get_data(as_text=True)

created = client.post("/admin/products", data={
    "csrf_token": token_from(client.get("/admin/products")),
    "name": "Test Mix",
    "category": "Micronutrient",
    "description": "Temporary product used to verify the admin form.",
    "usage": "Delete this sample after the automated check.",
    "price": "99",
    "stock": "4",
}, follow_redirects=True)
assert "Fertilizer added." in created.get_data(as_text=True)

with app.app_context():
    from app import get_db
    row = get_db().execute("SELECT fertilizer_id FROM fertilizers WHERE name = ?", ("Test Mix",)).fetchone()
    mix_id = row["fertilizer_id"]

edited = client.post(f"/admin/products/{mix_id}/edit", data={
    "csrf_token": token_from(client.get(f"/admin/products/{mix_id}/edit")),
    "name": "Test Mix",
    "category": "Micronutrient",
    "description": "Temporary product used to verify the admin form.",
    "usage": "Delete this sample after the automated check.",
    "price": "120",
    "stock": "6",
}, follow_redirects=True)
assert "Fertilizer updated." in edited.get_data(as_text=True)

stocked = client.post(f"/admin/products/{mix_id}/stock", data={
    "csrf_token": token_from(client.get("/admin/products")),
    "stock": "8",
}, follow_redirects=True)
assert "Stock updated." in stocked.get_data(as_text=True)

deleted = client.post(f"/admin/products/{mix_id}/delete", data={
    "csrf_token": token_from(client.get("/admin/products")),
}, follow_redirects=True)
assert "Fertilizer deleted." in deleted.get_data(as_text=True)

shop_page = client.get("/admin/shops")
new_shop = client.post("/admin/shops", data={
    "csrf_token": token_from(shop_page),
    "shop_name": "Temporary Krishi Point",
    "owner_name": "Test Owner",
    "address": "1 Test Lane, Anand",
    "village": "Testpur",
    "mobile": "9876500199",
    "fertilizer_ids": "1",
}, follow_redirects=True)
assert "Shop added." in new_shop.get_data(as_text=True)

status_page = client.get("/admin/orders")
changed = client.post(f"/admin/orders/{order_id}/status", data={
    "csrf_token": token_from(status_page),
    "order_status": "Confirmed",
}, follow_redirects=True)
assert "Confirmed" in changed.get_data(as_text=True)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
urea_stock = conn.execute("SELECT stock FROM fertilizers WHERE name = 'Urea'").fetchone()[0]
assert urea_stock == 199, urea_stock
conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
conn.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
conn.execute("UPDATE fertilizers SET stock = 200 WHERE name = 'Urea'")
conn.execute("DELETE FROM contact")
conn.execute("DELETE FROM shops WHERE shop_name = 'Temporary Krishi Point'")
conn.commit()
conn.close()

print("All major flows passed.")
