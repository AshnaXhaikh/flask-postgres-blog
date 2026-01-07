from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
DELETE_KEY = os.environ.get('DELETE_KEY')

# ---------------- IN-MEMORY STORAGE ----------------
posts = []
post_counter = 1

# ---------------- CONTEXT PROCESSOR ----------------
@app.context_processor
def inject_datetime():
    return dict(datetime=datetime)

# ---------------- FILTERS ----------------
@app.template_filter('strftime')
def datetimeformat(value, format='%B %d, %Y'):
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

@app.template_filter('truncate')
def truncate_filter(s, length, end='...'):
    if len(s) <= length:
        return s
    return s[:length] + end

# ---------------- ROUTES ----------------

@app.route('/')
def index():
    sorted_posts = sorted(posts, key=lambda x: x['created_at'], reverse=True)
    return render_template('index.html', posts=sorted_posts)

@app.route('/add', methods=['GET', 'POST'])
def add():
    global post_counter

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if any(p['title'] == title for p in posts):
            flash('A post with this title already exists.', 'danger')
            return redirect(url_for('add'))

        posts.append({
            'id': post_counter,
            'title': title,
            'content': content,
            'created_at': datetime.utcnow()
        })

        post_counter += 1
        flash('New blog post created!', 'success')
        return redirect(url_for('index'))

    return render_template('add_post.html')

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        return "Post not found", 404
    return render_template('post_detail_page.html', post=post)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit(post_id):
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        return "Post not found", 404

    if request.method == 'POST':
        new_title = request.form['title']
        new_content = request.form['content']

        if any(p['title'] == new_title and p['id'] != post_id for p in posts):
            flash('Another post with this title already exists.', 'danger')
            return redirect(url_for('edit', post_id=post_id))

        post['title'] = new_title
        post['content'] = new_content
        flash('Post updated successfully!', 'success')
        return redirect(url_for('post_detail', post_id=post_id))

    return render_template('edit_post.html', post=post)

@app.route('/delete/<int:post_id>', methods=['POST'])
def delete(post_id):
    global posts

    submitted_key = request.form.get('admin_key')

    if DELETE_KEY and submitted_key != DELETE_KEY:
        flash('Authorization failed.', 'danger')
        return redirect(url_for('post_detail', post_id=post_id))

    posts = [p for p in posts if p['id'] != post_id]
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('index'))
