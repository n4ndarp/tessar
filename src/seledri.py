from celery import Celery
import pandas as pd
import re
import os
from google.cloud import vision, storage

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] ='x.json'
client_gcs = storage.Client()
client = vision.ImageAnnotatorClient()

seledri = Celery('seledri', broker='pyamqp://guest:guest@localhost:5672/vhost', backend='rpc://')
seledri.conf.update(
    task_track_started=True,
)

def upload_image(image_file, image_name):
    bucket = client_gcs.bucket("xzuiko")
    blob = bucket.blob(image_name)
    blob.upload_from_file(image_file)
    return f"gs://{bucket.name}/{blob.name}"

def delete_image(image_name):
    bucket = client_gcs.bucket("xzuiko")
    blob = bucket.blob(image_name)
    blob.delete()

def detect_text(image_path):
    client = vision.ImageAnnotatorClient()
    img_p = vision.Image()
    img_p.source.image_uri = image_path
    response = client.document_text_detection(image=img_p)
    data = response.text_annotations[0].description
    data = data.split("\n")
    temp = []
    #Filter first 3 to be NIK, Prov, Kota/Kabupaten
    for line in data:
        match = re.search(r'\d{12,16}', line)
        if match:
            temp.append(match.group())
    for line in data:
        match = re.search(r'^PROVINSI.*', line)
        if match:
            temp.append(match.group())
    for line in data:
        match = re.search(r'^(KOTA|KABUPATEN).*', line)
        if match:
            temp.append(match.group())
            break
    #Filter overall accordingly
    for line in data:
        line = re.sub('\d{12,16}|^PROVINSI.*|^(KOTA|KABUPATEN).*|gol. darah|nik|kewarganegaraan|nama|status perkawinan|berlaku hingga|alamat|agama|tempat/tgl lahir|jenis kelamin|gol darah|rt/rw|kel|desa|kecamatan|pekerjaan|:', '', line, flags=re.IGNORECASE)
        line = re.sub(r'^.\s+|^\s+|\s+$', '', line, flags=re.IGNORECASE, count=3)
        line = re.sub(r'^.{0,2}$', '', line, flags=re.IGNORECASE)
        """
        ^.{0,2}$|\d{12,16}|\b\S*[^\w\s]\S*\b|:
        line = line.replace("/"," ").strip()
        line = line.replace(".","").strip()
        """
        if line != "":
            temp.append(line)
    
    #Final position checks
    df = pd.read_csv('keldesnew.csv')
    kec_file = pd.read_csv('kec.csv')
    mar_stat = ['KAWIN', 'BELUM KAWIN', 'CERAI HIDUP', 'CERAI MATI']
    for i, elem in enumerate(temp):
        if re.match(r'^[A-Za-z]+,\s\d{2}-\d{2}-\d{4}$', elem):
            t = temp[4]
            temp[4] = elem
            temp[i] = t
        elif (df['KELDES'].str.lower().str.strip() == elem.lower().strip()).any() == True:
            t = temp[9]
            temp[9] = elem
            temp[i] = t
        elif (kec_file['KECAMATAN'].str.lower().str.strip() == elem.lower().strip()).any() == True:
            brtahan = temp[10]
            temp[10] = elem
            temp[i] = brtahan
    for i, elem in enumerate(temp):
        if elem in mar_stat:
            t = temp[12]
            temp[12] = elem
            temp[i] = t

    final_data = {
        "nik": temp[0],
        "nama": temp[3],
        "ttl": temp[4],
        "alamat": temp[6]+' '+ temp[7],
        "rt_rw": temp[8],
        "kelurahan": temp[9],
        "kecamatan": temp[10],
        "kotakab": temp[2],
        "provinsi": temp[1],
        "agama": temp[11]
    }
    return final_data

@seledri.task
def text_detectz(image_path, image_name):
    print('Initialize task')
    text = detect_text(image_path)
    print('Result okeh') 
    delete_image(image_name)
    return text