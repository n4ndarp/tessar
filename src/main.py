import io
import os
import regex as re
import pandas as pd
import schemas
import json
from google.cloud import vision, storage
from google.protobuf.json_format import MessageToJson
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from auth import AuthHandler
from src.seledri import text_detectz
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:9000",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@CsrfProtect.load_config
def get_csrf_config():
  return schemas.CsrfSettings()

auth_handler = AuthHandler()
users = []
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] ='x.json'

def upload_image(image_file, image_name):
    client = storage.Client()
    bucket = client.bucket("xzuiko")
    blob = bucket.blob(image_name)
    blob.upload_from_file(image_file)
    return f"gs://{bucket.name}/{blob.name}"

def delete_image(image_name):
    client = storage.Client()
    bucket = client.bucket("xzuiko")
    blob = bucket.blob(image_name)
    blob.delete()

def detect_text(image_path):
    client = vision.ImageAnnotatorClient()
    img_p = vision.Image()
    img_p.source.image_uri = image_path
    response = client.document_text_detection(image=img_p, image_context={"language_hints": ["id"]})
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
        line = re.sub(r'\d{12,16}|^PROVINSI.*|^(KOTA|KABUPATEN).*', '', line, flags=re.IGNORECASE)
        #line = re.sub(r'\d{12,16}|^PROVINSI.*|^(KOTA|KABUPATEN).*|gol. darah|nik|kewarganegaraan|nama|status perkawinan|berlaku hingga|alamat|agama|tempat/tgl lahir|jenis kelamin|gol darah|rt/rw|kel|desa|kecamatan|pekerjaan|:', '', line, flags=re.IGNORECASE)
        line = re.sub(r'\b(?e)(?:nik|kewarganegaraan|nama|status perkawinan|status|perkawinan|berlaku hingga|berlaku|hingga|alamat|agama|tempat/tgl lahir|jenis kelamin|rt/rw|kel/desa|kel|desa|kecamatan|pekerjaan){e<=1}\b', '', line, flags=re.IGNORECASE)
        line = re.sub(r'.*?(WNI|WNA)', r'\1', line, flags=re.IGNORECASE)
        line = re.sub(r'^.\s+|^\s+|\s+$', '', line, flags=re.IGNORECASE|re.BESTMATCH, count=3)
        line = re.sub(r'^.\s+|^\s+|\s+$', '', line, flags=re.IGNORECASE|re.BESTMATCH, count=3)
        line = re.sub(r'^.{0,2}$', '', line, flags=re.IGNORECASE)
        """
        ^.{0,2}$|\d{12,16}|\b\S*[^\w\s]\S*\b|:
        """
        if line != "":
            temp.append(line)
            #print(line)
    pretemp = temp
    #Final position checks
    df = pd.read_csv('keldesnew.csv')
    kec_file = pd.read_csv('kec.csv')
    kerj_file = pd.read_csv('pekerjaan.csv')
    for i, elem in enumerate(temp):
        if re.match(r'^[A-Za-z]+,\s\d{2}-\d{2}-\d{4}$', elem):
            print(i,elem)
            if i == 4:
                break
            else:
                t = temp[4]
                temp[4] = elem
                temp[i] = t
                break

    for i, elem in enumerate(temp):
        if re.match(r'\b(?e)(?:LAKI-LAKI|PEREMPUAN){e<=4}\b', elem, re.BESTMATCH | re.IGNORECASE):
            print(i,elem)
            if i == 5:
                break
            else:
                t = temp[5]
                temp[5] = elem
                temp[i] = t
                break

    for i, elem in enumerate(temp):
        if re.match(r"\b(?e)(?:Gol\. Darah\s+([ABO0]|AB)){e<=2}", elem, re.IGNORECASE):
            print(i,elem)
            if i == 6:
                temp[6] = re.sub(r"\b(?e)(?:Gol\. Darah){e<=2}", '', elem, re.IGNORECASE).strip()
                break
            else:
                t = temp[6]
                temp[6] = re.sub(r"\b(?e)(?:Gol\. Darah){e<=2}", '', elem, re.IGNORECASE).strip()
                temp[i] = t
                break

    pattern = r'^\d{3}/\d{3}$'
    fuzzy_pattern = fr'({pattern}){{e<=2}}'
    for i, elem in enumerate(temp):
        if re.match(fuzzy_pattern, elem, re.IGNORECASE):
            print(i,elem)
            if i == 9:
                break
            else:
                t = temp[9]
                temp[9] = elem
                temp[i] = t
                break

    for i, elem in enumerate(temp):
        if (df['KELDES'].str.lower().str.strip() == elem.lower().strip()).any() == True:
            print(i,elem)
            if i == 10:
                break
            else:
                t = temp[10]
                temp[10] = elem
                temp[i] = t
                break

    for i, elem in enumerate(temp):
        if (kec_file['KECAMATAN'].str.lower().str.strip() == elem.lower().strip()).any() == True:
            print(i,elem)
            if i == 11:
                break
            else:
                brtahan = temp[11]
                temp[11] = elem
                temp[i] = brtahan
                break
    
    for i, elem in enumerate(temp):
        if re.match(r'\b(?:ISLAM|KRISTEN|KATOLIK|BUDHA|HINDU|KONGHUCU){e<=2}\b', elem, re.BESTMATCH | re.IGNORECASE):
            print(i,elem)
            if i == 12:
                break
            else:
                t = temp[12]
                temp[12] = elem
                temp[i] = t
                break

    for i, elem in enumerate(temp):
        if re.match(r'\b(?e)(?:KAWIN|BELUM KAWIN|CERAI HIDUP|CERAI MATI){e<=2}\b', elem, re.BESTMATCH|re.IGNORECASE):
            print(i,elem)
            if i == 13:
                break
            else:
                t = temp[13]
                temp[13] = elem
                temp[i] = t
                break

    for i, elem in enumerate(temp):
        if (kerj_file['PEKERJAAN'].str.lower().str.strip() == elem.lower().strip()).any() == True:
            print(i,elem)
            if i == 14:
                break
            else:
                brtahan = temp[14]
                temp[14] = elem
                temp[i] = brtahan
                break

    for i, elem in enumerate(temp):
        if re.match(r'\b(?e)(?:WNI|WNA){e<=1}\b', elem, re.BESTMATCH|re.IGNORECASE):
            print(i,elem)
            if i == 15:
                break
            else:
                t = temp[15]
                temp[15] = elem
                temp[i] = t
                break

    for i, elem in enumerate(temp):
        if re.match(r'\b(?e)(?:SEUMUR HIDUP){e<=4}\b', elem, re.BESTMATCH|re.IGNORECASE):
            print(i,elem)
            if i == 16:
                break
            else:
                t = temp[16]
                temp[16] = elem
                temp[i] = t
                break
    
    final_data = {
        "nik": temp[0],
        "nama": temp[3],
        "ttl": temp[4],
        "kelamin": temp[5],
        "gol. darah": temp[6],
        "alamat": temp[7],
        "rt_rw": temp[9],
        "kelurahan": temp[10],
        "kecamatan": temp[11],
        "kotakab": temp[2],
        "provinsi": temp[1],
        "agama": temp[12],
        "status": temp[13],
        "pekerjaan": temp[14],
        "kewarganegaraan": temp[15],
        "masa_berlaku": temp[16]
    }
    return final_data

def detect_testbed(img_path):
    client = vision.ImageAnnotatorClient()
    img_p = vision.Image()
    img_p.source.image_uri = img_path
    response = client.document_text_detection(image=img_p, image_context={"language_hints": ["id"]})
    data = response.text_annotations
    return(data)

@app.get("/csrftoken")
async def get_csrf_token(csrf_protect:CsrfProtect = Depends()):
	response = JSONResponse(status_code=200, content={'csrf_token':'cookie'})
	csrf_protect.set_csrf_cookie(response)
	return response

@app.post('/register')
async def register(login: schemas.Pengguna, request: Request, csrf_protect:CsrfProtect = Depends()):
    csrf_protect.validate_csrf_in_cookies(request)
    if any(x['username'] == login.username for x in users):
        raise HTTPException(status_code=400, detail='Username sudah ada')
    hashed_pass = auth_handler.get_password_hash(login.password)
    users.append({'username': login.username, 'password': hashed_pass})
    return {'message': 'ok!'}

@app.post('/login')
def login(login: schemas.Pengguna, request: Request, csrf_protect:CsrfProtect = Depends()):
    csrf_protect.validate_csrf_in_cookies(request)
    user = None
    for x in users:
        if x['username'] == login.username:
            user = x
            break
    if (user is None) or (not auth_handler.verify_password(login.password, user['password'])):
        raise HTTPException(status_code=401, detail='Username/Password Salah')
    access_token = auth_handler.encode_token(user['username'])
    return {'access_token': access_token}

@app.get('/withoutjwt')
def notoken():
    return { 'hello': 'world' }

@app.get('/withjwt')
def withtoken(request: Request, username=Depends(auth_handler.auth_wrapper), csrf_protect:CsrfProtect = Depends()):
    csrf_protect.validate_csrf_in_cookies(request)
    return {'name': username}

@app.post("/text-detection")
async def text_detection(image: UploadFile, request: Request):
    #csrf_protect.validate_csrf_in_cookies(request)
    image_file = io.BytesIO(await image.read())
    image_name = image.filename
    image_path = upload_image(image_file, image_name)
    text = detect_text(image_path) 
    delete_image(image_name)
    return text

@app.post("/text-detection-testbed")
async def text_detectiontestbed(image: UploadFile):
    image_file = io.BytesIO(await image.read())
    image_name = image.filename
    image_path = upload_image(image_file, image_name)
    textz = detect_testbed(image_path) 
    delete_image(image_name)
    sorted_annotations = sorted(textz, key=lambda a: a.bounding_poly.vertices[0].y, reverse=True)
    sorted_descriptions = [a.description for a in sorted_annotations]
    print(sorted_descriptions)
    return sorted_descriptions

@app.post("/text-detection-seledri")
async def text_detection_seledri(image: UploadFile, request: Request, username=Depends(auth_handler.auth_wrapper), csrf_protect:CsrfProtect = Depends()):
    csrf_protect.validate_csrf_in_cookies(request)
    image_file = io.BytesIO(await image.read())
    image_name = image.filename
    image_path = upload_image(image_file, image_name)
    task = text_detectz.delay(image_path, image_name)
    while not task.ready():
        pass
    result = task.get()
    return result
    
@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(status_code=exc.status_code, content={ 'detail':  exc.message })