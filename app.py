from flask import Flask, render_template
from config import Config
from models import db, login_manager
from routes.auth import auth
from routes.payments import payments
from routes.invoices import invoices
from routes.ice import ice
from routes.catalog import catalog
from routes.annexes import annexes
from flask_login import login_required, current_user

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    db.init_app(app)
    login_manager.init_app(app)
    
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(payments, url_prefix='/payments')
    app.register_blueprint(invoices, url_prefix='/invoices')
    app.register_blueprint(ice, url_prefix='/ice')
    app.register_blueprint(catalog, url_prefix='/catalog')
    app.register_blueprint(annexes, url_prefix='/annexes')
    
    with app.app_context():
        db.create_all()
    
    return app

app = create_app()

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    from models.user import Factura
    total_facturas = Factura.query.filter_by(usuario_id=current_user.id).count()
    return render_template('dashboard.html', total_facturas=total_facturas)

@app.route('/bienvenido')
def bienvenido():
    return render_template('bienvenido.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)