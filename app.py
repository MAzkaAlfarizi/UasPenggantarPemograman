from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_image(image_path, output_size=(300, 300)):
    with Image.open(image_path) as img:
        img.thumbnail(output_size)
        img.save(image_path)

# Database functions
def get_db_connection():
    conn = sqlite3.connect('servants.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS servants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        class TEXT NOT NULL,
        rarity INTEGER NOT NULL,
        attack INTEGER NOT NULL,
        hp INTEGER NOT NULL,
        np_name TEXT NOT NULL,
        np_effect TEXT NOT NULL,
        image_url TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Routes
@app.route('/')
def index():
    conn = get_db_connection()
    class_stats = conn.execute('''
        SELECT class, COUNT(*) as count, 
               AVG(rarity) as avg_rarity,
               AVG(attack) as avg_attack,
               AVG(hp) as avg_hp
        FROM servants
        GROUP BY class
        ORDER BY count DESC
    ''').fetchall()
    
    top_attack = conn.execute('''
        SELECT name, class, attack 
        FROM servants 
        ORDER BY attack DESC 
        LIMIT 3
    ''').fetchall()
    conn.close()
    
    return render_template('index.html', 
                         class_stats=class_stats,
                         top_attack=top_attack)

@app.route('/servants')
def servants():
    conn = get_db_connection()
    servants = conn.execute('SELECT * FROM servants').fetchall()
    conn.close()
    return render_template('servants.html', servants=servants)

@app.route('/servant/<int:id>')
def servant_detail(id):
    conn = get_db_connection()
    servant = conn.execute('SELECT * FROM servants WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if servant is None:
        flash('Servant not found!', 'error')
        return redirect(url_for('servants'))
    
    return render_template('servant_detail.html', servant=servant)

@app.route('/add_servant', methods=['GET', 'POST'])
def add_servant():
    if request.method == 'POST':
        name = request.form['name']
        servant_class = request.form['class']
        rarity = request.form['rarity']
        attack = request.form['attack']
        hp = request.form['hp']
        np_name = request.form['np_name']
        np_effect = request.form['np_effect']
        
        image_url = ''
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{name.replace(' ', '_')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                resize_image(filepath)
                image_url = url_for('static', filename=f'uploads/{filename}')
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO servants (name, class, rarity, attack, hp, np_name, np_effect, image_url) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, servant_class, rarity, attack, hp, np_name, np_effect, image_url))
        conn.commit()
        conn.close()
        
        flash('Servant added successfully!', 'success')
        return redirect(url_for('servants'))
    
    return render_template('add_servant.html')

@app.route('/edit_servant/<int:id>', methods=['GET', 'POST'])
def edit_servant(id):
    conn = get_db_connection()
    servant = conn.execute('SELECT * FROM servants WHERE id = ?', (id,)).fetchone()
    
    if request.method == 'POST':
        name = request.form['name']
        servant_class = request.form['class']
        rarity = request.form['rarity']
        attack = request.form['attack']
        hp = request.form['hp']
        np_name = request.form['np_name']
        np_effect = request.form['np_effect']
        
        image_url = servant['image_url']
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                if servant['image_url']:
                    old_filename = servant['image_url'].split('/')[-1]
                    old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                
                filename = secure_filename(f"{name.replace(' ', '_')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                resize_image(filepath)
                image_url = url_for('static', filename=f'uploads/{filename}')
        
        conn.execute('''
            UPDATE servants 
            SET name = ?, class = ?, rarity = ?, attack = ?, hp = ?, np_name = ?, np_effect = ?, image_url = ? 
            WHERE id = ?
        ''', (name, servant_class, rarity, attack, hp, np_name, np_effect, image_url, id))
        conn.commit()
        conn.close()
        
        flash('Servant updated successfully!', 'success')
        return redirect(url_for('servant_detail', id=id))
    
    conn.close()
    return render_template('edit_servant.html', servant=servant)

@app.route('/delete_servant/<int:id>')
def delete_servant(id):
    conn = get_db_connection()
    servant = conn.execute('SELECT * FROM servants WHERE id = ?', (id,)).fetchone()
    
    if servant and servant['image_url']:
        filename = servant['image_url'].split('/')[-1]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    conn.execute('DELETE FROM servants WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Servant deleted successfully!', 'success')
    return redirect(url_for('servants'))

@app.route('/story')
def story():
    story_arcs = [
        {
            'title': 'Observer on Timeless Temple',
            'chapters': [
                'Prologue: Chaldea',
                'Singularity F: Flaming Contaminated City - Fuyuki',
                'Singularity I: Wicked Dragon Hundred Years War - Orleans',
                'Singularity II: Eternal Madness Empire - Septem',
                'Singularity III: Closed-off Sea of Flames - Okeanos',
                'Singularity IV: Death World in the City of Demonic Fog - London',
                'Singularity V: North American Myth War - E Pluribus Unum',
                'Singularity VI: Divine Realm of the Round Table - Camelot',
                'Singularity VII: Absolute Demonic Front - Babylonia',
                'Final Singularity: Grand Temple of Time - Solomon'
            ],
            'summary': 'Player berusaha menghapus 7 singularity untuk mencegah kepunahan manusia di tahun 2016.',
            'year': '2015-2016'
        },
        {
            'title': 'Epic of Remnant',
            'chapters': [
                'Prologue',
                'Subspecies Singularity I: Shinjuku - Phantom Incident',
                'Subspecies Singularity II: Agartha - Legend of the Subterranean World',
                'Subspecies Singularity III: Shimosa - The Stage of Carnage',
                'Subspecies Singularity IV: Salem - Forbidden Advent Garden'
            ],
            'summary': 'Setelah berhasil menghilangkan 7 singularty dan mencegah kepunahan manusia, Muncul beberapa singularity baru berskala kecil yang muncul di Jepang, Amerika, dan Eropa.',
            'year': '2017-2018'
        },
        {
            'title': 'Cosmos in the Lostbelt',
            'chapters': [
                'Prologue',
                'Lostbelt No. 1: Permafrost Empire - Anastasia',
                'Lostbelt No. 2: Eternal Ice Century - Götterdämmerung',
                'Lostbelt No. 3: Sinking Fantasy World - SIN',
                'Lostbelt No. 4: Genesis Destruction Cycle - Yuga Kshetra',
                'Lostbelt No. 5: Olympia - Zeus',
                'Lostbelt No. 6: Avalon le Fae - Fairy Round Table Domain',
                'Lostbelt No. 7: Nahui Mictlan - The Day the Sun Disappeared'
            ],
            'summary': 'menceritkan dunia pararel yang disebut Lostbelts yang mereprensetasikan sejarah alternatif dari kejadian beesar.',
            'year': '2018-Present'
        }
    ]
    return render_template('story.html', story_arcs=story_arcs)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)