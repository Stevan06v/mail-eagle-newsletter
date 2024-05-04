import os
import pandas as pd
from flask_bootstrap import Bootstrap5
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.file import FileAllowed, FileRequired
from jsonstore import JsonStore
from wtforms.fields import *
from dotenv import load_dotenv
from wtforms.validators import DataRequired, Length, Regexp
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from secrets import compare_digest

load_dotenv()

store = JsonStore('config.json')

app = Flask(__name__)

app.secret_key = 'dev'

login_manager = LoginManager(app)

bootstrap = Bootstrap5(app)

csrf = CSRFProtect(app)


# Define a User model
class User(UserMixin):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_id(self):
        return self.username


@login_manager.user_loader
def load_user(user_id):
    return user if user.get_id() == user_id else None


user = User(os.getenv('LOGIN'), os.getenv('PASSWORD'))

# Register the user with Flask-Login
login_manager.user_loader(load_user)


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 150)])
    submit = SubmitField()


class SenderEmailCredentials(FlaskForm):
    smtp_server = StringField('SMTP-Server', validators=[DataRequired()])
    smtp_port = IntegerField('SMTP-Port', validators=[DataRequired()])
    sender_email = EmailField('Sender-Email', validators=[DataRequired()])
    sender_password = PasswordField('Sender-Password', validators=[DataRequired()])

    submit = SubmitField()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    login_form = LoginForm()

    if login_form.validate_on_submit():
        if user.username == login_form.username.data and compare_digest(user.password, login_form.password.data):
            # Login the user
            login_user(user)

            flash('Successfully logged in!')
            return redirect(url_for('index'))
        else:
            return render_template('login.html', form=login_form, error='Invalid username or password')

    return render_template('login.html', form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect('/login')
    else:
        return render_template('index.html')


@app.route('/configure', methods=['GET', 'POST'])
@login_required
def configure():
    form = SenderEmailCredentials()
    if request.method == 'POST' and form.validate_on_submit():
        # Process form data
        smtp_server = form.smtp_server.data
        smtp_port = form.smtp_port.data
        sender_email = form.sender_email.data
        sender_password = form.sender_password.data

        store['email_sender.smtp_server'] = smtp_server
        store['email_sender.smtp_port'] = smtp_port
        store['email_sender.sender_email'] = sender_email
        store['email_sender.sender_password'] = sender_password

        flash('Email sender configuration saved successfully!', 'success')

        return redirect(url_for('configure'))

    # Load existing data if available
    form.smtp_server.data = store['email_sender.smtp_server']
    form.smtp_port.data = store['email_sender.smtp_port']
    form.sender_email.data = store['email_sender.sender_email']
    form.sender_password.data = store['email_sender.sender_password']

    return render_template('configure.html', form=form, email_sender=store['email_sender'])


class JobForm(FlaskForm):
    name = StringField('Job Name', description="Define a name to identify the job later on.",
                       validators=[DataRequired()])
    csv = FileField(label="Email List as CSV", description="Input the HTML Newsletter Content File.",
                    validators=[FileAllowed(['csv']), FileRequired()])
    column = StringField('Email Column Name', description="Use the exact name of your CSV Email Column.",
                         validators=[DataRequired()])
    subject = StringField(description="Set a subject for the email.",
                          validators=[DataRequired()])
    content = FileField(description="Input the HTML Newsletter Content File.",
                        validators=[FileAllowed(['html'], FileRequired())])
    date = DateTimeLocalField(description="This field indicates the date when the newsletter should be sent.",
                              validators=[DataRequired()])
    submit = SubmitField('Add')



@app.route('/jobs', methods=['GET', 'POST'])
@login_required
def jobs():
    form = JobForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Handle file uploads
            csv_file = form.csv.data
            content_file = form.content.data

            # Save uploaded files to a folder
            if csv_file:
                csv_file_path = os.path.join('uploads', csv_file.filename)
                csv_file.save(csv_file_path)
            if content_file:
                content_file_path = os.path.join('uploads', content_file.filename)
                content_file.save(content_file_path)

            store['email_sender.smtp_server']
            name = form.name.data
            column = form.column.data
            subject = form.subject.data
            date = form.date.data

            flash("Successfully created job!", 'success')
            return redirect(url_for('jobs'))
        except Exception as e:
            flash(f"An error occurred: {e}", 'error')

    return render_template('jobs.html', form=form)


app.run(debug=True)

