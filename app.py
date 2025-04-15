from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from mimetypes import guess_type

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


class FileMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    path = db.Column(db.String(500), nullable=False)


def get_files(sort_by='created_at', order='desc'):
    query = FileMetadata.query
    order_func = db.asc if order == 'asc' else db.desc
    if sort_by == 'name':
        query = query.order_by(order_func(FileMetadata.name))
    elif sort_by == 'size':
        query = query.order_by(order_func(FileMetadata.size))
    else:
        query = query.order_by(order_func(FileMetadata.created_at))
    return query.all()


@app.route('/')
def index():
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')
    files = get_files(sort_by, order)
    return render_template('index.html', files=files, sort_by=sort_by, order=order)


@app.route('/admin')
def admin():
    files = get_files()
    return render_template('admin.html', files=files)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('Файл не выбран!', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран!', 'error')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    new_file = FileMetadata(
        name=filename,
        size=os.path.getsize(file_path),
        mime_type=guess_type(filename)[0],
        path=file_path
    )
    db.session.add(new_file)
    db.session.commit()
    flash(f'Файл "{filename}" успешно загружен!', 'success')
    return redirect(url_for('index'))


@app.route('/admin/delete/<int:file_id>')
def delete_file(file_id):
    file = FileMetadata.query.get_or_404(file_id)
    try:
        os.remove(file.path)
        db.session.delete(file)
        db.session.commit()
        flash(f'Файл "{file.name}" успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении файла: {str(e)}', 'error')
    return redirect(url_for('admin'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)