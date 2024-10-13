from flask import Flask, request, jsonify, render_template
import pickle
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import numpy as np
from sqlalchemy.orm import relationship
from skfuzzy import control as ctrl

app = Flask(__name__)
CORS(app)  # Allow all domains; customize as needed

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database models
class registration(db.Model):
    firebase_uid = db.Column(db.String(100), primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(50), nullable=False)

    user_profile = relationship('UserProfile', backref='registration', uselist=False)

    def __repr__(self):
        return f"Registration('{self.username}', '{self.email}')"


class UserProfile(db.Model):
    firebase_uid = db.Column(db.String(100), db.ForeignKey('registration.firebase_uid'), primary_key=True)
    child_name = db.Column(db.String(100), nullable=False)
    child_age = db.Column(db.Integer, nullable=False)
    parent_name = db.Column(db.String(100), nullable=False)
    parent_phone_number = db.Column(db.Integer, nullable=False)  # Change to String for phone numbers
    address = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"UserProfile('{self.child_name}', '{self.parent_name}', '{self.parent_phone_number}')"


class Quiz1(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    firebase_uid = db.Column(db.String(100), db.ForeignKey('registration.firebase_uid'), nullable=False)
    quiz_id = db.Column(db.Integer, nullable=False)
    question1_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    question2_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    question3_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    question4_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    question5_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    average_result = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"Quiz1('{self.firebase_uid}', '{self.quiz_id}', '{self.average_result}')"


class Questions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, nullable=False)
    question_id = db.Column(db.Integer, nullable=False)
    options = db.Column(db.String(255), nullable=False)  # Assuming options are stored as a single string


class predicted_values(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    firebase_uid = db.Column(db.String(100), db.ForeignKey('registration.firebase_uid'), nullable=False)
    predicted_values = db.Column(db.Float, nullable=False)

def apply_fuzzy_logic_system(counting_input, color_input, calculation_input, control_system):
    simulator = ctrl.ControlSystemSimulation(control_system)
    simulator.input['Counting_Ability'] = np.mean(counting_input)
    simulator.input['Color_Ability'] = np.mean(color_input)
    simulator.input['Calculation_Ability'] = np.mean(calculation_input)
    simulator.compute()
    return simulator.output['Percentage']

# Load the fuzzy control system from the pickle file
with open('fuzzy_model.pkl', 'rb') as file:
    loaded_fuzzy_ctrl = pickle.load(file)

@app.route('/')
def main_page():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        counting_input = data['counting_input']
        color_input = data['color_input']
        calculation_input = data['calculation_input']
        firebase_uid = data['uid']

        prediction = apply_fuzzy_logic_system(counting_input, color_input, calculation_input, loaded_fuzzy_ctrl)

        new_predicted_value = predicted_values(firebase_uid=firebase_uid, predicted_values=prediction)
        db.session.add(new_predicted_value)
        db.session.commit()

        return jsonify({'prediction': prediction})

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/prediction_table/<string:firebase_uid>', methods=['GET'])
def get_prediction_table(firebase_uid):
    try:
        predictions = predicted_values.query.filter_by(firebase_uid=firebase_uid).all()
        if predictions:
            prediction_data = [{'id': pred.id, 'firebase_uid': pred.firebase_uid, 'predicted_values': pred.predicted_values} for pred in predictions]
            return jsonify({'predictions': prediction_data})
        else:
            return jsonify({'message': 'No predictions found for the given user'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/save_user_details', methods=['POST'])
def save_user_details():
    try:
        data = request.get_json()
        user_profile_data = {
            'firebase_uid': data['uid'],
            'child_name': data['child_name'],
            'child_age': data['child_age'],
            'parent_name': data['parent_name'],
            'parent_phone_number': data['parent_phone_number'],
            'address': data['address'],
        }

        existing_profile = UserProfile.query.filter_by(firebase_uid=user_profile_data['firebase_uid']).first()
        if existing_profile:
            existing_profile.child_name = user_profile_data['child_name']
            existing_profile.child_age = user_profile_data['child_age']
            existing_profile.parent_name = user_profile_data['parent_name']
            existing_profile.parent_phone_number = user_profile_data['parent_phone_number']
            existing_profile.address = user_profile_data['address']
        else:
            user_profile = UserProfile(**user_profile_data)
            user_profile = UserProfile(firebase_uid=user_profile_data['firebase_uid'],
                                       child_name=user_profile_data['child_name'],
                                       child_age=user_profile_data['child_age'],
                                       parent_name=user_profile_data['parent_name'],
                                       parent_phone_number=user_profile_data['parent_phone_number'],
                                       address=user_profile_data['address'])
            db.session.add(user_profile)

        db.session.commit()
        return jsonify({'message': 'User details saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/register_user', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        new_registration = registration(**data)
        db.session.add(new_registration)
        db.session.commit()
        return jsonify({'message': 'Registration successful'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/quiz_update', methods=['POST'])
def quiz_update():
    try:
        data = request.get_json()
        questionids = data.get('questionids', [])
        quizid = data.get('quizid')
        avg_result = data.get('avg_result')
        firebase_uid = data.get('uid')

        new_quiz_update = Quiz1(
            firebase_uid=firebase_uid,
            quiz_id=quizid,
            question1_id=questionids[0],
            question2_id=questionids[1],
            question3_id=questionids[2],
            question4_id=questionids[3],
            question5_id=questionids[4],
            average_result=avg_result
        )

        db.session.add(new_quiz_update)
        db.session.commit()

        return jsonify({'message': 'Quiz update successful'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_user_details/<string:firebase_uid>', methods=['GET'])
def get_user_details(firebase_uid):
    try:
        user_profile = UserProfile.query.filter_by(firebase_uid=firebase_uid).first()
        if user_profile:
            return jsonify({
                'child_name': user_profile.child_name,
                'child_age': user_profile.child_age,
                'parent_name': user_profile.parent_name,
                'parent_phone_number': user_profile.parent_phone_number,
                'address': user_profile.address,
            })
        else:
            return jsonify({'error': 'User profile not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/result_history/<string:firebase_uid>', methods=['GET'])
def result_history(firebase_uid):
    try:
        results = Quiz1.query.filter_by(firebase_uid=firebase_uid).all()
        result_data = [{'quiz_id': result.quiz_id,
                        'question1_id': result.question1_id,
                        'question2_id': result.question2_id,
                        'question3_id': result.question3_id,
                        'question4_id': result.question4_id,
                        'question5_id': result.question5_id,
                        'average_result': result.average_result} for result in results]

        return jsonify({'results': result_data})
    except Exception as e:
        return jsonify({'error': str(e)})

