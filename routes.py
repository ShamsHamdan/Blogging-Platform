# routes.py

from flask import render_template, flash, redirect, url_for, jsonify, request
from flask_login import current_user, login_user, logout_user, login_required
from app.forms import RegistrationForm, LoginForm, PostForm
from app.models import User, Post, Interaction, Comment
from main import app, db
from werkzeug.security import check_password_hash


@app.route('/')
def get_started():
    return render_template('getStarted.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():

        user = User(username=form.username.data, email=form.email.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('regForm.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password_hash,
                                        form.password.data):
            login_user(user)  # Log in the user
            flash('Login successful!')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('login'))

    print("Form errors:", form.errors)
    return render_template('loginForm.html', title='Sign In', form=form)


@app.route('/home')
def home():
    posts = Post.query.all()
    post_comments = {}
    post_likes = {}
    liked_users = {}
    for post in posts:
        comments = Comment.query.filter_by(post_id=post.id).all()
        post_comments[post.id] = comments
        liked_users[post.id] = [interaction.user.username for interaction in post.interactions]
        liked = Interaction.query.filter_by(user_id=current_user.id, post_id=post.id).first() is not None
        post_likes[post.id] = liked
    return render_template('home.html', posts=posts, post_comments=post_comments, post_likes=post_likes,
                           liked_users=liked_users)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_started'))


@app.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).all()
    return render_template('user_profile.html', user=user, posts=posts)


@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You are not authorized to edit this post.', 'danger')
        return redirect(url_for('user_profile', username=current_user.username))

    form = PostForm(obj=post)
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated.', 'success')
        return redirect(url_for('user_profile', username=current_user.username))

    return render_template('editPost.html', title='Edit Post', form=form)


@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You are not authorized to delete this post.', 'danger')
        return redirect(url_for('home'))
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted.', 'success')
    return redirect(url_for('user_profile', username=current_user.username))


@app.route('/add_post', methods=['GET', 'POST'])
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_post = Post(title=title, content=content, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        flash('The Post Added Successfully.', 'success')
        return redirect(url_for('user_profile', username=current_user.username))
    return render_template('addPost.html')


@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('comment')
    if content:
        comment = Comment(body=content, user_id=current_user.id, post_id=post.id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment added successfully.', 'success')

        return redirect(url_for('home'))

    return jsonify({'error': 'Content is required'}), 400


@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    liked_post = Post.query.get_or_404(post_id)
    if liked_post.author != current_user:  # Ensure the user can't like their own post
        if current_user.username not in [like.user.username for like in liked_post.interactions]:
            interaction = Interaction(user=current_user, post=liked_post, reaction='like')
            db.session.add(interaction)
            db.session.commit()
            # Return the username in the response
            return jsonify({'success': True, 'username': current_user.username}), 200
        else:
            return jsonify({'success': False, 'error': 'You have already liked this post'}), 400
    else:
        return jsonify({'success': False, 'error': 'You cannot like your own post'}), 400


@app.route('/view_comments/<int:post_id>')
def view_comments(post_id):
    post = Post.query.get_or_404(post_id)
    comments = post.comments
    return render_template('comment.html', post=post, comments=comments)


@app.route('/post/<int:post_id>/likes')
def post_likes(post_id):
    post = Post.query.get_or_404(post_id)
    liked_users = [interaction.user for interaction in post.interactions if interaction.reaction == 'like']
    return render_template('interact.html', post=post, liked_users=liked_users)
