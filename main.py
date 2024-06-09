from flask import Flask, render_template, request, redirect, session, url_for
import pandas as pd
import sqlite3

app = Flask(__name__)
app.secret_key = "A13Fe"

# Veritabanı bağlantısını oluşturun
def get_db_connection():
    conn = sqlite3.connect("veriler.db")
    conn.row_factory = sqlite3.Row
    return conn

# Veritabanı ve tabloların oluşturulması
def tabloyu_olustur():
    baglanti = sqlite3.connect("veriler.db")
    imlec = baglanti.cursor()

    # `kullanicilar` tablosunu oluşturun
    imlec.execute("""
    CREATE TABLE IF NOT EXISTS kullanicilar (
        ad TEXT PRIMARY KEY,
        email TEXT,
        sifre TEXT,
        kayit_tarihi TEXT
    )
    """)

    # `ekimler` tablosunu oluşturun
    imlec.execute("""
    CREATE TABLE IF NOT EXISTS ekimler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_adi TEXT,
        ekim_tarihi DATE,
        urun_adi TEXT,
        ekilen_alan REAL,
        il_ilce TEXT,
        urun_miktari REAL,
        gubreleme_tarihi DATE,
        hasat_tarihi DATE,
        hasat_miktari REAL,
        FOREIGN KEY (kullanici_adi) REFERENCES kullanicilar (ad)
    )
    """)

    # Değişiklikleri kaydedin ve bağlantıyı kapatın
    baglanti.commit()
    baglanti.close()

# Tablonun oluşturulmasını sağlayın
tabloyu_olustur()

# Veri setini okuma
data = pd.read_csv("veri_seti.csv", sep=";", encoding="ISO-8859-9")


# Ana sayfa
@app.route('/', methods=['GET', 'POST'])
def index():
    logged_in = "ad" in session
    return render_template('index.html', logged_in=logged_in)

@app.route('/amac')
def amac():
    logged_in = "ad" in session
    return render_template('amac.html', logged_in=logged_in)

@app.route("/cikis")  
def cikis():
    session.clear()
    return redirect("/login")

@app.route("/kaydol")
def kaydol():
    return render_template('kaydol.html')

@app.route("/kayitbilgileri", methods=["POST"])
def kayit():
    isim = request.form["isim"]
    email = request.form["email"]
    sifre = request.form["sifre"]

    baglanti = get_db_connection()
    sorgu = "SELECT * FROM kullanicilar WHERE ad=?"
    imlec = baglanti.cursor()
    imlec.execute(sorgu, (isim,))
    kayitlar = imlec.fetchall()
    
    if len(kayitlar) == 0:
        sorgu = "INSERT INTO kullanicilar (ad, email, sifre, kayit_tarihi) VALUES (?, ?, ?, datetime('now', 'localtime'))"
        imlec.execute(sorgu, (isim, email, sifre))
        baglanti.commit()
        session["ad"] = isim  # Kullanıcı kaydolduktan sonra oturum açılır
        return redirect("/")
    else:
        return render_template("kaydol.html", hata="Bu kullanıcı zaten kayıtlı")

@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/takvim")
def takvim():
    return render_template('takvim.html')

@app.route("/loginbilgileri", methods=["POST"])
def login_kontrol():
    isim = request.form["isim"]
    sifre = request.form["sifre"]

    baglanti = get_db_connection()
    sorgu = "SELECT * FROM kullanicilar WHERE ad=? AND sifre=?"
    imlec = baglanti.cursor()
    imlec.execute(sorgu, (isim, sifre))
    kayitlar = imlec.fetchall()
    baglanti.close()
    
    if len(kayitlar) == 0:
        return render_template("login.html", hata="Kullanıcı bilgileri hatalı")
    else:
        session["ad"] = isim
        return redirect("/")

@app.route('/profil', methods=['GET', 'POST'])
def profil():
    if "ad" not in session:
        return redirect("/login")

    kullanici_adi = session['ad']
    conn = get_db_connection()
    kullanici_bilgileri = conn.execute('SELECT ad, kayit_tarihi FROM kullanicilar WHERE ad = ?', (kullanici_adi,)).fetchone()
    ekim_bilgileri = conn.execute('SELECT id, ekim_tarihi, urun_adi, ekilen_alan, il_ilce, urun_miktari, gubreleme_tarihi, hasat_tarihi, hasat_miktari FROM ekimler WHERE kullanici_adi = ?', (kullanici_adi,)).fetchall()
    conn.close()

    return render_template('profil.html', kullanici_bilgileri=kullanici_bilgileri, ekim_bilgileri=ekim_bilgileri, logged_in=True)

@app.route('/ekim_sil/<int:ekim_id>', methods=['POST'])
def ekim_sil(ekim_id):
    if 'ad' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM ekimler WHERE id = ?', (ekim_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('profil'))

@app.route('/ekim_guncelle/<int:ekim_id>', methods=['GET', 'POST'])
def ekim_guncelle(ekim_id):
    if 'ad' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    ekim = conn.execute('SELECT * FROM ekimler WHERE id = ?', (ekim_id,)).fetchone()
    conn.close()
    
    if request.method == 'POST':
        ekim_tarihi = request.form['ekim_tarihi']
        urun_adi = request.form['urun_adi']
        ekilen_alan = request.form['ekilen_alan']
        il_ilce = request.form['il_ilce']
        urun_miktari = request.form['urun_miktari']
        gubreleme_tarihi = request.form.get('gubreleme_tarihi')
        hasat_tarihi = request.form.get('hasat_tarihi')
        hasat_miktari = request.form.get('hasat_miktari')
        
        conn = get_db_connection()
        conn.execute('UPDATE ekimler SET ekim_tarihi = ?, urun_adi = ?, ekilen_alan = ?, il_ilce = ?, urun_miktari = ?, gubreleme_tarihi = ?, hasat_tarihi = ?, hasat_miktari = ? WHERE id = ?',
                     (ekim_tarihi, urun_adi, ekilen_alan, il_ilce, urun_miktari, gubreleme_tarihi, hasat_tarihi, hasat_miktari, ekim_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('profil'))
    
    return render_template('ekim_guncelle.html', ekim=ekim)


@app.route('/ekim_ekle', methods=['POST'])
def ekim_ekle():
    if 'ad' not in session:
        return redirect(url_for('login'))
    
    kullanici_adi = session['ad']
    ekim_tarihi = request.form['ekim_tarihi']
    urun_adi = request.form['urun_adi']
    ekilen_alan = request.form['ekilen_alan']
    il_ilce = request.form['il_ilce']
    urun_miktari = request.form['urun_miktari']
    gubreleme_tarihi = request.form.get('gubreleme_tarihi')
    hasat_tarihi = request.form.get('hasat_tarihi')
    hasat_miktari = request.form.get('hasat_miktari')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO ekimler (kullanici_adi, ekim_tarihi, urun_adi, ekilen_alan, il_ilce, urun_miktari, gubreleme_tarihi, hasat_tarihi, hasat_miktari) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                 (kullanici_adi, ekim_tarihi, urun_adi, ekilen_alan, il_ilce, urun_miktari, gubreleme_tarihi, hasat_tarihi, hasat_miktari))
    conn.commit()
    conn.close()
    
    return redirect(url_for('profil'))

@app.route('/bitki_iliski', methods=['GET', 'POST'])
def bitki_iliski():
    bitki_secenekleri = sorted(data['bitki'].unique())
    ara_baglanti_secenekleri = sorted(data['ara_baglanti'].unique())
    sonuclar = []
    selected_bitki = None
    selected_ara_baglanti = None

    if request.method == 'POST':
        selected_bitki = request.form.get('bitki')
        selected_ara_baglanti = request.form.get('ara_baglanti')
        
        filtrelenmis_veri = data[(data['bitki'] == selected_bitki) & (data['ara_baglanti'] == selected_ara_baglanti)]
        sonuclar = filtrelenmis_veri['sonuc'].tolist()

    logged_in = "ad" in session
    return render_template('bitki_iliski.html', 
                           bitki_secenekleri=bitki_secenekleri, 
                           ara_baglanti_secenekleri=ara_baglanti_secenekleri, 
                           sonuclar=sonuclar, 
                           selected_bitki=selected_bitki, 
                           selected_ara_baglanti=selected_ara_baglanti,
                           logged_in=logged_in)


aylar = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']

@app.route('/<ay>')
def ay(ay):
    return render_template(ay + '.html')


if __name__ == '__main__':
    app.run(debug=True)
