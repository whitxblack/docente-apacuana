from app import create_app

app = create_app()

if __name__ == '__main__':
    # Usamos el puerto 5000 por defecto para Flask, 
    # ya que Django en gestor-apacuana usa el 8000.
    app.run(debug=True, port=5000)
