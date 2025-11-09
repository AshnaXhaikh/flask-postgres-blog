from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
import os 
# Used for local development only, safe to keep for consistency
from dotenv import load_dotenv

load_dotenv() 

app = Flask(__name__)

# context processor to make datetime available in all templates
@app.context_processor
def inject_datetime():
    return dict(datetime=datetime)

# settin up custom Jinja2 filters
@app.template_filter('strftime')
def datetimeformat(value, format='%B %d, %Y'):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime(format)
    try:
        date_obj = datetime.fromisoformat(str(value)) 
        return date_obj.strftime(format)
    except Exception:
        return str(value)

@app.template_filter('truncate')
def truncate_filter(s, length, killwords=False, end='...'):
    if len(s) <= length:
        return s
    return s[:length] + end

# --- FLASK CONFIGURATION (NOW SECURELY READING FROM ENVIRONMENT) ---

# CRITICAL: Database URI
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
if not app.config['SQLALCHEMY_DATABASE_URI']:
    # Use ValueError as a standard way to signal missing configuration
    raise ValueError("DATABASE_URL environment variable is not set! Check your .env or deployment settings.")
    
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CRITICAL: Flask secret key for session security
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("FLASK_SECRET_KEY environment variable is not set! Check your .env or deployment settings.")

# REQUIRED: The secret key for authorizing deletions (Read from environment)
DELETE_KEY = os.environ.get('DELETE_KEY')

db = SQLAlchemy(app)

# --- DATABASE MODEL ---

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, unique=True) 
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 

# --- FLASK ROUTES ---

@app.route('/')
def index():
    # Explicitly using app context for database queries in serverless
    with app.app_context():
        posts = BlogPost.query.order_by(desc(BlogPost.created_at)).all()
        return render_template('index.html', posts=posts)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        post_title = request.form['title']
        post_content = request.form['content']

        with app.app_context():
            existing_post = BlogPost.query.filter_by(title=post_title).first()
            
            if existing_post:
                flash(f'A blog post with the title "{post_title}" already exists. Please choose a unique title.', 'danger')
                return redirect(url_for('add'))
            
            new_post = BlogPost(
                title=post_title,
                content=post_content
            )
            try:
                db.session.add(new_post)
                db.session.commit()
                flash('New blog post successfully created!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while saving the post.', 'danger')
                print(f"Database error: {e}")
                return redirect(url_for('add'))
            
    return render_template('add_post.html')

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    with app.app_context():
        post = db.get_or_404(BlogPost, post_id)
        return render_template('post_detail_page.html', post=post)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit(post_id):
    with app.app_context():
        post = db.get_or_404(BlogPost, post_id)
        
        if request.method == 'POST':
            new_title = request.form['title']
            new_content = request.form['content']

            existing_post = BlogPost.query.filter(
                BlogPost.title == new_title, 
                BlogPost.id != post_id
            ).first()

            if existing_post:
                flash(f'A post with the title "{new_title}" already exists.', 'danger')
                return redirect(url_for('edit', post_id=post_id))

            post.title = new_title
            post.content = new_content
            
            try:
                db.session.commit()
                flash('Blog post successfully updated!', 'success')
                return redirect(url_for('post_detail', post_id=post.id))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while saving changes.', 'danger')
                print(f"Database error: {e}")
                return redirect(url_for('edit', post_id=post_id))
            
    # Renders the new edit_post.html template
    return render_template('edit_post.html', post=post) 


@app.route('/delete/<int:post_id>', methods=['POST'])
def delete(post_id):
    with app.app_context():
        post = db.get_or_404(BlogPost, post_id)
        
        # --- AUTHORIZATION CHECK ---
        submitted_key = request.form.get('admin_key')
        
        if DELETE_KEY is None:
            flash('Configuration error: The DELETE_KEY environment variable is not set on the server.', 'warning')
            return redirect(url_for('post_detail', post_id=post_id))
            
        if submitted_key != DELETE_KEY:
            flash('Authorization failed. The provided key is incorrect.', 'danger')
            return redirect(url_for('post_detail', post_id=post_id))

        # If the key is correct, proceed with deletion
        try:
            db.session.delete(post)
            db.session.commit()
            flash(f'Post "{post.title}" successfully deleted!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during deletion.', 'danger')
            print(f"Database error on delete: {e}")
            return redirect(url_for('post_detail', post_id=post_id))

# NOTE: The 'if __name__ == "__main__":' block for local development 
# has been REMOVED as it can conflict with the production Gunicorn server setup.
# Database table creation is handled by 'db_setup.py' during the Vercel build.