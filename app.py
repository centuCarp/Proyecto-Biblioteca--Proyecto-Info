from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysql import MySQL

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones' # Necesario para Flask Sessions

# Configuración de la Base de Datos MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'       # Cambiá por tu usuario de MySQL
app.config['MYSQL_PASSWORD'] = ''   # Cambiá por tu contraseña de MySQL
app.config['MYSQL_DB'] = 'biblioteca'  # Nombre de tu base de datos

conexion = MySQL(app)

# Ruta de Login (Página principal)
@app.route('/')
def login():
    return render_template('index.html')

# Ruta del Dashboard / Inicio
@app.route('/inicio')
def inicio():
    return render_template('paginas/inicio.html')

# Ruta de Préstamos
@app.route('/prestamos')
def prestamos():
    return render_template('paginas/prestamo.html')

if __name__ == '__main__':
    app.run(debug=True)