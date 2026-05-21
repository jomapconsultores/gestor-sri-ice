from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.user import Usuario
from models import db
from datetime import datetime, timedelta

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.check_password(password):
            login_user(usuario, remember=remember)
            next_page = request.args.get('next')
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos.', 'danger')
    
    return render_template('login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        nombre = request.form.get('nombre')
        empresa = request.form.get('empresa', '')
        ruc = request.form.get('ruc', '')
        password = request.form.get('password')
        confirmar = request.form.get('confirmar')
        
        if password != confirmar:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html')
        
        if Usuario.query.filter_by(email=email).first():
            flash('Este email ya está registrado.', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('register.html')
        
        usuario = Usuario(
            email=email,
            nombre=nombre,
            empresa=empresa,
            ruc=ruc
        )
        usuario.set_password(password)
        
        db.session.add(usuario)
        db.session.commit()
        
        flash('¡Registro exitoso! Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login'))