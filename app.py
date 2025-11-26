import os
from flask import Flask, render_template, redirect, url_for, flash, request, session
from dotenv import load_dotenv
from models import db, Item, Admin
from markupsafe import Markup, escape

load_dotenv()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in as admin.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

#===============================
#### Create table function
#===============================
def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s is None:
            return ''
        return Markup('<br>'.join(escape(s).splitlines()))

    # ============================
    # Admin Authentication
    # ============================

    @app.route("/admin/register", methods=["GET", "POST"])
    def admin_register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            if not username or not password:
                flash("Username and password required.", "error")
                return render_template("admin_register.html")

            if Admin.query.filter_by(username=username).first():
                flash("Username already taken.", "error")
                return render_template("admin_register.html")

            admin = Admin(username=username)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            flash("Admin registered successfully.", "success")
            return redirect(url_for("admin_login"))
        return render_template("admin_register.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            admin = Admin.query.filter_by(username=username).first()
            if not admin or not admin.check_password(password):
                flash("Invalid username or password.", "error")
                return render_template("admin_login.html")

            session["admin_id"] = admin.id
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))

        return render_template("admin_login.html")

    @app.route("/admin/logout")
    def logout():
        session.pop("admin_id", None)
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    # ============================
    # Public Views
    # ============================

    @app.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
        per_page = 6
        items = Item.query.order_by(Item.created_at.desc()).paginate(page=page, per_page=per_page)
        return render_template('list.html', items=items)

    @app.route('/item/<int:item_id>')
    def detail(item_id):
        item = Item.query.get_or_404(item_id)
        return render_template('detail.html', item=item)

    # ============================
    # Admin-Protected Item Routes
    # ============================

    @app.route('/create', methods=['GET', 'POST'])
    @login_required
    def create():
        if request.method == 'POST':
            title = (request.form.get('title') or '').strip()
            description = (request.form.get('description') or '').strip() or None

            if not title:
                flash('Title is required.', 'error')
                return render_template('create.html', title=title, description=description)

            item = Item(title=title, description=description)
            db.session.add(item)
            db.session.commit()

            flash('Item created successfully.', 'success')
            return redirect(url_for('index'))

        return render_template('create.html', title='', description='')

    @app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
    @login_required
    def edit(item_id):
        item = Item.query.get_or_404(item_id)
        
        if request.method == 'POST':
            title = (request.form.get('title') or '').strip()
            description = (request.form.get('description') or '').strip() or None

            if not title:
                flash('Title is required.', 'error')
                return render_template('edit.html', item=item, title=title, description=description)

            item.title = title
            item.description = description
            db.session.commit()
            
            flash('Item updated.', 'success')
            return redirect(url_for('detail', item_id=item.id))

        return render_template('edit.html', item=item, title=item.title, description=item.description or '')

    @app.route('/delete/<int:item_id>', methods=['POST'])
    @login_required
    def delete(item_id):
        item = Item.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted.', 'info')
        return redirect(url_for('index'))

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    return app

if __name__ == '__main__':
    create_app().run(debug=True)
