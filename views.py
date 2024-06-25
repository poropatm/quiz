import os
from random import shuffle

from flask import redirect, url_for, flash, render_template, Blueprint, request, json, current_app
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import func, and_
from werkzeug.utils import secure_filename

from config import STATIC_FOLDER, IMAGES_FOLDER
from models import User, db, Question, QuizScore, Quiz, Answer, Image
from forms import LoginForm, RegistrationForm, AddQuestionForm, SelectQuizForm, EditQuizForm
from datetime import datetime, timezone
import plotly.express as px

views_app = Blueprint('views', __name__)
admin_app = Blueprint('admin', __name__)


# username:user, pass:user
# username:admin, pass:admin


# Ako je korisnik prijavljen, preusmjerava na 'views.welcome', inače na 'views.login'.
@views_app.route('/')
def root():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.select_quiz'))
        else:
            return redirect(url_for('views.welcome'))
    else:
        return redirect(url_for('views.login'))


# Prikazuje obrazac za prijavu i obrađuje prijavu korisnika
@views_app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login successful!', 'success')

            next_page = request.args.get('next')
            if current_user.is_admin:
                return redirect(next_page or url_for('admin.admin_dashboard'))
            else:
                return redirect(next_page or url_for('views.welcome'))

        else:
            # Dodaj grešku na polja username i password
            form.username.errors.append('Netočno korisničko ime ili lozinka.')
            form.password.errors.append('Netočno korisničko ime ili lozinka.')

    return render_template('login.html', form=form)


# Prikazuje obrazac za registraciju i obrađuje registraciju novog korisnika
@views_app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        # Provjeri postoji li već user s tim usernameom
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            # Greška ako user s tim usernameom već postoji
            form.username.errors.append('Korisničko ime već postoji. Molimo odaberite drugo.')
            return redirect(url_for('views.register'))

        # Kreiranje novog usera
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            username=form.username.data
        )
        new_user.set_password(form.password.data)

        # Spremi novog usera u bazu
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('views.login'))

    return render_template('register.html', form=form)


# Prikazuje i obrađuje kviz za zadani ID kviza
@views_app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def quiz(quiz_id):
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    quiz_name = Quiz.query.get(quiz_id).quiz_name

    for question in questions:
        shuffle(question.answers)

    if request.method == 'POST':
        user_answers_json = request.form.get('userAnswers')

        if user_answers_json:
            user_answers = json.loads(user_answers_json)
        else:
            user_answers = {}

        correct_count = 0  # Broj točnih odgovora
        total_questions = len(questions)

        for question in questions:
            question_id = str(question.id)
            user_answer = user_answers.get(question_id)

            correct_answer = next((answer for answer in question.answers if answer.is_correct), None)
            if user_answer and correct_answer:
                if user_answer == correct_answer.option_text:
                    correct_count += 1

        # Izračunaj postotak
        if total_questions > 0:
            percentage_score = round((correct_count / total_questions) * 100)
        else:
            percentage_score = 0

        # Spremi rezultat u bazu
        quiz_score = QuizScore(user_id=current_user.id, quiz_id=quiz_id, score=percentage_score,
                               date=datetime.now(timezone.utc))
        db.session.add(quiz_score)
        db.session.commit()

        return render_template('quiz1.html', quiz_id=quiz_id, quiz_name=quiz_name, score=percentage_score, total=100)

    shuffle(questions)

    return render_template('quiz1.html', quiz_id=quiz_id, quiz_name=quiz_name, questions=questions, score=None)


# Prikazuje rang listu za određeni kviz s najboljim rezultatom za svakog korisnika
@views_app.route('/highscores/<int:quiz_id>')
@login_required
def highscores(quiz_id):
    # Nađi najbolji rezultat po useru
    high_scores = db.session.query(
        User.username,
        func.max(QuizScore.score).label('max_score'),
        func.max(QuizScore.date).label('max_date')
    ).join(QuizScore, User.id == QuizScore.user_id). \
        filter(QuizScore.quiz_id == quiz_id). \
        group_by(User.username). \
        order_by(func.max(QuizScore.score).desc()).limit(10).all()

    return render_template('highscores.html', quiz_id=quiz_id, high_scores=high_scores)


# prikaz profila s rezultatima
@views_app.route('/profile')
@login_required
def profile():
    user_highscores = (
        db.session.query(Quiz.quiz_name, db.func.max(QuizScore.score).label('max_score'))
        .join(QuizScore, Quiz.id == QuizScore.quiz_id)
        .filter_by(user_id=current_user.id)
        .group_by(Quiz.quiz_name)
        .all()
    )

    return render_template('profile.html', user_highscores=user_highscores, username=current_user.username)


@views_app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.login'))


# početna stranica, prikazuje sve kvizove
@views_app.route('/welcome')
@login_required
def welcome():
    quizzes = Quiz.query.all()

    return render_template('welcome.html', username=current_user.username, quizzes=quizzes)


# početna stranica za admina
@admin_app.route('/admin', methods=['GET'])
@login_required
def admin_dashboard():
    if current_user.is_admin:  # provjera je li user admin
        return redirect(url_for('admin.select_quiz'))
    else:
        return redirect(
            url_for('views.welcome'))  # ako pokušava pristupiti ne admin redirect na njegovu početnu stranicu


# selektiranje kviza za kojeg će se mijenjati/dodavati pitanja
@admin_app.route('/select_quiz', methods=['GET', 'POST'])
@login_required
def select_quiz():
    quizzes = Quiz.query.all()

    if current_user.is_admin:
        form = SelectQuizForm()
        form.quiz.choices = [(quiz_el.id, quiz_el.quiz_name) for quiz_el in quizzes]

        if form.validate_on_submit():
            selected_quiz_id = int(request.form.get('quiz'))
            return redirect(url_for('admin.list_questions', quiz_id=selected_quiz_id))

        return render_template('admin/selectQuiz.html', form=form, quizzes=quizzes)
    else:
        return redirect(url_for('views.welcome'))


# Dodavanje novog kviza
@admin_app.route('/add_quiz', methods=['POST'])
@login_required
def add_quiz():
    if current_user.is_admin:
        if request.method == 'POST':
            new_quiz_name = request.form.get('new_quiz')

            if new_quiz_name:
                new_quiz = Quiz(quiz_name=new_quiz_name)
                db.session.add(new_quiz)
                db.session.commit()

        return redirect(url_for('admin.select_quiz'))
    else:
        return redirect(url_for('views.welcome'))


# Brisanje kviza
@admin_app.route('/delete_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def delete_quiz(quiz_id):
    if current_user.is_admin:
        quiz_to_delete = Quiz.query.get_or_404(quiz_id)

        for question in quiz_to_delete.questions:
            db.session.delete(question)

        db.session.delete(quiz_to_delete)
        db.session.commit()

        return redirect(url_for('admin.select_quiz'))
    else:
        return redirect(url_for('views.welcome'))


# popis pitanja, mogućnost brisanja ili izmjene pojedinih pitanja u određenom kvizu
@admin_app.route('/list_questions/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def list_questions(quiz_id):
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    selected_quiz = Quiz.query.get(quiz_id)
    edit_quiz_form = EditQuizForm()

    if edit_quiz_form.validate_on_submit():
        new_quiz_name = edit_quiz_form.new_quiz_name.data
        selected_quiz.quiz_name = new_quiz_name
        db.session.commit()
        return redirect(url_for('admin.list_questions', quiz_id=quiz_id))

    edit_quiz_form.new_quiz_name.data = selected_quiz.quiz_name
    return render_template('admin/listQuestions.html', quiz_id=quiz_id, quiz_name=selected_quiz.quiz_name,
                           questions=questions, edit_quiz_form=edit_quiz_form)


# dodavanje pitanja u kviz
@admin_app.route('/add_question/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    if current_user.is_admin:
        form = AddQuestionForm()

        if form.validate_on_submit():
            question_text = form.question_text.data
            options = [
                form.option_a.data,
                form.option_b.data,
                form.option_c.data,
                form.option_d.data
            ]
            correct_option = form.correct_option.data

            # Kreiranje pitanja i dodavanje u bazu
            new_question = Question(
                quiz_id=quiz_id,
                question_text=question_text
            )
            db.session.add(new_question)
            db.session.commit()

            # Kreiranje odgovora za to pitanje i dodavanje odgovora u bazu
            for i, option in enumerate(options):
                is_correct = (correct_option == f'option_{chr(97 + i)}')
                new_answer = Answer(
                    question_id=new_question.id,
                    option_text=option,
                    is_correct=is_correct
                )
                db.session.add(new_answer)

            db.session.commit()

            # Upload slike
            image_file = form.image_upload.data
            if image_file:
                # Spremanje uploadane slike
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(STATIC_FOLDER, IMAGES_FOLDER, filename)
                image_file.save(image_path)

                # Kreiranje Image i povezivanje s pitanjem
                new_image = Image(file_path=f'{IMAGES_FOLDER}/{filename}')
                new_question.image = new_image
                db.session.add(new_image)

            db.session.commit()

            return redirect(url_for('admin.edit_question', quiz_id=quiz_id, question_id=new_question.id))
        return render_template('admin/addQuestion.html', form=form, quiz_id=quiz_id)
    else:
        return redirect(url_for('views.welcome'))


# izmjena pitanja u kvizu
@admin_app.route('/edit_question/<int:quiz_id>/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(quiz_id, question_id):
    if current_user.is_admin:
        question = Question.query.get_or_404(question_id)
        form = AddQuestionForm()

        if form.validate_on_submit():
            question.question_text = form.question_text.data
            question.answers[0].option_text = form.option_a.data
            question.answers[1].option_text = form.option_b.data
            question.answers[2].option_text = form.option_c.data
            question.answers[3].option_text = form.option_d.data
            question.answers[0].is_correct = (form.correct_option.data == 'option_a')
            question.answers[1].is_correct = (form.correct_option.data == 'option_b')
            question.answers[2].is_correct = (form.correct_option.data == 'option_c')
            question.answers[3].is_correct = (form.correct_option.data == 'option_d')

            # Upload slike ako 'image_upload' postoji u podacima forme
            if 'image_upload' in request.files:
                image_file = request.files['image_upload']
                if image_file:
                    # Ako već postoji slika povezana s pitanjem, brisanje te slike
                    if question.image:
                        existing_image_path = os.path.normpath(os.path.join('static', question.image.file_path))

                        if os.path.exists(existing_image_path):
                            os.remove(existing_image_path)

                        # Uklanjanje te slike s pitanja
                        db.session.delete(question.image)

                    filename = secure_filename(image_file.filename)
                    image_path = os.path.join('static', 'images', filename)
                    image_file.save(image_path)

                    # Kreiranje Image i povezivanje s pitanjem
                    new_image = Image(file_path=f'images/{filename}')  # Update the file_path
                    question.image = new_image

                    db.session.add(new_image)

            db.session.commit()

            return redirect(url_for('admin.edit_question', quiz_id=quiz_id, question_id=question_id))

        # popunjavanje forme s trenutnim podacima
        form.question_text.data = question.question_text
        for i, answer in enumerate(question.answers):
            form[f'option_{chr(ord("a") + i)}'].data = answer.option_text

            # namješta correct_option polje u formi ovisno o tome koji je odgovor točan
            if answer.is_correct:
                form.correct_option.data = f'option_{chr(ord("a") + i)}'

        return render_template('admin/editQuestion.html', form=form, quiz_id=quiz_id, question_id=question_id,
                               question=question)

    else:
        return redirect(url_for('views.welcome'))


# brisanje određenog pitanja
@admin_app.route('/delete_question/<int:quiz_id>/<int:question_id>', methods=['GET', 'POST'])
@login_required
def delete_question(quiz_id, question_id):
    if current_user.is_admin:
        question = Question.query.get_or_404(question_id)

        # Briše pitanje i njegove povezane odgovore
        db.session.delete(question)
        db.session.commit()

        # Vraća na popis pitanja za taj kviz, tj vizualno samo refresha stranicu
        return redirect(url_for('admin.list_questions', quiz_id=quiz_id))

    else:
        return redirect(url_for('views.welcome'))


# brisanje slike
@admin_app.route('/delete_image/<int:question_id>', methods=['POST'])
@login_required
def delete_image(question_id):
    if current_user.is_admin:
        question = Question.query.get_or_404(question_id)

        # Provjera ima li pitanje povezanu sliku
        if question.image and db.session.query(Image).get(question.image.id):
            # Brisanje slike
            image_path = os.path.normpath(os.path.join('static', question.image.file_path))

            if os.path.exists(image_path):
                os.remove(image_path)

            # Uklanjanje te slike s pitanja
            db.session.delete(question.image)
            db.session.commit()

            # Redirekt na editiranje tog pitanja
            return redirect(url_for('admin.edit_question', quiz_id=question.quiz_id, question_id=question_id))

        else:
            return redirect(url_for('admin.edit_question', quiz_id=question.quiz_id, question_id=question_id))

    else:
        return redirect(url_for('views.welcome'))


@admin_app.route('/quiz_statistics/<int:quiz_id>')
@login_required
def quiz_statistics(quiz_id):
    # Upit za računanje statistike
    quiz_statistics_data = db.session.query(
        User.username,
        QuizScore.score
    ).join(QuizScore, User.id == QuizScore.user_id). \
        filter(QuizScore.quiz_id == quiz_id).all()

    # Kreiranje DataFramea za rezultat upita
    import pandas as pd
    df = pd.DataFrame(quiz_statistics_data, columns=['Korisničko ime', 'Rezultat'])

    # Računanje statistike - prosjek, max
    average_score = df['Rezultat'].mean()
    highest_score = df['Rezultat'].max()

    # Plotly Express - kreiranje histograma
    bins = [i for i in range(0, 101)]
    fig = px.histogram(df, x='Rezultat', nbins=len(bins) - 1, range_x=(0, 101),
                       labels={'Rezultat': 'Rezultat kviza'},
                       title='Distribucija rezultata', category_orders={'Rezultat': bins},
                       histnorm='percent', color_discrete_sequence=['lightcoral'])

    fig.update_yaxes(title_text='Postotak')
    fig.update_layout(title_x=0.5)

    # Pretvaranje u HTML
    chart_html = fig.to_html(full_html=False)

    # Dohvati sve kvizove za popunjavanje dropdown-a
    quizzes = Quiz.query.all()

    # Dohvati odabrani kviz
    selected_quiz = Quiz.query.get(quiz_id)

    return render_template('quizStatistics.html', chart_html=chart_html, average_score=average_score,
                           highest_score=highest_score, quiz_id=quiz_id, quizzes=quizzes, selected_quiz=selected_quiz)


@admin_app.route('/quiz_statistics_all')
@login_required
def quiz_statistics_all():
    # Dohvati podatke o statistici za sve kvizove iz baze podataka
    quiz_statistics_data = db.session.query(
        Quiz.quiz_name,
        func.avg(QuizScore.score).label('Prosjek'),
        func.max(QuizScore.score).label('Najviši rezultat')
    ).join(QuizScore, Quiz.id == QuizScore.quiz_id).group_by(Quiz.id).all()

    # Stvori DataFrame iz rezultata upita
    import pandas as pd
    df = pd.DataFrame(quiz_statistics_data, columns=['Naziv Kviza', 'Prosjek', 'Najviši rezultat'])

    # Izračunaj prosječan rezultat i najviši rezultat
    average_score = df['Prosjek'].mean()
    highest_score = df['Najviši rezultat'].max()

    # Stvori stupčasti grafikon pomoću Plotly Express
    fig = px.bar(df, x='Naziv Kviza', y=['Prosjek', 'Najviši rezultat'],
                 title='Rezultati po kvizovima', labels={'value': 'Rezultat', 'variable': ''}, barmode='group',
                 color_discrete_map={'Prosjek': 'lightblue', 'Najviši rezultat': 'lightcoral'})

    fig.update_xaxes(title_text='')
    fig.update_layout(title_x=0.5)

    # Pretvori Plotly sliku u HTML
    chart_html = fig.to_html(full_html=False)

    # Dohvati sve kvizove za popunjavanje dropdown-a
    quizzes = Quiz.query.all()

    # Prikazi HTML predložak s grafikonom i statistikama
    return render_template('quizStatisticsAll.html', chart_html=chart_html, average_score=average_score,
                           highest_score=highest_score, quizzes=quizzes)
