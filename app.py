import os
import re
import json
import random
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage

from google.cloud.firestore import SERVER_TIMESTAMP

# =======================================================
# == KONFIGURASI APLIKASI ==
# =======================================================
app = Flask(__name__)
app.secret_key = 'rahasia-negara-kingg-ganti-ini-ya'

# =======================================================
# == BANK SOAL IOT (20 SOAL) ==
# =======================================================
FULL_QUESTION_BANK = [
    {'id': 1, 'pertanyaan': 'Apa kepanjangan dari IoT?', 'opsi': ['Internet of Technology', 'Internet of Things', 'Intranet of Things', 'Input of Tools'], 'jawaban': 'Internet of Things'},
    {'id': 2, 'pertanyaan': 'Komponen otak dari Arduino Uno adalah?', 'opsi': ['ATmega328P', 'ESP8266', 'Resistor', 'LED'], 'jawaban': 'ATmega328P'},
    {'id': 3, 'pertanyaan': 'Sensor DHT11 berfungsi mengukur?', 'opsi': ['Jarak', 'Cahaya', 'Suhu & Kelembaban', 'Gerakan'], 'jawaban': 'Suhu & Kelembaban'},
    {'id': 4, 'pertanyaan': 'Tegangan operasi standar ESP8266/ESP32 adalah?', 'opsi': ['5V', '3.3V', '12V', '9V'], 'jawaban': '3.3V'},
    {'id': 5, 'pertanyaan': 'Protokol komunikasi ringan yang populer untuk IoT adalah?', 'opsi': ['HTTP', 'FTP', 'MQTT', 'SMTP'], 'jawaban': 'MQTT'},
    {'id': 6, 'pertanyaan': 'Apa fungsi dari Relay?', 'opsi': ['Mengukur suhu', 'Saklar elektronik beban tinggi', 'Memancarkan WiFi', 'Menyimpan data'], 'jawaban': 'Saklar elektronik beban tinggi'},
    {'id': 7, 'pertanyaan': 'Pin pada Arduino yang mendukung PWM ditandai dengan simbol?', 'opsi': ['~ (Tilde)', '# (Tag)', '* (Bintang)', '+ (Plus)'], 'jawaban': '~ (Tilde)'},
    {'id': 8, 'pertanyaan': 'Manakah yang merupakan Single Board Computer (Mini PC)?', 'opsi': ['Arduino Uno', 'Raspberry Pi', 'NodeMCU', 'Sensor PIR'], 'jawaban': 'Raspberry Pi'},
    {'id': 9, 'pertanyaan': 'Kaki Anoda pada LED harus dihubungkan ke?', 'opsi': ['Ground (GND)', 'VCC / Positif', 'Pin Reset', 'Pin Analog'], 'jawaban': 'VCC / Positif'},
    {'id': 10, 'pertanyaan': 'Apa fungsi resistor pada rangkaian LED?', 'opsi': ['Menambah terang', 'Membatasi arus', 'Mengubah warna', 'Mematikan LED'], 'jawaban': 'Membatasi arus'},
    {'id': 11, 'pertanyaan': 'Sistem bilangan yang hanya terdiri dari 0 dan 1 disebut?', 'opsi': ['Desimal', 'Heksadesimal', 'Biner', 'Oktal'], 'jawaban': 'Biner'},
    {'id': 12, 'pertanyaan': 'Library Arduino untuk mengontrol servo motor adalah?', 'opsi': ['Servo.h', 'Motor.h', 'Wire.h', 'SPI.h'], 'jawaban': 'Servo.h'},
    {'id': 13, 'pertanyaan': 'Platform IoT Dashboard yang populer (Drag & Drop) adalah?', 'opsi': ['Blynk', 'Notepad', 'Paint', 'Word'], 'jawaban': 'Blynk'},
    {'id': 14, 'pertanyaan': 'Sensor HC-SR04 menggunakan gelombang apa?', 'opsi': ['Ultrasonik', 'Inframerah', 'Radio', 'Mikro'], 'jawaban': 'Ultrasonik'},
    {'id': 15, 'pertanyaan': 'Istilah "GPIO" singkatan dari?', 'opsi': ['General Purpose Input Output', 'Global Position Input Output', 'General Power In Out', 'Graphic Processing Input Output'], 'jawaban': 'General Purpose Input Output'},
    {'id': 16, 'pertanyaan': 'Berapa baud rate standar untuk Serial Monitor?', 'opsi': ['9600', '100', '5000', '1M'], 'jawaban': '9600'},
    {'id': 17, 'pertanyaan': 'Kabel jumper Male-to-Female digunakan untuk menghubungkan?', 'opsi': ['Arduino ke Breadboard', 'Sensor ke Breadboard', 'Pin Header ke Breadboard', 'Sesama kabel'], 'jawaban': 'Pin Header ke Breadboard'},
    {'id': 18, 'pertanyaan': 'Apa itu "Sketch" dalam Arduino IDE?', 'opsi': ['Gambar Rangkaian', 'Program/Kodingan', 'Library', 'Monitor Serial'], 'jawaban': 'Program/Kodingan'},
    {'id': 19, 'pertanyaan': 'LDR (Light Dependent Resistor) berubah nilainya berdasarkan?', 'opsi': ['Suhu', 'Cahaya', 'Suara', 'Getaran'], 'jawaban': 'Cahaya'},
    {'id': 20, 'pertanyaan': 'Fungsi void setup() pada Arduino berjalan berapa kali?', 'opsi': ['Berkali-kali (Loop)', 'Hanya sekali saat awal', 'Setiap 1 detik', 'Tidak tentu'], 'jawaban': 'Hanya sekali saat awal'}
]

# =======================================================
# == INISIALISASI FIREBASE ==
# =======================================================
try:
    if not firebase_admin._apps:
        # MENGGUNAKAN FILE KUNCI ASLI
        cred = credentials.Certificate('serviceAccountKey.json')
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'cloud-saya.appspot.com' 
        })
        
    db = firestore.client()
    bucket = storage.bucket()
except Exception as e:
    print(f"CRITICAL ERROR: Gagal inisialisasi Firebase. {e}")

# =======================================================
# == DECORATORS & HELPERS ==
# =======================================================
@app.context_processor
def inject_user_data():
    return dict(is_admin=session.get('is_admin', False), user_email=session.get('user_email', 'Tamu'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('firebase_token'): return redirect(url_for('login_form'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'): 
            return redirect(url_for('project_list')) 
        return f(*args, **kwargs)
    return decorated_function

def generate_search_fields(nama):
    lower = nama.lower()
    keywords = list(set(re.sub(r'[^\w\s]', '', lower).split()))
    return lower, [k for k in keywords if k]

# =======================================================
# == AUTH ROUTES (SUDAH DIPERBAIKI JAMNYA) ==
# =======================================================
@app.route('/login')
def login_form():
    if session.get('firebase_token'): return redirect(url_for('project_list'))
    return render_template('login.html')

@app.route('/register')
def register_form():
    return render_template('register.html')

@app.route('/session-login', methods=['POST'])
def session_login():
    try:
        id_token = request.json['idToken']
        
        # --- PERBAIKAN UTAMA DI SINI ---
        # clock_skew_seconds=10 artinya:
        # "Kalau jam laptop beda maksimal 10 detik dari jam server, anggap SAH."
        decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=10)
        # -------------------------------
        
        uid = decoded_token['uid']
        
        # LOGIKA ROLE ADMIN
        user_doc = db.collection('users').document(uid).get()
        is_admin = False
        if user_doc.exists:
            user_data = user_doc.to_dict()
            if user_data.get('role') == 'admin':
                is_admin = True
        
        session['firebase_token'] = id_token
        session['user_uid'] = uid
        session['user_email'] = decoded_token.get('email', '')
        session['is_admin'] = is_admin 
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print("\n" + "="*50)
        print(f"🔥 PENYEBAB ERROR: {e}")
        print("="*50 + "\n")
        return jsonify({"status": "error", "message": str(e)}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_form'))

# =======================================================
# == SETTINGS ROUTE ==
# =======================================================
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user_uid = session.get('user_uid')
    try: user_record = auth.get_user(user_uid)
    except: return redirect(url_for('logout'))

    msg, msg_type = None, None

    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'update_profile':
                new_name = request.form.get('display_name')
                new_email = request.form.get('email')
                foto = request.files.get('foto_profil')
                update_data = {}
                if new_name and new_name != user_record.display_name: update_data['display_name'] = new_name
                if new_email and new_email != user_record.email: update_data['email'] = new_email
                if foto and foto.filename:
                    blob = bucket.blob(f"profile_pics/{user_uid}_{int(datetime.now().timestamp())}.jpg")
                    blob.upload_from_file(foto, content_type=foto.content_type)
                    blob.make_public()
                    update_data['photo_url'] = blob.public_url
                if update_data:
                    auth.update_user(user_uid, **update_data)
                    msg, msg_type = "Profil berhasil diperbarui!", "success"
                    user_record = auth.get_user(user_uid)

            elif action == 'change_password':
                new_pass = request.form.get('new_password')
                if len(new_pass) < 6: msg, msg_type = "Password min 6 karakter.", "error"
                else: auth.update_user(user_uid, password=new_pass); msg, msg_type = "Password berhasil diganti.", "success"
            
            elif action == 'delete_account':
                if request.form.get('confirm_email') == user_record.email: auth.delete_user(user_uid); session.clear(); return redirect(url_for('login_form'))
                else: msg, msg_type = "Email konfirmasi salah.", "error"
        except Exception as e: msg, msg_type = f"Gagal: {str(e)}", "error"

    return render_template('settings.html', user=user_record, msg=msg, msg_type=msg_type)

# =======================================================
# == MAIN ROUTES ==
# =======================================================
@app.route('/')
def home(): return redirect(url_for('project_list'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_uid = session.get('user_uid')
    try:
        user_record = auth.get_user(user_uid)
        ts = user_record.user_metadata.creation_timestamp / 1000 if user_record.user_metadata.creation_timestamp else 0
        tgl_gabung = datetime.fromtimestamp(ts).strftime('%d %B %Y') if ts else "N/A"
        user_profile = {'display_name': user_record.display_name or 'User IoT', 'email': user_record.email, 'photo_url': user_record.photo_url, 'created_at': tgl_gabung}
        
        bookmarks = db.collection('users').document(user_uid).collection('bookmarks').stream()
        ids = [doc.id for doc in bookmarks]
        daftar_proyek = []
        if ids:
            refs = [db.collection('proyekIoT').document(pid) for pid in ids]
            docs = db.get_all(refs)
            daftar_proyek = [{'id': d.id, 'data': d.to_dict()} for d in docs if d.exists]

        return render_template('dashboard.html', user_profile=user_profile, daftar_proyek=daftar_proyek)
    except Exception as e: return f"Error Dashboard: {e}"

@app.route('/projects')
@login_required
def project_list():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 12
        search_term = request.args.get('search_query', '').lower()
        filter_kategori = request.args.get('filter_kategori', '')
        user_uid = session.get('user_uid')
        bookmarked_ids = {d.id for d in db.collection('users').document(user_uid).collection('bookmarks').stream()} if user_uid else set()

        base_query = db.collection('proyekIoT')
        if filter_kategori: base_query = base_query.where('kategori', '==', filter_kategori)
        results = {}
        has_next, has_prev = False, False

        if search_term:
            keywords = [k for k in re.sub(r'[^\w\s]', '', search_term).split() if k]
            if keywords:
                q1 = base_query.where('keywords', 'array_contains_any', keywords).limit(50)
                for d in q1.stream(): results[d.id] = d.to_dict()
            q2 = base_query.where('nama_lowercase', '>=', search_term).where('nama_lowercase', '<=', search_term + '\uf8ff').limit(50)
            for d in q2.stream(): results[d.id] = d.to_dict()
        else:
            offset = (page - 1) * per_page
            q = base_query.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(per_page + 1).offset(offset)
            docs = list(q.stream())
            has_next = len(docs) > per_page
            has_prev = page > 1
            if has_next: docs = docs[:per_page]
            for d in docs: results[d.id] = d.to_dict()

        daftar_proyek = [{'id': i, 'data': d} for i, d in results.items()]
        return render_template('project_list.html', daftar_proyek=daftar_proyek, search_term=search_term, filter_kategori=filter_kategori, bookmarked_ids=bookmarked_ids, page=page, has_next=has_next, has_prev=has_prev)
    except Exception as e: return f"Database Error: {e}", 500

@app.route('/proyek/<project_id>')
@login_required
def project_detail(project_id):
    doc = db.collection('proyekIoT').document(project_id).get()
    if not doc.exists: return "Proyek tidak ditemukan", 404
    data = doc.to_dict()
    user_uid = session.get('user_uid')
    
    is_bookmarked = db.collection('users').document(user_uid).collection('bookmarks').document(project_id).get().exists
    rating_doc = db.collection('proyekIoT').document(project_id).collection('ratings').document(user_uid).get()
    user_rating = rating_doc.to_dict()['rating'] if rating_doc.exists else 0
    komentar = [{'id': k.id, 'data': k.to_dict()} for k in db.collection('proyekIoT').document(project_id).collection('komentar').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()]

    return render_template('project_detail.html', proyek={'id': doc.id, 'data': data}, daftar_komentar=komentar, is_bookmarked=is_bookmarked, user_rating=user_rating, avg_rating=data.get('avg_rating', 0), num_ratings=data.get('num_ratings', 0))

# =======================================================
# == ACTION ROUTES ==
# =======================================================
@app.route('/toggle_bookmark/<project_id>', methods=['POST'])
@login_required
def toggle_bookmark(project_id):
    uid = session.get('user_uid')
    ref = db.collection('users').document(uid).collection('bookmarks').document(project_id)
    if ref.get().exists: ref.delete()
    else: ref.set({'timestamp': SERVER_TIMESTAMP})
    return redirect(request.referrer)

@app.route('/proyek/<project_id>/add_comment', methods=['POST'])
@login_required
def add_comment(project_id):
    txt = request.form.get('komentar_teks')
    if txt: db.collection('proyekIoT').document(project_id).collection('komentar').add({'teks': txt, 'user_email': session.get('user_email'), 'timestamp': SERVER_TIMESTAMP})
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/proyek/<project_id>/add_rating', methods=['POST'])
@login_required
def add_rating(project_id):
    try:
        rating = int(request.form.get('rating'))
        user_uid = session.get('user_uid')
        doc_ref = db.collection('proyekIoT').document(project_id)
        doc_ref.collection('ratings').document(user_uid).set({'rating': rating})
        
        ratings_stream = doc_ref.collection('ratings').stream()
        total, count = 0, 0
        for r in ratings_stream: total += r.to_dict().get('rating', 0); count += 1
        avg = total / count if count > 0 else 0
        doc_ref.update({'avg_rating': round(avg, 1), 'num_ratings': count})
    except Exception as e: print(f"Error Add Rating: {e}")
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    if request.method == 'POST':
        score, details, count = 0, [], 0
        for q in FULL_QUESTION_BANK:
            ans = request.form.get(f"q_{q['id']}")
            if ans:
                count += 1
                correct = (ans == q['jawaban'])
                if correct: score += 1
                details.append({'pertanyaan': q['pertanyaan'], 'jawaban_user': ans, 'jawaban_benar': q['jawaban'], 'is_correct': correct})
        final = (score / count) * 100 if count > 0 else 0
        return render_template('quiz_result.html', nilai=final, hasil=details)
    return render_template('quiz.html', questions=random.sample(FULL_QUESTION_BANK, 5))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        db.collection('pesan_kontak').add({'nama': request.form['nama'], 'email': request.form['email'], 'pesan': request.form['pesan'], 'timestamp': SERVER_TIMESTAMP})
        return render_template('contact.html', success=True)
    return render_template('contact.html', user_email=session.get('user_email', ''))

# =======================================================
# == ADMIN ROUTES (CRUD & DASHBOARD) ==
# =======================================================
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    docs = db.collection('proyekIoT').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    proyek_list = [{'id': d.id, 'data': d.to_dict()} for d in docs]
    return render_template('admin_dashboard.html', proyek_list=proyek_list)

@app.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_project_form():
    if request.method == 'POST':
        nama = request.form['nama_proyek']
        lower, keys = generate_search_fields(nama)
        db.collection('proyekIoT').add({
            'nama': nama, 'kategori': request.form['kategori'],
            'deskripsi_singkat': request.form['deskripsi_singkat'],
            'alat_bahan': request.form['alat_bahan'],
            'tutorial_lengkap': request.form['tutorial_lengkap'],
            'source_code': request.form['source_code'],
            'nama_lowercase': lower, 'keywords': keys, 'avg_rating': 0, 'num_ratings': 0, 'timestamp': SERVER_TIMESTAMP
        })
        return redirect(url_for('admin_dashboard'))
    return render_template('add_project.html')

@app.route('/edit/<project_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_project(project_id):
    ref = db.collection('proyekIoT').document(project_id)
    doc = ref.get()
    if not doc.exists: return "Proyek tidak ditemukan", 404

    if request.method == 'POST':
        nama = request.form['nama_proyek']
        lower, keys = generate_search_fields(nama)
        update_data = {
            'nama': nama, 'kategori': request.form['kategori'],
            'deskripsi_singkat': request.form['deskripsi_singkat'],
            'alat_bahan': request.form['alat_bahan'],
            'tutorial_lengkap': request.form['tutorial_lengkap'],
            'source_code': request.form['source_code'],
            'nama_lowercase': lower, 'keywords': keys
        }
        if 'image_file' in request.files:
            foto = request.files['image_file']
            if foto.filename:
                blob = bucket.blob(f"project_images/{project_id}_{int(datetime.now().timestamp())}.jpg")
                blob.upload_from_file(foto, content_type=foto.content_type)
                blob.make_public()
                update_data['image_url'] = blob.public_url
        ref.update(update_data)
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_project.html', proyek={'id': doc.id, 'data': doc.to_dict()})

@app.route('/delete_project/<project_id>', methods=['POST'])
@login_required
@admin_required
def delete_project_action(project_id):
    db.collection('proyekIoT').document(project_id).delete()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)