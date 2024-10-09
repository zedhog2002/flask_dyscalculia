from app import app
from app import db

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()  
        db.create_all()

    app.run(debug=True,port=5566)