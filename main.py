from flask import Flask, after_this_request,render_template,request,redirect,session,flash,url_for,Markup
from flask_mysqldb import MySQL
import MySQLdb.cursors
from functools import wraps
import instaloader
import pandas as pd
import time
import os
from googleapiclient.discovery import build
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from matplotlib import pyplot as plt
import seaborn as sns
from textblob import TextBlob
import pandas as pd
import re
from googletrans import Translator
import csv
import shutil
import numpy as np


app = Flask(__name__)
UPLOAD_PROFILE = 'static/scrapping'
app.config['UPLOAD_PROFILE'] = UPLOAD_PROFILE
# mysql config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'senti'
mysql = MySQL(app)


def login_not_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            flash('Login Successfully','success')
            return redirect(url_for("home"))
        else:
            return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['POST','GET'])
@login_not_required
def index():
    if request.method=='POST':
        username=request.form["username"]
        password=request.form["password"]
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("select * from user where username=%s and password=md5(%s)",(username,password))
        data=cur.fetchone()
        if data:
            session['logged_in']=True
            session['id']=data['id']
            session['name']=data['name']
            session['username']=data['username']
            session['level']=data['level']
            flash('Login Successfully','success')
            return redirect(url_for('home'))
        else:
            flash('Invalid Login. Try Again','danger')
            return redirect(url_for('index'))
    return render_template('index.html')

def is_logged_in(f):
	@wraps(f)
	def wrap(*args,**kwargs):
		if 'logged_in' in session:
			return f(*args,**kwargs)
		else:
			flash('Unauthorized, Please Login','danger')
			return redirect(url_for('index'))
	return wrap

@app.route('/home', methods=['POST','GET'])
@is_logged_in
def home():
    tittle = "Dashboard - Home"
    tittle1 = "Dashboard"
    return render_template('home.html', tittle = tittle, tittle1 = tittle1)

@app.route('/account', methods=['POST','GET'])
@is_logged_in
def account():
    tittle = "Dashboard - Account"
    tittle1 = "Account"
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        level = request.form['level']

        cur = mysql.connection.cursor()
        cur.execute('''INSERT INTO user(name,username,password,level) VALUES(%s,%s,md5(%s),%s)''',(name,username,password,level))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('account'))
    
    cur=mysql.connection.cursor()
    cur.execute(''' SELECT * FROM user ''')
    akun = cur.fetchall()
    cur.close()
    
    return render_template('user.html', tittle = tittle, tittle1 = tittle1, akun = akun)

@app.route('/account/edit', methods=['POST','GET'])
@is_logged_in
def edit():
    if request.method == 'POST':
        id = request.form.get("id", None)
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        level = request.form['level']

        cur = mysql.connection.cursor()
        cur.execute(''' 
        UPDATE user 
        SET 
            name = %s,
            username = %s,
            password = md5(%s),
            level = %s
        WHERE
            id = %s;
        ''',(name,username,password,level,id))
        mysql.connection.commit()
        return redirect(url_for('account'))

@app.route('/account/delete/<int:id>', methods=['POST','GET'])
@is_logged_in
def delete(id):
    cur=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(''' SELECT * FROM user WHERE id=%s''', (id, ))
    data = cur.fetchone()
    id = data['id']

    cur.execute('''
    DELETE 
    FROM user 
    WHERE id=%s''', (id, ))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('account'))

@app.route('/scrapping/instagram', methods=['GET', 'POST'])
@is_logged_in
def instagram_scrapping():
    
    tittle = "Dashboard - Scrapping Instagram"
    tittle1 = "Scrapping Instagram"
    file_csv = ""
    instagram = ""
    
    if request.method == 'POST':
        user_name = request.form['user_name']
        postingan = request.form['postingan']

        USER = "poseidonseal888"
        username = user_name
        L = instaloader.Instaloader(max_connection_attempts=1)
        L.load_session_from_file(USER)
        time.sleep(10)

        profile = instaloader.Profile.from_username(L.context, username)
        total_comments = 0
        for post in profile.get_posts():
            post = post.from_shortcode(L.context, postingan)
        
            comments = []
            for comment in post.get_comments():
                comments.append(comment.text.encode('ascii', 'ignore').decode('ascii'))
                for answer in comment.answers:
                    comments.append(answer.text.encode('ascii', 'ignore').decode('ascii'))

            total_comments += len(comments)
            break

        data = {"Comments": comments}
        hasil = pd.DataFrame(data, columns=['Comments'])
        timestring = time.strftime("%Y%m%d_%H%M%S")
        nama_file = os.path.join(UPLOAD_PROFILE, "Dataset_" + username + "(" + postingan + ")" + timestring + ".csv")
        hasil.to_csv(nama_file, index=False, header=True)
        file_csv = ("Dataset_" + username + "(" + postingan + ")" + timestring + ".csv")
        instagram = ['<a href="/static/scrapping/'+file_csv+'"><button type="submit" class="btn btn-primary">Save File</button></a>']
        link = ("https://www.instagram.com/p/" + postingan + "/")

        cur = mysql.connection.cursor()
        cur.execute('''INSERT INTO dataset(name_file,link,waktu,jml_komen,type) VALUES(%s,%s,NOW(),%s,"Instagram")''',(file_csv,link,total_comments))
        mysql.connection.commit()
        cur.close()

        flash('Data berhasil disimpan!', 'success')
        return redirect(url_for('instagram_scrapping'))

    cur=mysql.connection.cursor()
    cur.execute(''' SELECT * FROM dataset WHERE type="Instagram" ''')
    dataset = cur.fetchall()
    cur.close()

    return render_template('instagram_scrapping.html', tittle = tittle, tittle1 = tittle1, instagram = instagram, dataset=dataset)

@app.route('/scrapping/youtube', methods=['GET', 'POST'])
@is_logged_in
def youtube_scrapping():
    tittle = "Dashboard - Scrapping Youtube"
    tittle1 = "Scrapping Youtube"
    youtube_data = ""
    api_key = "AIzaSyARpEA5nl4hw7GFpGlBSO69Np6piY0h3Ho" 
    youtube = build('youtube', 'v3', developerKey=api_key)
    if request.method == 'POST':
        code_lang = request.form['idyoutube']
        total_comments = 0

        for id_code in code_lang:
            data = youtube.commentThreads().list(part='snippet', videoId=code_lang, textFormat="plainText").execute()
            youtubeid = []
            commentlist = []
            replieslist = []

            for i in data["items"]:
                comment = i["snippet"]['topLevelComment']["snippet"]["textDisplay"]
                replies = i["snippet"]['totalReplyCount']

                youtubeid.append(id_code)    
                commentlist.append(comment)
                replieslist.append(replies)

                totalReplyCount = i["snippet"]['totalReplyCount']
            
                if totalReplyCount > 0:

                    parent = i["snippet"]['topLevelComment']["id"]
                
                    data2 = youtube.comments().list(part='snippet', parentId=parent,
                                            textFormat="plainText").execute()

                    for i in data2["items"]:
                        comment = i["snippet"]["textDisplay"]
                        replies = ""

                        youtubeid.append(id_code)    
                        commentlist.append(comment)
                        replieslist.append(replies)

            while ("nextPageToken" in data):
                data = youtube.commentThreads().list(part='snippet', videoId=code_lang, pageToken=data["nextPageToken"],
                                            textFormat="plainText").execute()
                                             
                for i in data["items"]:
                    comment = i["snippet"]['topLevelComment']["snippet"]["textDisplay"]
                    replies = i["snippet"]['totalReplyCount']

                    youtubeid.append(id_code)    
                    commentlist.append(comment)
                    replieslist.append(replies)

                    totalReplyCount = i["snippet"]['totalReplyCount']
            
                    if totalReplyCount > 0:

                        parent = i["snippet"]['topLevelComment']["id"]
                
                        data2 = youtube.comments().list(part='snippet', parentId=parent,
                                    textFormat="plainText").execute()

                        for i in data2["items"]:
                            comment = i["snippet"]["textDisplay"]
                            replies = ""

                            youtubeid.append(id_code)    
                            commentlist.append(comment)
                            replieslist.append(replies)
        total_comments += len(commentlist)

        data = {'Comments':commentlist}
        hasil = pd.DataFrame(data, columns= ['Comments'])
        timestring = time.strftime("%Y%m%d_%H%M%S")
        nama_file = os.path.join(UPLOAD_PROFILE, "youtube-comments" + "_" + code_lang + timestring +".csv")
        hasil.to_csv(nama_file, index=False, header=True)
        file_csv = ("youtube-comments" + "_" + code_lang + timestring +".csv")
        youtube_data = ['<a href="/static/scrapping/'+file_csv+'"><button type="submit" class="btn btn-primary">Save File</button></a>']
        link = ("https://www.youtube.com/watch?v=" + code_lang + "/")

        cur = mysql.connection.cursor()
        cur.execute('''INSERT INTO dataset(name_file,link,waktu,jml_komen,type) VALUES(%s,%s,NOW(),%s,"Youtube")''',(file_csv,link,total_comments))
        mysql.connection.commit()
        cur.close()

    cur=mysql.connection.cursor()
    cur.execute(''' SELECT * FROM dataset WHERE type="Youtube"''')
    dataset = cur.fetchall()
    cur.close()

    return render_template('youtube_scrapping.html', tittle = tittle, tittle1 = tittle1, youtube_data = youtube_data, dataset = dataset)

@app.route('/scrapping/delete/<int:id_file>', methods=['POST','GET'])
@is_logged_in
def delete_yt(id_file):
    cur=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(''' SELECT * FROM dataset WHERE id_file=%s''', (id_file, ))
    data = cur.fetchone()
    id_file = data['id_file']
    filename = data['name_file']

    os.unlink(os.path.join(UPLOAD_PROFILE, filename))
    cur.execute('''
    DELETE 
    FROM dataset 
    WHERE id_file=%s''', (id_file, ))
    mysql.connection.commit()
    cur.close()

    flash('Data berhasil Dihapus!', 'success')
    return redirect(url_for('home'))

@app.route('/analysis', methods=['GET', 'POST'])
@is_logged_in
def analysis():
    
    tittle = "Dashboard - Sentiment Analysis"
    tittle1 = "Sentiment Analysis"
    analysis_data = ['<span>1. Pilih nama file yang akan di Scrapping</span>']

    if request.method == 'POST':
        filename = request.form['filescrapp']
        data = pd.read_csv('static/scrapping/' + filename, sep='\t', quoting=csv.QUOTE_NONE)
        f = open("static/scrapping/" + filename, encoding="mbcs")

        parent_dir = 'static/analysis/'
        timestring = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(parent_dir, filename + timestring)
        os.mkdir(path)

        comment = f.read()
        word_tokens = word_tokenize(comment)
        words_list = ['@']
        word_tokens_word_list = dict([(match, len([w for w in word_tokens if match in w])) for match in words_list])
        freq_kata_1 = nltk.FreqDist(word_tokens_word_list)

        def cleanTxt(text):
            text = re.sub(r'[^\w]', ' ', str(text))
            text = re.sub(r'\d+', '', text)
            
            return text

        def textstopWords(text):
            stop_words = set(stopwords.words('english'))
            words = word_tokenize(text)
            words = [word.lower() for word in words if word.isalpha() and word.lower() not in stop_words]
            text = ' '.join(words)
            
            return text
        
        translator = Translator()
        
        data['Comments'] = data['Comments'].apply(cleanTxt)
        data['Translate'] = data['Comments'].apply(lambda x: translator.translate(x, dest='en').text)

        data['Translate'].apply(textstopWords)

        # get subjectivity
        def getSubjectivity(text):
            return TextBlob(text).sentiment.subjectivity

        def labelSubjectivity(subjectivity):
            if subjectivity == 0:
                return "Teks tersebut sangat objektif"
            elif subjectivity == 1:
                return "Teks tersebut sangat subjektif"
            else:
                if subjectivity < 0.2:
                    return "Teks tersebut sangat objektif"
                elif 0.2 <= subjectivity < 0.4:
                    return "Teks tersebut cenderung objektif"
                elif 0.4 <= subjectivity < 0.6:
                    return "Teks tersebut netral"
                elif 0.6 <= subjectivity < 0.8:
                    return "Teks tersebut cenderung subjektif"
                else:
                    return "Teks tersebut sangat subjektif"
        
        # get polarity
        def getPolarity(text):
            return TextBlob(text).sentiment.polarity

        #Columns
        data['Subjectivity'] = data['Translate'].apply(getSubjectivity)
        data['Polarity'] = data['Translate'].apply(getPolarity)

        def getAnalysis(score):
            if score < 0 :
                return 'Negative'
            elif score == 0:
                return 'Neutral'
            else:
                return 'Positive'
            
        data['Subject Label'] = data['Subjectivity'].apply(labelSubjectivity)
        data['Analysis'] = data['Polarity'].apply(getAnalysis)

        # Value Count
        senti = data['Analysis'].value_counts()
        all_senti = pd.Series(dict(senti))

        # % Percentages:
        pcomments = data[data.Analysis == 'Positive']
        pcomments = pcomments['Translate']
        positive_count = pcomments.shape[0]
        positive_percentage = round((positive_count / data.shape[0]) * 100, 1)
        result_positive = f'{positive_count} = {positive_percentage}%'

        ncomments = data[data.Analysis == 'Negative']
        ncomments = ncomments['Translate']
        negative_count = ncomments.shape[0]
        negative_percentage = round((negative_count / data.shape[0]) * 100, 1)
        result_negative = f'{negative_count} = {negative_percentage}%'

        nucomments = data[data.Analysis == 'Neutral']
        nucomments = nucomments['Translate']
        netral_count = nucomments.shape[0]
        netral_percentage = round((netral_count / data.shape[0]) * 100, 1)
        result_netral = f'{netral_count} = {netral_percentage}%'

        # Sentiment Plot
        fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(5, 6), gridspec_kw={'height_ratios': [1, 2]})

        # Plot Persentase
        percentages = [positive_percentage, negative_percentage, netral_percentage]
        labels = ['Positive', 'Negative', 'Neutral']
        ax1.pie(percentages, labels=labels, autopct='%1.1f%%', startangle=90, colors=['green', 'red', 'blue'])
        ax1.set_title('Sentiment Percentage')

        # Plot count
        senti_plot = sns.barplot(x=all_senti.index, y=all_senti.values, ax=ax2, palette={'Positive': 'green', 'Negative': 'red', 'Neutral': 'blue'})
        for i, v in enumerate(all_senti.values):
            ax2.text(i, v + 0.1, str(v), color='black', ha='center')

        ax2.set_title('Sentiment Analysis')
        ax2.set_xlabel('')
        ax2.set_ylabel('Counts')

        # Atur layout subplot
        plt.gcf().subplots_adjust(bottom=0.15)
        plt.savefig(path + '/foto1.png')

        pathimage = path + '/foto1.png'
        pathfile = path + '/analisis_' + timestring + '_' + filename
        data.to_csv(pathfile)

        cur=mysql.connection.cursor()
        cur.execute('''SELECT id_file FROM dataset WHERE name_file = %s''', (filename,))
        result = cur.fetchone()
        id_file = result[0]

        cur.execute('''INSERT INTO analisis (id_file, file_sa, grafik_sa) VALUES (%s, %s, %s)''', (id_file, pathfile, pathimage))
        id_sa = cur.lastrowid

        cur.execute('''INSERT INTO hasil_analisis (id_file, id_sa, negative, neutral, positive) VALUES (%s, %s, %s, %s, %s)''', (id_file, id_sa, result_negative, result_netral, result_positive))

        mysql.connection.commit()
        cur.close()

        analysis_data = ['<center><div class="col-row"><div class="column"><img src="'+path+'/foto1.png"></div></div></center>']
    
    cur=mysql.connection.cursor()
    cur.execute(''' SELECT * FROM dataset''')
    filedataset = cur.fetchall()
    cur.close()

    return render_template('analysis.html', tittle = tittle, tittle1 = tittle1, analysis_data = analysis_data, filedataset = filedataset)

@app.route('/hasil', methods=['GET', 'POST'])
@is_logged_in
def hasil():
    tittle = "Dashboard - Dataset Analisa Sentimen"
    tittle1 = "Dataset Analisa Sentimen"

    cur=mysql.connection.cursor()
    cur.execute(''' SELECT analisis.id_sa, dataset.name_file, dataset.link, dataset.type, analisis.file_sa, analisis.grafik_sa, hasil_analisis.negative, hasil_analisis.neutral, hasil_analisis.positive FROM dataset LEFT JOIN analisis ON dataset.id_file = analisis.id_file LEFT JOIN hasil_analisis ON hasil_analisis.id_file = dataset.id_file WHERE analisis.id_sa IS NOT NULL ''')
    datasetanalisa = cur.fetchall()
    cur.close()

    return render_template('hasil.html', tittle = tittle, tittle1 = tittle1, datasetanalisa=datasetanalisa)

@app.route('/hasil/delete/<int:id_sa>', methods=['POST','GET'])
@is_logged_in
def delete_hasil(id_sa):
    cur=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(''' SELECT * FROM analisis WHERE id_sa=%s''', (id_sa, ))
    data = cur.fetchone()
    id_sa = data['id_sa']
    folder_path = data['file_sa']

    parent_folder = os.path.dirname(folder_path)
    shutil.rmtree(parent_folder, ignore_errors=True)

    cur.execute('''
    DELETE 
    FROM analisis 
    WHERE id_sa=%s''', (id_sa, ))
    mysql.connection.commit()
    cur.close()

    flash('Data berhasil Dihapus!', 'success')
    return redirect(url_for('home'))

@app.route('/laporan/scrapping', methods=['POST','GET'])
@is_logged_in
def lapScrapping():
    tittle = "Dashboard - Laporan Scrapping"
    tittle1 = "Laporan Kinerja Scrapping"
    
    cur=mysql.connection.cursor()
    cur.execute(''' SELECT dataset.id_file, user.name, dataset.link, dataset.waktu, dataset.jml_komen, dataset.type FROM dataset JOIN user ON dataset.id = user.id ''')
    dataset = cur.fetchall()
    
    cur.execute(''' SELECT COUNT(id_file) FROM dataset ''')
    total = cur.fetchone()[0]

    cur.execute(''' SELECT name FROM user WHERE level = "admin" LIMIT 1 ''')
    admin = cur.fetchone()[0]

    cur.execute(''' SELECT COUNT(id) FROM user ''')
    count_user = cur.fetchone()[0]

    cur.execute(''' SELECT COUNT(DISTINCT user.id) FROM dataset JOIN user ON dataset.id = user.id ''')
    user_scraping_count = cur.fetchone()[0]


    mysql.connection.commit()
    cur.close()
    
    return render_template('lap_scrapping.html', tittle = tittle, tittle1 = tittle1, dataset = dataset, total=total, admin=admin, user_scraping_count=user_scraping_count, count_user=count_user)

@app.route('/laporan/analisis', methods=['POST','GET'])
@is_logged_in
def lapAnalisis():
    tittle = "Dashboard - Laporan Analisis"
    tittle1 = "Laporan Kinerja Analisis"
    
    cur=mysql.connection.cursor()
    cur.execute(''' SELECT user.name, dataset.link, hasil_analisis.positive, hasil_analisis.negative, hasil_analisis.neutral FROM analisis JOIN user ON analisis.id = user.id JOIN dataset ON dataset.id_file = analisis.id_file JOIN hasil_analisis ON hasil_analisis.id_sa = analisis.id_sa ''')
    analisis = cur.fetchall()
    
    cur.execute(''' SELECT COUNT(id_file) FROM dataset ''')
    total = cur.fetchone()[0]

    cur.execute(''' SELECT COUNT(id_sa) FROM analisis ''')
    total_analisis = cur.fetchone()[0]

    cur.execute(''' SELECT name FROM user WHERE level = "admin" LIMIT 1 ''')
    admin = cur.fetchone()[0]

    cur.execute(''' SELECT COUNT(id) FROM user ''')
    count_user = cur.fetchone()[0]

    cur.execute(''' SELECT COUNT(DISTINCT user.id) FROM analisis JOIN user ON analisis.id = user.id ''')
    user_analisis_count = cur.fetchone()[0]

    mysql.connection.commit()
    cur.close()
    
    return render_template('lap_analisis.html', tittle = tittle, tittle1 = tittle1, analisis = analisis, total=total, admin=admin, user_analisis_count=user_analisis_count, count_user=count_user, total_analisis=total_analisis)


@app.route('/logout/')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out','success')
	return redirect(url_for('index'))

if __name__ == '__main__':
    app.secret_key='8056174bos805'
    app.run(debug=True)