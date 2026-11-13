"""Smart Fertilizer Finder — Flask routes for farmers, carts, orders, and admin."""

import os
import re
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import initialize

initialize()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SMART_FERTILIZER_SECRET", "dev-change-this-smart-fertilizer-key"
)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
ORDER_STATUSES = [
    "Pending",
    "Confirmed",
    "Packed",
    "Out for Delivery",
    "Delivered",
    "Cancelled",
]
POPULAR_NAMES = ("Urea", "DAP", "NPK", "Organic Fertilizers")
MAX_LINE_QTY = 500
DUMMY_PASSWORD_HASH = generate_password_hash("not-a-real-password")


def get_db():
    """Reuse one SQLite connection for the current request."""
    if "db" not in g:
        from database import connect

        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def clean(value, max_len):
    """Collapse whitespace and limit length for single-line fields."""
    text = " ".join(str(value or "").split())
    return text[:max_len]


def clean_multiline(value, max_len):
    text = str(value or "").replace("\r\n", "\n").strip()
    return text[:max_len]


def like_param(term):
    """Escape LIKE wildcards so a search is literal."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def valid_password(password):
    if not isinstance(password, str) or not 6 <= len(password) <= 128:
        return False
    return any(ch.isalpha() for ch in password) and any(ch.isdigit() for ch in password)


def parse_quantity(value, stock):
    """Accept a whole number between 1 and the available stock."""
    try:
        qty = int(value)
    except (TypeError, ValueError):
        return None
    if qty < 1 or qty > min(int(stock), MAX_LINE_QTY):
        return None
    return qty


def parse_price(value):
    try:
        price = round(float(value), 2)
    except (TypeError, ValueError):
        return None
    if price <= 0 or price > 1_000_000:
        return None
    return price


def parse_stock(value):
    try:
        stock = int(value)
    except (TypeError, ValueError):
        return None
    if stock < 0 or stock > 1_000_000:
        return None
    return stock


def safe_redirect_target(target):
    """Allow only same-site relative paths."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    return target


def resolve_image(name):
    """Pick a stored photo, then a matching SVG, then the default artwork."""
    images = os.path.join(app.static_folder, "images")
    candidates = []
    if name:
        base = os.path.basename(str(name))
        stem, ext = os.path.splitext(base)
        candidates.append(base)
        if ext.lower() != ".svg":
            candidates.append(stem + ".svg")
    candidates.append("default.svg")
    for candidate in candidates:
        if candidate and os.path.isfile(os.path.join(images, candidate)):
            return candidate
    return "logo.svg"


@app.template_filter("media")
def media_filter(name):
    return url_for("static", filename="images/" + resolve_image(name))


@app.template_filter("inr")
def format_inr(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    return "₹{:,.2f}".format(amount)


def farmer_login_redirect(message):
    """Send a visitor to login and return them to a safe GET page afterwards."""
    if request.method == "GET":
        next_url = request.full_path[:-1] if request.full_path.endswith("?") else request.full_path
    else:
        next_url = None
        if request.referrer:
            parsed = urlparse(request.referrer)
            if parsed.netloc in ("", request.host) and parsed.path.startswith("/") and not parsed.path.startswith("//"):
                next_url = parsed.path
                if parsed.query:
                    next_url += "?" + parsed.query
        next_url = next_url or url_for("home")
    flash(message, "warning")
    return redirect(url_for("login", next=next_url))


def login_required(view):
    """Send anonymous visitors to the farmer login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id:
            user = get_db().execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if user is not None:
                return view(*args, **kwargs)
            session.pop("user_id", None)
            session.pop("user_name", None)
        return farmer_login_redirect("Please log in to continue.")

    return wrapped


def admin_required(view):
    """Block farmer sessions and anonymous visitors from admin pages."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in as an administrator.", "warning")
            return redirect(url_for("admin_login", next=request.path))
        admin = get_db().execute(
            "SELECT admin_id FROM admin WHERE admin_id = ?", (session["admin_id"],)
        ).fetchone()
        if admin is None:
            session.pop("admin_id", None)
            session.pop("admin_name", None)
            flash("Please log in as an administrator.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


@app.before_request
def csrf_protect():
    """Reject cross-site POSTs that do not carry the session token."""
    if request.method != "POST":
        return None
    token = request.form.get("csrf_token", "")
    saved = session.get("csrf", "")
    try:
        valid_csrf = bool(token) and bool(saved) and secrets.compare_digest(token, saved)
    except (TypeError, ValueError):
        valid_csrf = False
    if not valid_csrf:
        flash("Your form expired. Please try again.", "warning")
        referrer = request.referrer or ""
        parsed = urlparse(referrer)
        if referrer and parsed.netloc in ("", request.host):
            return redirect(referrer)
        return redirect(url_for("home"))
    return None


@app.after_request
def secure_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.path.startswith("/admin") or request.path in {"/cart", "/orders", "/login", "/register"}:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.context_processor
def inject_globals():
    def csrf_token():
        if not session.get("csrf"):
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    count = 0
    if session.get("user_id"):
        row = get_db().execute(
            "SELECT COALESCE(SUM(quantity), 0) AS total FROM cart WHERE user_id = ?",
            (session["user_id"],),
        ).fetchone()
        count = row["total"]
    return {
        "cart_count": count,
        "current_year": datetime.now().year,
        "csrf_token": csrf_token,
    }


def list_categories():
    rows = get_db().execute(
        "SELECT DISTINCT category FROM fertilizers ORDER BY category COLLATE NOCASE"
    ).fetchall()
    return [row["category"] for row in rows]


def search_products(keyword, category, sort):
    """Search, filter, and sort fertilizers. Sort values come from a fixed list."""
    sql = "SELECT * FROM fertilizers WHERE 1 = 1"
    params = []
    if keyword:
        like = like_param(keyword)
        sql += (
            " AND (name LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\' "
            "OR description LIKE ? ESCAPE '\\')"
        )
        params.extend([like, like, like])
    if category:
        sql += " AND category = ?"
        params.append(category)
    order_by = {
        "price_asc": "price ASC, name COLLATE NOCASE ASC",
        "price_desc": "price DESC, name COLLATE NOCASE ASC",
        "name": "name COLLATE NOCASE ASC",
    }.get(sort, "name COLLATE NOCASE ASC")
    sql += f" ORDER BY {order_by}"
    return [dict(row) for row in get_db().execute(sql, params)]


def popular_products():
    marks = ",".join("?" for _ in POPULAR_NAMES)
    rows = get_db().execute(
        f"SELECT * FROM fertilizers WHERE name IN ({marks})", POPULAR_NAMES
    ).fetchall()
    order = {name: index for index, name in enumerate(POPULAR_NAMES)}
    found = [dict(row) for row in rows]
    return sorted(found, key=lambda item: order.get(item["name"], 99))


def load_shops(keyword=None, limit=None):
    """Group each shop with the fertilizer names it stocks."""
    sql = """
        SELECT s.shop_id, s.shop_name, s.owner_name, s.address, s.village, s.mobile,
               f.name AS fertilizer_name
        FROM shops s
        LEFT JOIN shop_fertilizers sf ON sf.shop_id = s.shop_id
        LEFT JOIN fertilizers f ON f.fertilizer_id = sf.fertilizer_id
    """
    params = []
    if keyword:
        like = like_param(keyword)
        sql += (
            " WHERE (s.village LIKE ? ESCAPE '\\' OR s.address LIKE ? ESCAPE '\\' "
            "OR s.shop_name LIKE ? ESCAPE '\\' OR s.owner_name LIKE ? ESCAPE '\\')"
        )
        params.extend([like, like, like, like])
    sql += " ORDER BY s.shop_name COLLATE NOCASE, f.name COLLATE NOCASE"
    grouped = {}
    order = []
    for row in get_db().execute(sql, params):
        shop_id = row["shop_id"]
        if shop_id not in grouped:
            grouped[shop_id] = {
                "shop_id": shop_id,
                "shop_name": row["shop_name"],
                "owner_name": row["owner_name"],
                "address": row["address"],
                "village": row["village"],
                "mobile": row["mobile"],
                "fertilizers": [],
            }
            order.append(shop_id)
        if row["fertilizer_name"]:
            grouped[shop_id]["fertilizers"].append(row["fertilizer_name"])
    shops = [grouped[shop_id] for shop_id in order]
    if limit:
        return shops[:limit]
    return shops


def load_orders(user_id=None):
    """Return orders with line items. Pass a user id for a farmer's own history."""
    sql = """
        SELECT o.order_id, o.user_id, o.total_amount, o.order_date, o.order_status,
               u.name AS customer_name, u.email, u.mobile
        FROM orders o
        JOIN users u ON u.user_id = o.user_id
    """
    params = []
    if user_id is not None:
        sql += " WHERE o.user_id = ?"
        params.append(user_id)
    sql += " ORDER BY o.order_id DESC"
    orders = [dict(row) for row in get_db().execute(sql, params)]
    if not orders:
        return []
    ids = [order["order_id"] for order in orders]
    marks = ",".join("?" for _ in ids)
    item_rows = get_db().execute(
        f"""
        SELECT oi.order_id, oi.quantity, oi.price,
               COALESCE(f.name, 'Fertilizer') AS name
        FROM order_items oi
        LEFT JOIN fertilizers f ON f.fertilizer_id = oi.fertilizer_id
        WHERE oi.order_id IN ({marks})
        ORDER BY oi.item_id
        """,
        ids,
    )
    grouped = {order_id: [] for order_id in ids}
    for item in item_rows:
        grouped[item["order_id"]].append(dict(item))
    for order in orders:
        order["items"] = grouped[order["order_id"]]
    return orders


def site_stats():
    db = get_db()
    return {
        "farmers": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "fertilizers": db.execute("SELECT COUNT(*) FROM fertilizers").fetchone()[0],
        "shops": db.execute("SELECT COUNT(*) FROM shops").fetchone()[0],
        "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
    }


def save_uploaded_image(file_storage):
    """Store an admin image upload. Returns (filename or None, error or None)."""
    if file_storage is None or not file_storage.filename:
        return None, None
    original = secure_filename(file_storage.filename)
    if "." not in original:
        return None, "Upload a png, jpg, webp, or gif image."
    ext = original.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None, "Upload a png, jpg, webp, or gif image."
    filename = f"{secrets.token_hex(8)}.{ext}"
    folder = os.path.join(app.static_folder, "images")
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return filename, None


def parse_fertilizer_form(form):
    """Validate fertilizer fields from an admin form."""
    name = clean(form.get("name"), 80)
    category = clean(form.get("category"), 40)
    description = clean_multiline(form.get("description"), 2000)
    usage = clean_multiline(form.get("usage"), 2000)
    price = parse_price(form.get("price"))
    stock = parse_stock(form.get("stock"))
    errors = []
    if len(name) < 2:
        errors.append("Enter a fertilizer name.")
    if len(category) < 2:
        errors.append("Enter a category.")
    if len(description) < 10:
        errors.append("Enter a description of at least 10 characters.")
    if len(usage) < 10:
        errors.append("Enter usage information of at least 10 characters.")
    if price is None:
        errors.append("Enter a price greater than zero.")
    if stock is None:
        errors.append("Enter a stock quantity of zero or more.")
    if errors:
        return None, " ".join(errors)
    return {
        "name": name,
        "category": category,
        "description": description,
        "usage": usage,
        "price": price,
        "stock": stock,
    }, None


def parse_shop_form(form):
    shop_name = clean(form.get("shop_name"), 80)
    owner_name = clean(form.get("owner_name"), 80)
    address = clean(form.get("address"), 160)
    village = clean(form.get("village"), 80)
    mobile = clean(form.get("mobile"), 15)
    raw_ids = form.getlist("fertilizer_ids") if hasattr(form, "getlist") else []
    fertilizer_ids = []
    for value in raw_ids:
        if str(value).isdigit():
            fertilizer_ids.append(int(value))
    errors = []
    if len(shop_name) < 2:
        errors.append("Enter the shop name.")
    if len(owner_name) < 2:
        errors.append("Enter the owner name.")
    if len(address) < 5:
        errors.append("Enter the shop address.")
    if len(village) < 2:
        errors.append("Enter the village or town.")
    if not re.fullmatch(r"\d{10}", mobile):
        errors.append("Enter a 10-digit mobile number.")
    if errors:
        return None, " ".join(errors)
    return {
        "shop_name": shop_name,
        "owner_name": owner_name,
        "address": address,
        "village": village,
        "mobile": mobile,
        "fertilizer_ids": fertilizer_ids,
    }, None


def replace_shop_fertilizers(db, shop_id, fertilizer_ids):
    valid_rows = db.execute("SELECT fertilizer_id FROM fertilizers").fetchall()
    valid_ids = {row["fertilizer_id"] for row in valid_rows}
    db.execute("DELETE FROM shop_fertilizers WHERE shop_id = ?", (shop_id,))
    for fertilizer_id in dict.fromkeys(fertilizer_ids):
        if fertilizer_id in valid_ids:
            db.execute(
                "INSERT INTO shop_fertilizers (shop_id, fertilizer_id) VALUES (?, ?)",
                (shop_id, fertilizer_id),
            )


def render_admin_products(form, edit_product=None):
    products = [
        dict(row)
        for row in get_db().execute(
            "SELECT * FROM fertilizers ORDER BY name COLLATE NOCASE"
        )
    ]
    return render_template(
        "admin/products.html",
        products=products,
        categories=list_categories(),
        form=form,
        edit_product=edit_product,
    )


def render_admin_shops(form, edit_shop=None, selected_ids=None):
    db = get_db()
    fertilizers = [
        dict(row)
        for row in db.execute("SELECT fertilizer_id, name FROM fertilizers ORDER BY name COLLATE NOCASE")
    ]
    return render_template(
        "admin/shops.html",
        shops=load_shops(),
        fertilizers=fertilizers,
        form=form,
        edit_shop=edit_shop,
        selected_ids=selected_ids or [],
    )


@app.route("/")
def home():
    return render_template(
        "index.html",
        popular=popular_products(),
        shops=load_shops(limit=3),
        categories=list_categories(),
        stats=site_stats(),
    )


@app.route("/products")
def products():
    keyword = clean(request.args.get("q"), 80)
    category = clean(request.args.get("category"), 40)
    sort = request.args.get("sort", "name")
    if sort not in {"name", "price_asc", "price_desc"}:
        sort = "name"
    items = search_products(keyword, category, sort)
    return render_template(
        "products.html",
        products=items,
        categories=list_categories(),
        q=keyword,
        category=category,
        sort=sort,
    )


@app.route("/product/<int:fertilizer_id>")
def product_details(fertilizer_id):
    row = get_db().execute(
        "SELECT * FROM fertilizers WHERE fertilizer_id = ?", (fertilizer_id,)
    ).fetchone()
    if row is None:
        abort(404)
    product = dict(row)
    related = [
        dict(item)
        for item in get_db().execute(
            """
            SELECT * FROM fertilizers
            WHERE category = ? AND fertilizer_id != ?
            ORDER BY name COLLATE NOCASE
            LIMIT 3
            """,
            (product["category"], product["fertilizer_id"]),
        )
    ]
    return render_template("product_details.html", product=product, related=related)


@app.route("/shops")
def shops():
    keyword = clean(request.args.get("q"), 80)
    return render_template("shops.html", shops=load_shops(keyword), q=keyword)


@app.route("/about")
def about():
    return render_template("about.html", stats=site_stats())


@app.route("/contact", methods=["GET", "POST"])
def contact():
    errors = {}
    if request.method == "POST":
        name = clean(request.form.get("name"), 80)
        email = clean(request.form.get("email"), 120).lower()
        message = clean_multiline(request.form.get("message"), 2000)
        if len(name) < 2:
            errors["name"] = "Please enter your name."
        if not EMAIL_RE.match(email):
            errors["email"] = "Please enter a valid email address."
        if len(message) < 10:
            errors["message"] = "Please enter a message of at least 10 characters."
        if not errors:
            get_db().execute(
                """
                INSERT INTO contact (name, email, message, submitted_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, message, datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
            get_db().commit()
            flash("Thank you. Your message has been sent.", "success")
            return redirect(url_for("contact"))
    form = request.form if request.method == "POST" else {}
    return render_template("contact.html", errors=errors, form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("home"))
    errors = {}
    if request.method == "POST":
        name = clean(request.form.get("name"), 80)
        email = clean(request.form.get("email"), 120).lower()
        mobile = clean(request.form.get("mobile"), 15)
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""
        if len(name) < 2:
            errors["name"] = "Please enter your full name."
        if not EMAIL_RE.match(email):
            errors["email"] = "Please enter a valid email address."
        if not re.fullmatch(r"\d{10}", mobile):
            errors["mobile"] = "Please enter a 10-digit mobile number."
        if not valid_password(password):
            errors["password"] = "Use at least 6 characters with one letter and one number."
        if password != confirm:
            errors["confirm_password"] = "Passwords do not match."
        if not errors:
            db = get_db()
            taken = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
            if taken:
                errors["email"] = "An account with this email already exists."
            else:
                try:
                    db.execute(
                        """
                        INSERT INTO users (name, email, mobile, password)
                        VALUES (?, ?, ?, ?)
                        """,
                        (name, email, mobile, generate_password_hash(password)),
                    )
                    db.commit()
                except sqlite3.IntegrityError:
                    db.rollback()
                    errors["email"] = "An account with this email already exists."
                else:
                    flash("Registration successful. Please log in.", "success")
                    return redirect(url_for("login"))
    form = request.form if request.method == "POST" else {}
    return render_template("register.html", errors=errors, form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("home"))
    next_url = safe_redirect_target(request.values.get("next"))
    if request.method == "POST":
        email = clean(request.form.get("email"), 120).lower()
        password = request.form.get("password") or ""
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        password_hash = user["password"] if user else DUMMY_PASSWORD_HASH
        if user is None or not check_password_hash(password_hash, password):
            flash("Invalid email or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["csrf"] = secrets.token_hex(16)
            flash(f"Welcome, {user['name']}.", "success")
            return redirect(next_url or url_for("home"))
    return render_template("login.html", next_url=next_url or "", form=request.form if request.method == "POST" else {})


@app.route("/logout", methods=["POST"])
def logout():
    was_logged_in = session.pop("user_id", None)
    session.pop("user_name", None)
    session["csrf"] = secrets.token_hex(16)
    if was_logged_in:
        flash("You have logged out.", "success")
    return redirect(url_for("home"))


@app.route("/cart/add/<int:fertilizer_id>", methods=["POST"])
def add_to_cart(fertilizer_id):
    """Add a fertilizer to the logged-in farmer's cart, or increase its quantity."""
    if not session.get("user_id"):
        flash("Please log in to add items to your cart.", "warning")
        return redirect(url_for("login", next=url_for("product_details", fertilizer_id=fertilizer_id)))
    user = get_db().execute(
        "SELECT user_id FROM users WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    if user is None:
        session.pop("user_id", None)
        session.pop("user_name", None)
        flash("Please log in to add items to your cart.", "warning")
        return redirect(url_for("login", next=url_for("product_details", fertilizer_id=fertilizer_id)))
    db = get_db()
    product = db.execute(
        "SELECT fertilizer_id, name, stock FROM fertilizers WHERE fertilizer_id = ?",
        (fertilizer_id,),
    ).fetchone()
    if product is None:
        abort(404)
    qty = parse_quantity(request.form.get("quantity", 1), product["stock"])
    destination = url_for("product_details", fertilizer_id=fertilizer_id)
    if product["stock"] < 1:
        flash(f"{product['name']} is out of stock.", "warning")
        return redirect(destination)
    if qty is None:
        flash(f"Choose a quantity from 1 to {min(product['stock'], MAX_LINE_QTY)}.", "danger")
        return redirect(destination)
    existing = db.execute(
        "SELECT cart_id, quantity FROM cart WHERE user_id = ? AND fertilizer_id = ?",
        (session["user_id"], fertilizer_id),
    ).fetchone()
    if existing:
        new_qty = existing["quantity"] + qty
        if new_qty > product["stock"] or new_qty > MAX_LINE_QTY:
            flash(f"Only {product['stock']} units of {product['name']} are available.", "warning")
            return redirect(url_for("cart"))
        db.execute(
            "UPDATE cart SET quantity = ? WHERE cart_id = ? AND user_id = ?",
            (new_qty, existing["cart_id"], session["user_id"]),
        )
    else:
        db.execute(
            "INSERT INTO cart (user_id, fertilizer_id, quantity) VALUES (?, ?, ?)",
            (session["user_id"], fertilizer_id, qty),
        )
    db.commit()
    flash(f"{product['name']} added to your cart.", "success")
    return redirect(url_for("cart"))


@app.route("/cart")
@login_required
def cart():
    rows = get_db().execute(
        """
        SELECT c.cart_id, c.quantity, f.fertilizer_id, f.name, f.price, f.stock, f.image, f.category
        FROM cart c
        JOIN fertilizers f ON f.fertilizer_id = c.fertilizer_id
        WHERE c.user_id = ?
        ORDER BY c.cart_id DESC
        """,
        (session["user_id"],),
    ).fetchall()
    items = []
    total = 0
    for row in rows:
        item = dict(row)
        item["line_total"] = round(item["price"] * item["quantity"], 2)
        total += item["line_total"]
        items.append(item)
    return render_template("cart.html", items=items, total=round(total, 2))


@app.route("/cart/update/<int:cart_id>", methods=["POST"])
@login_required
def update_cart(cart_id):
    db = get_db()
    row = db.execute(
        """
        SELECT c.cart_id, f.stock, f.name
        FROM cart c
        JOIN fertilizers f ON f.fertilizer_id = c.fertilizer_id
        WHERE c.cart_id = ? AND c.user_id = ?
        """,
        (cart_id, session["user_id"]),
    ).fetchone()
    if row is None:
        flash("That cart item is no longer available.", "danger")
        return redirect(url_for("cart"))
    qty = parse_quantity(request.form.get("quantity"), row["stock"])
    if qty is None:
        flash(f"Enter a valid quantity for {row['name']}.", "danger")
        return redirect(url_for("cart"))
    db.execute(
        "UPDATE cart SET quantity = ? WHERE cart_id = ? AND user_id = ?",
        (qty, cart_id, session["user_id"]),
    )
    db.commit()
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:cart_id>", methods=["POST"])
@login_required
def remove_from_cart(cart_id):
    get_db().execute(
        "DELETE FROM cart WHERE cart_id = ? AND user_id = ?",
        (cart_id, session["user_id"]),
    )
    get_db().commit()
    flash("Item removed from your cart.", "success")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    """Place an order only when every cart line still has enough stock."""
    db = get_db()
    items = db.execute(
        """
        SELECT c.fertilizer_id, c.quantity, f.price, f.stock, f.name
        FROM cart c
        JOIN fertilizers f ON f.fertilizer_id = c.fertilizer_id
        WHERE c.user_id = ?
        """,
        (session["user_id"],),
    ).fetchall()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))
    for item in items:
        if item["quantity"] < 1 or item["quantity"] > item["stock"]:
            flash(f"Not enough stock for {item['name']}. Update the quantity and try again.", "danger")
            return redirect(url_for("cart"))
    try:
        for item in items:
            cursor = db.execute(
                """
                UPDATE fertilizers
                SET stock = stock - ?
                WHERE fertilizer_id = ? AND stock >= ?
                """,
                (item["quantity"], item["fertilizer_id"], item["quantity"]),
            )
            if cursor.rowcount != 1:
                raise ValueError(item["name"])
        total = round(sum(item["price"] * item["quantity"] for item in items), 2)
        cursor = db.execute(
            """
            INSERT INTO orders (user_id, total_amount, order_date, order_status)
            VALUES (?, ?, ?, ?)
            """,
            (
                session["user_id"],
                total,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Pending",
            ),
        )
        order_id = cursor.lastrowid
        for item in items:
            db.execute(
                """
                INSERT INTO order_items (order_id, fertilizer_id, quantity, price)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, item["fertilizer_id"], item["quantity"], item["price"]),
            )
        db.execute("DELETE FROM cart WHERE user_id = ?", (session["user_id"],))
        db.commit()
    except ValueError as exc:
        db.rollback()
        flash(f"Not enough stock for {exc}. Your order was not placed.", "danger")
        return redirect(url_for("cart"))
    except sqlite3.Error:
        db.rollback()
        flash("Could not place the order. Please try again.", "danger")
        return redirect(url_for("cart"))
    flash(f"Order #{order_id} placed successfully.", "success")
    return redirect(url_for("orders", placed=order_id))


@app.route("/orders")
@login_required
def orders():
    placed = request.args.get("placed", type=int)
    history = load_orders(session["user_id"])
    placed_order = next((order for order in history if order["order_id"] == placed), None)
    return render_template("orders.html", orders=history, placed_order=placed_order)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    next_url = safe_redirect_target(request.values.get("next"))
    if next_url and not next_url.startswith("/admin"):
        next_url = None
    if request.method == "POST":
        username = clean(request.form.get("username"), 40).lower()
        password = request.form.get("password") or ""
        admin = get_db().execute(
            "SELECT * FROM admin WHERE username = ?", (username,)
        ).fetchone()
        password_hash = admin["password"] if admin else DUMMY_PASSWORD_HASH
        if admin is None or not check_password_hash(password_hash, password):
            flash("Invalid admin username or password.", "danger")
        else:
            session.clear()
            session["admin_id"] = admin["admin_id"]
            session["admin_name"] = admin["username"]
            session["csrf"] = secrets.token_hex(16)
            flash("Admin login successful.", "success")
            return redirect(next_url or url_for("admin_dashboard"))
    return render_template(
        "admin/login.html",
        next_url=next_url or "",
        form=request.form if request.method == "POST" else {},
    )


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session["csrf"] = secrets.token_hex(16)
    flash("Admin session closed.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    customers = [
        dict(row)
        for row in db.execute(
            """
            SELECT u.user_id, u.name, u.email, u.mobile, COUNT(o.order_id) AS order_count
            FROM users u
            LEFT JOIN orders o ON o.user_id = u.user_id
            GROUP BY u.user_id
            ORDER BY u.name COLLATE NOCASE
            """
        )
    ]
    messages = [
        dict(row)
        for row in db.execute(
            "SELECT * FROM contact ORDER BY contact_id DESC LIMIT 8"
        )
    ]
    low_stock = [
        dict(row)
        for row in db.execute(
            "SELECT * FROM fertilizers WHERE stock < 15 ORDER BY stock ASC, name COLLATE NOCASE"
        )
    ]
    return render_template(
        "admin/dashboard.html",
        stats=site_stats(),
        customers=customers,
        messages=messages,
        low_stock=low_stock,
        recent_orders=load_orders()[:5],
    )


@app.route("/admin/products", methods=["GET", "POST"])
@admin_required
def admin_products():
    if request.method == "POST":
        data, error = parse_fertilizer_form(request.form)
        image_name, image_error = save_uploaded_image(request.files.get("image"))
        if error or image_error:
            flash(error or image_error, "danger")
            return render_admin_products(request.form)
        get_db().execute(
            """
            INSERT INTO fertilizers (name, category, description, usage, price, stock, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data["category"],
                data["description"],
                data["usage"],
                data["price"],
                data["stock"],
                image_name or "default.svg",
            ),
        )
        get_db().commit()
        flash("Fertilizer added.", "success")
        return redirect(url_for("admin_products"))
    return render_admin_products({})


@app.route("/admin/products/<int:fertilizer_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_product(fertilizer_id):
    row = get_db().execute(
        "SELECT * FROM fertilizers WHERE fertilizer_id = ?", (fertilizer_id,)
    ).fetchone()
    if row is None:
        flash("Fertilizer not found.", "danger")
        return redirect(url_for("admin_products"))
    product = dict(row)
    if request.method == "POST":
        data, error = parse_fertilizer_form(request.form)
        image_name, image_error = save_uploaded_image(request.files.get("image"))
        if error or image_error:
            flash(error or image_error, "danger")
            return render_admin_products(request.form, product)
        get_db().execute(
            """
            UPDATE fertilizers
            SET name = ?, category = ?, description = ?, usage = ?, price = ?, stock = ?, image = ?
            WHERE fertilizer_id = ?
            """,
            (
                data["name"],
                data["category"],
                data["description"],
                data["usage"],
                data["price"],
                data["stock"],
                image_name or product["image"],
                fertilizer_id,
            ),
        )
        get_db().commit()
        flash("Fertilizer updated.", "success")
        return redirect(url_for("admin_products"))
    return render_admin_products(product, product)


@app.route("/admin/products/<int:fertilizer_id>/stock", methods=["POST"])
@admin_required
def admin_update_stock(fertilizer_id):
    stock = parse_stock(request.form.get("stock"))
    if stock is None:
        flash("Enter a valid stock number.", "danger")
        return redirect(url_for("admin_products"))
    cursor = get_db().execute(
        "UPDATE fertilizers SET stock = ? WHERE fertilizer_id = ?",
        (stock, fertilizer_id),
    )
    if cursor.rowcount != 1:
        get_db().rollback()
        flash("Fertilizer not found.", "danger")
    else:
        get_db().commit()
        flash("Stock updated.", "success")
    return redirect(url_for("admin_products"))


@app.route("/admin/products/<int:fertilizer_id>/delete", methods=["POST"])
@admin_required
def admin_delete_product(fertilizer_id):
    try:
        cursor = get_db().execute(
            "DELETE FROM fertilizers WHERE fertilizer_id = ?", (fertilizer_id,)
        )
        if cursor.rowcount != 1:
            flash("Fertilizer not found.", "danger")
        else:
            get_db().commit()
            flash("Fertilizer deleted.", "success")
    except sqlite3.IntegrityError:
        get_db().rollback()
        flash(
            "This fertilizer is already part of an order, so it cannot be deleted. Set its stock to zero instead.",
            "warning",
        )
    return redirect(url_for("admin_products"))


@app.route("/admin/shops", methods=["GET", "POST"])
@admin_required
def admin_shops():
    if request.method == "POST":
        data, error = parse_shop_form(request.form)
        if error:
            flash(error, "danger")
            selected = [int(value) for value in request.form.getlist("fertilizer_ids") if value.isdigit()]
            return render_admin_shops(request.form, selected_ids=selected)
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO shops (shop_name, owner_name, address, village, mobile)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["shop_name"],
                data["owner_name"],
                data["address"],
                data["village"],
                data["mobile"],
            ),
        )
        replace_shop_fertilizers(db, cursor.lastrowid, data["fertilizer_ids"])
        db.commit()
        flash("Shop added.", "success")
        return redirect(url_for("admin_shops"))
    return render_admin_shops({})


@app.route("/admin/shops/<int:shop_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_shop(shop_id):
    row = get_db().execute("SELECT * FROM shops WHERE shop_id = ?", (shop_id,)).fetchone()
    if row is None:
        flash("Shop not found.", "danger")
        return redirect(url_for("admin_shops"))
    shop = dict(row)
    current_ids = [
        item["fertilizer_id"]
        for item in get_db().execute(
            "SELECT fertilizer_id FROM shop_fertilizers WHERE shop_id = ?", (shop_id,)
        )
    ]
    if request.method == "POST":
        data, error = parse_shop_form(request.form)
        if error:
            flash(error, "danger")
            selected = [int(value) for value in request.form.getlist("fertilizer_ids") if value.isdigit()]
            return render_admin_shops(request.form, shop, selected)
        db = get_db()
        db.execute(
            """
            UPDATE shops
            SET shop_name = ?, owner_name = ?, address = ?, village = ?, mobile = ?
            WHERE shop_id = ?
            """,
            (
                data["shop_name"],
                data["owner_name"],
                data["address"],
                data["village"],
                data["mobile"],
                shop_id,
            ),
        )
        replace_shop_fertilizers(db, shop_id, data["fertilizer_ids"])
        db.commit()
        flash("Shop updated.", "success")
        return redirect(url_for("admin_shops"))
    return render_admin_shops(shop, shop, current_ids)


@app.route("/admin/shops/<int:shop_id>/delete", methods=["POST"])
@admin_required
def admin_delete_shop(shop_id):
    cursor = get_db().execute("DELETE FROM shops WHERE shop_id = ?", (shop_id,))
    if cursor.rowcount != 1:
        flash("Shop not found.", "danger")
    else:
        get_db().commit()
        flash("Shop deleted.", "success")
    return redirect(url_for("admin_shops"))


@app.route("/admin/orders")
@admin_required
def admin_orders():
    return render_template(
        "admin/orders.html",
        orders=load_orders(),
        statuses=ORDER_STATUSES,
    )


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_order_status(order_id):
    """Change an order status and return stock when an order is cancelled."""
    new_status = request.form.get("order_status", "")
    if new_status not in ORDER_STATUSES:
        flash("Choose a valid order status.", "danger")
        return redirect(url_for("admin_orders"))
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    if order is None:
        flash("Order not found.", "danger")
        return redirect(url_for("admin_orders"))
    old_status = order["order_status"]
    if old_status == new_status:
        flash("Order status is already set.", "info")
        return redirect(url_for("admin_orders"))
    items = db.execute(
        "SELECT fertilizer_id, quantity FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    try:
        if new_status == "Cancelled" and old_status != "Cancelled":
            for item in items:
                db.execute(
                    "UPDATE fertilizers SET stock = stock + ? WHERE fertilizer_id = ?",
                    (item["quantity"], item["fertilizer_id"]),
                )
        elif old_status == "Cancelled" and new_status != "Cancelled":
            for item in items:
                cursor = db.execute(
                    """
                    UPDATE fertilizers
                    SET stock = stock - ?
                    WHERE fertilizer_id = ? AND stock >= ?
                    """,
                    (item["quantity"], item["fertilizer_id"], item["quantity"]),
                )
                if cursor.rowcount != 1:
                    raise ValueError("stock")
        db.execute(
            "UPDATE orders SET order_status = ? WHERE order_id = ?",
            (new_status, order_id),
        )
        db.commit()
    except ValueError:
        db.rollback()
        flash("Not enough stock to reopen this order.", "danger")
        return redirect(url_for("admin_orders"))
    except sqlite3.Error:
        db.rollback()
        flash("Could not update the order.", "danger")
        return redirect(url_for("admin_orders"))
    flash(f"Order #{order_id} marked as {new_status}.", "success")
    return redirect(url_for("admin_orders"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(_error):
    flash("The image must be smaller than 2 MB.", "danger")
    return redirect(url_for("admin_products"))


@app.errorhandler(500)
def server_error(_error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
