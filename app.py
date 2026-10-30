from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones' # Necesario para Flask Sessions

# Configuración de la Base de Datos MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'       # Cambiá por tu usuario de MySQL
app.config['MYSQL_PASSWORD'] = ''   # Cambiá por tu contraseña de MySQL
app.config['MYSQL_DB'] = 'Biblioteca'  # Nombre de tu base de datos

mysql = MySQL(app)

@app.route('/logout')
def logout():
    # Limpiamos todas las variables almacenadas en la sesión de Flask
    session.clear()
    # Redirigimos al usuario de vuelta al login principal
    return redirect(url_for('login'))
    
# Ruta de Login (Página principal)
@app.route('/', methods=['GET', 'POST'])
def login():
    # Verificamos si el usuario envió el formulario mediante el método POST
    if request.method == 'POST':
        
        # Capturamos los valores ingresados en los inputs del formulario HTML
        email = request.form['email']
        password = request.form['password']
        
        # Abrimos un cursor para ejecutar consultas SQL en la base de datos
        cursor = mysql.connection.cursor()
        
        # Ejecutamos una consulta segura utilizando %s para evitar inyecciones SQL
        cursor.execute("SELECT * FROM Usuarios WHERE Email = %s AND Contraseña = %s", (email, password))
        
        
        # Obtenemos un único registro (el primer usuario que coincida)
        user = cursor.fetchone()
        
        # Cerramos el cursor para liberar memoria de la base de datos
        cursor.close()
        
        # Validamos si la consulta encontró un usuario existente
        if user:
            # Creamos la sesión indicando que el usuario inició sesión correctamente
            session['loggedin'] = True
            session['id'] = user[0]           # Guardamos el ID del usuario (columna 0)
            session['name'] = user[1]         # Guardamos el Nombre Completo (columna 1)
            
            # Extraemos los permisos de rol de las columnas booleanas de la BD
            es_profesor = user[5]             # Columna esProfesor
            es_bibliotecario = user[6]        # Columna esBibliotecario
            
            
            # Asignamos un texto de rol legible según los permisos de la base de datos
            if es_bibliotecario:
                session['role'] = 'Bibliotecario/a'
            elif es_profesor:
                session['role'] = 'Profesor/a'
            else:
                session['role'] = 'Estudiante'
                
            # Redirigimos al usuario autenticado hacia la vista de inicio
            return redirect(url_for('inicio'))
        else:
            # Si el usuario no existe o la contraseña es incorrecta, definimos un mensaje de error
            error = "Correo o contraseña incorrectos."
            return render_template('index.html', error=error)
            
    # Si la petición es GET (recién entra a la página), simplemente renderizamos el index.html del login
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        dni = request.form['dni']
        email = request.form['email']
        password = request.form['password']
        tipo_usuario = request.form['tipo_usuario']
        
        # Definimos los valores booleanos según el rol seleccionado
        es_bibliotecario = True if tipo_usuario == 'bibliotecario' else False
        es_profesor = True if tipo_usuario == 'profesor' else False
        
        cursor = mysql.connection.cursor()
        
        # Verificamos si el correo o DNI ya existen
        cursor.execute("SELECT * FROM Usuarios WHERE Email = %s OR DNI = %s", (email, dni))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            return render_template('registro.html', error="El correo o DNI ya se encuentran registrados.")
        
        # Insertamos el nuevo usuario en la base de datos
        cursor.execute(
            "INSERT INTO Usuarios (Nombre_Completo, DNI, Email, Contraseña, esProfesor, esBibliotecario) VALUES (%s, %s, %s, %s, %s, %s)",
            (nombre, dni, email, password, es_profesor, es_bibliotecario)
        )
        mysql.connection.commit()
        cursor.close()
        
        # Redirigimos al login una vez creado exitosamente
        return redirect(url_for('login'))
        
    return render_template('registro.html')

# Ruta del Dashboard / Inicio
@app.route('/inicio')
def inicio():
    # Verificamos que el usuario haya iniciado sesión antes de dejarlo entrar al inicio
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    # Creamos el cursor para hacer las consultas a la base de datos
    cursor = mysql.connection.cursor()

    total_prestamos = 0
    # Ejecutamos las consultas SQL de conteo (COUNT) para los préstamos y los libros
    cursor.execute("SELECT COUNT(*) FROM Prestamos_Libros")
    total_prestamos += cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Prestamos_Carros")
    total_prestamos += cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Prestamos_Computadoras")
    total_prestamos += cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Prestamos_Elementos")
    total_prestamos += cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(E.ID) FROM Ejemplares E INNER JOIN Prestamos_Libros PL ON E.ID = PL.ID_Ejemplar WHERE E.ID NOT IN (SELECT ID_Ejemplar FROM Prestamos_Libros WHERE Fecha_Devolucion IS NULL)")
    libros_disponibles = cursor.fetchone()[0]
    
    # Cerramos el cursor de la base de datos
    cursor.close()

    # Renderizamos la plantilla inicio.html enviándole las variables con las métricas reales
    return render_template('inicio.html', 
                           total_prestamos=total_prestamos, 
                           libros_disponibles=libros_disponibles)



@app.route('/inicio#registrar_prestamo', methods=['POST'])
def registrar_prestamo():
    # Verificamos que el usuario tenga sesión activa
    if not session.get('loggedin'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # Capturamos los datos enviados desde el formulario modal de inicio.html
        nombre_solicitante = request.form['nombreSolicitante']
        tipo_prestamo = request.form['tipoPrestamo']
        item_title = request.form['itemTitle']
        fecha_limite = request.form['fechaLimite']
        
        cursor = mysql.connection.cursor()
        
        # 1. Buscamos el ID del usuario en la tabla Usuarios mediante su Nombre_Completo
        cursor.execute("SELECT ID FROM Usuarios WHERE Nombre_Completo = %s", (nombre_solicitante,))
        usuario = cursor.fetchone()
        
        if usuario:
            id_usuario = usuario[0]
            
            # 2. Insertamos en la tabla correspondiente según si es Computadora o Carro
            # Usamos los nombres de columnas correctos de tus tablas de préstamos
            if tipo_prestamo == 'Computadora':
                cursor.execute(
                    "INSERT INTO Prestamos_Computadoras (ID_Usuario, Numero_Computadora, Hora_Inicio, Hora_Limite) VALUES (%s, %s, NOW(), %s)",
                    (id_usuario, item_title, fecha_limite)
                )
            elif tipo_prestamo == 'Carro':
                cursor.execute(
                    "INSERT INTO Prestamos_Carros (ID_Profesor, Numero_Carro, Hora_Inicio, Hora_Limite, Estado) VALUES (%s, %s, NOW(), %s)",
                    (id_usuario, item_title, fecha_limite)
                )
                
            # Guardamos los cambios en la base de datos de MySQL
            mysql.connection.commit()
            
        cursor.close()
        
        # Redirigimos de vuelta al inicio para actualizar la vista
        return redirect(url_for('inicio'))

# Ruta de Préstamos: SELECT dinámico unificado de todas las tablas de préstamos
@app.route('/prestamos')
def prestamos():
    if not session.get('loggedin'):
        return redirect(url_for('login'))
        
    cursor = mysql.connection.cursor()

    # Consulta unificada para traer todos los préstamos activos conectando con la tabla Usuarios
    cursor.execute("""
        -- 1. Préstamos de Libros
        SELECT p.ID, 'Libro' as Tipo, l.Titulo as Elemento, 
               u.Nombre_Completo as Solicitante,
               CASE WHEN u.esProfesor = 1 THEN 'Profesor/a' ELSE 'Estudiante' END as Rol,
               p.Fecha_Limite as FechaLimite, 'En curso' as Estado
        FROM Prestamos_Libros p
        JOIN Ejemplares e ON p.ID_Ejemplar = e.ID
        JOIN Libros l ON e.ISBN_Libro = l.ISBN
        JOIN Usuarios u ON p.ID_Usuario = u.ID
        
        UNION
        
        -- 2. Préstamos de Computadoras
        SELECT p.ID, 'Computadora' as Tipo, CONCAT('Netbook - ID: ', p.Numero_Computadora) as Elemento,
               u.Nombre_Completo as Solicitante,
               CASE WHEN u.esProfesor = 1 THEN 'Profesor/a' ELSE 'Estudiante' END as Rol,
               p.Hora_Limite as FechaLimite, 'En curso' as Estado
        FROM Prestamos_Computadoras p
        JOIN Usuarios u ON p.ID_Usuario = u.ID
        
        UNION
        
        -- 3. Préstamos de Carros (Hecho por profesores)
        SELECT p.ID, 'Carro' as Tipo, CONCAT('Carro ID: ', p.Numero_Carro) as Elemento,
               u.Nombre_Completo as Solicitante, 'Profesor/a' as Rol,
               p.Hora_Limite as FechaLimite, 'En curso' as Estado
        FROM Prestamos_Carros p
        JOIN Usuarios u ON p.ID_Profesor = u.ID
        
        UNION
        
        -- 4. Préstamos de Elementos
        SELECT p.ID, 'Otros' as Tipo, p.Codigo_Elementos as Elemento,
               u.Nombre_Completo as Solicitante,
               CASE WHEN u.esProfesor = 1 THEN 'Profesor/a' ELSE 'Estudiante' END as Rol,
               p.Hora_Limite as FechaLimite, 'En curso' as Estado
        FROM Prestamos_Elementos p
        JOIN Usuarios u ON p.ID_Usuario = u.ID
    """)
    
    data = cursor.fetchall()
    cursor.close()
    
    # Transformamos los datos en una lista de diccionarios para enviarla al HTML de préstamos
    lista_prestamos = []
    for row in data:
        lista_prestamos.append({
            'id': row[0],
            'tipo': row[1],
            'elemento': row[2],
            'solicitante': row[3],
            'rol': row[4],
            'fecha_limite': str(row[5]),
            'estado': row[6]
        })
        
    return render_template('prestamo.html', prestamos=lista_prestamos)


# Ruta de Catálogo e Inventario corregida
@app.route('/catalogo', methods=['GET', 'POST'])
def catalogo():
    cursor = mysql.connection.cursor()
    
    # Si el usuario envía el formulario modal (método POST)
    if request.method == 'POST':
        numero_compu = request.form['numero']
        numero_carro = request.form['numero_carro']
        estado = request.form['estado']

        try:
            cursor.execute(
                "INSERT INTO Computadoras (Numero, Numero_Carro, Estado) VALUES (%s, %s, %s)",
                (numero_compu, numero_carro, estado)
            )
            mysql.connection.commit() # Corregido: se usa mysql.connection en lugar de conexion
        except Exception as e:
            print(f"Error al registrar la computadora: {e}")
        finally:
            cursor.close()

        # Recarga la misma página ya con el registro guardado
        return redirect(url_for('catalogo'))

    # Si es método GET: Obtenemos las computadoras y los carros para el selector del modal
    cursor.execute("""
        SELECT Numero, Numero_Carro, Estado
        FROM Computadoras
    """)
    computadoras = cursor.fetchall()

    cursor.execute("SELECT Numero FROM Carros")
    carros = cursor.fetchall()

    cursor.close()
    
    return render_template('catalogo.html', computadoras=computadoras, carros=carros)

@app.route('/usuarios')
def usuarios():
    lista_usuarios = []
    try:
        # 1. Abrir conexión y cursor (con dictionary=True para acceder fácilmente por nombre de columna)
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        
        # 2. Consultar la tabla Usuarios
        cursor.execute("SELECT ID, Nombre_Completo, DNI, Email, esProfesor, esBibliotecario FROM Usuarios")
        lista_usuarios = cursor.fetchall()
        
        # 3. Cerrar cursor y conexión
        cursor.close()
        conexion.close()
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")
    
    # 4. Renderizar la plantilla enviándole los datos reales
    return render_template('usuarios.html', usuarios=lista_usuarios)
    
if __name__ == '__main__':
    app.run(debug=True)