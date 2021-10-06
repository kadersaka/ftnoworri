from flask import Flask, jsonify
from flask_restful import Resource, Api, reqparse, abort, fields, marshal_with
from werkzeug.datastructures import FileStorage
import werkzeug.security
from werkzeug.utils import secure_filename

import boto3
import uuid
import os
from os import path
from os import remove
import botocore
from botocore.client import Config
from botocore.exceptions import ClientError

from PIL import Image
from io import BytesIO
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageEnhance
from pdf2image import convert_from_path, convert_from_bytes
#from wand.image import Image as wimage
from os.path import exists
from PyPDF2 import PdfFileReader, PdfFileWriter

import ffmpeg

#AWS_ACCESS_KEY_ID = 'AKIA3YBCFTUL3D4VTRXO'
AWS_ACCESS_KEY_ID = 'AKIA3YBCFTULVDE3ZSPJ'
#AWS_SECRET_ACCESS_KEY = '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'
AWS_SECRET_ACCESS_KEY = 'Hz1cEAra+MUv34yqjR7BqeEjTbK2kZQ3IbKwf67I'
AWS_DEFAULT_REGION = 'eu-central-1'
AWS_BUCKET = 'trust-zone'
AWS_UPLOAD_FOLDER = "secure_files/"
UPLOAD_FOLDER = './uploads'

application = Flask(__name__)
application.config.from_object(__name__)
api = Api(application)





def aws_session():
    return boto3.session.Session(aws_access_key_id=application.config['AWS_ACCESS_KEY_ID'],
                                 aws_secret_access_key=application.config['AWS_SECRET_ACCESS_KEY'],
                                 region_name=application.config['AWS_DEFAULT_REGION'])


def get_client():
    return boto3.client('s3', aws_access_key_id=application.config['AWS_ACCESS_KEY_ID'],
                        aws_secret_access_key=application.config['AWS_SECRET_ACCESS_KEY'],
                        config=Config(signature_version='s3v4'), region_name=application.config["AWS_DEFAULT_REGION"])


def make_bucket(name, acl):
    session = aws_session()
    s3_resource = session.resource('s3')
    return s3_resource.create_bucket(Bucket=name, ACL=acl, CreateBucketConfiguration={
        'LocationConstraint': 'eu-central-1'}, )


def create_presigned_url(object_name, expiration=36000):
    response = {}

    client = get_client()
    try:
        response["url"] = client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': application.config["AWS_BUCKET"],
                'Key': object_name
            },
            ExpiresIn=expiration
        )
    except Exception as error:
        response['ERROR'] = str(error)
        status_code = 400

    status_code = 200
    return response, status_code


def upload_file_obj(file, bucket, file_name):
    """
    Function to upload a file to an S3 bucket without saving it locally
    """
    s3 = get_client()
    s3.upload_fileobj(file, bucket, file_name)


def download_file(file_name):
    """
    Function to downloads a given file from an S3 bucket
    """
    print(file_name)
    session = aws_session()
    s3_resource = session.resource('s3', region_name='eu-central-1')
    output = f"secure_files/{file_name}"
    bucket = s3_resource.Bucket(application.config["AWS_BUCKET"])

    s3 = get_client()
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': application.config["AWS_BUCKET"],
            'Key': file_name
        }
    )

    return url


def list_files(bucket):
    """
    Function to list files in a given S3 bucket
    """
    s3 = get_client()
    contents = []
    for item in s3.list_objects(Bucket=bucket)['Contents']:
        contents.append(item)

    return contents


"""------------------------------------------------------------------
    #video processing
------------------------------------------------------------------"""


def upload_image(image_file):
    fic = image_file
    if fic:
        fic.save(os.path.join(application.config['UPLOAD_FOLDER'], secure_filename(fic.filename)))
    # fic.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(fic.filename)))
    # fic.save(secure_filename(fic.filename))
    a = treat_video(fic.filename)
    if a:
        return jsonify({"status": "Done"})
    return jsonify({"status": "error"})


def upload(video_file):
    fic = video_file
    if fic:
        fic.save(os.path.join(application.config['UPLOAD_FOLDER'], secure_filename(fic.filename)))

    a = treat_video(fic)
    if a:
        return jsonify({"status": "Done"})
    return jsonify({"status": "error"})


def treat_video(videofile):
    mpath = path.join(application.config['UPLOAD_FOLDER'], videofile.filename)
    opath = path.join(application.config['UPLOAD_FOLDER'], "Output_" + videofile.filename)
    resize_video(mpath, get_dimension(mpath), opath)
    return True


def get_dimension(path):
    video_streams = ffmpeg.probe(path, select_streams="v")['streams'][0]
    return video_streams['width'], video_streams['height']


def resize_video(path, size, outputname):
    response = {}
    in_mem_file = BytesIO()
    overlay_file = ffmpeg.input('./assets/logo.png').filter('scale', 20, 20)
    stream = ffmpeg.input(path).filter("scale", "{}x{}".format(int(size[0] / 5), int(size[1] / 5))).overlay(
        overlay_file.hflip(), x=int(size[0] / 30), y=int(size[1] / 30)).output(outputname)
    vid = ffmpeg.run(stream)
    # print(vid.stdout)
    print(vid)



"""------------------------------------------------------------------
    #video processing
#------------------------------------------------------------------"""


def create_watermark(image_path, final_image_path, watermark):
    response = {}
    main = Image.open(image_path)
    main_copy = Image.open(image_path)
    mark = Image.open(watermark)

    #            image = Image.open(p_file)
    #           print(type(image))

    mask = mark.convert('L').point(lambda x: min(x, 25))
    mark.putalpha(mask)

    mark_width, mark_height = mark.size
    main_width, main_height = main.size
    aspect_ratio = mark_width / mark_height
    new_mark_width = main_width * 0.25
    mark.thumbnail((new_mark_width, new_mark_width / aspect_ratio), Image.ANTIALIAS)

    tmp_img = Image.new('RGB', main.size)

    for i in range(0, tmp_img.size[0], mark.size[0]):
        for j in range(0, tmp_img.size[1], mark.size[1]):
            main.paste(mark, (i, j), mark)
            main.thumbnail((8000, 8000), Image.ANTIALIAS)
    # main.save(final_image_path, quality=100)

    in_mem_file = BytesIO()
    # in_mem_file = BytesIO(main)
    # image = Image.open(in_mem_file)
    # image.thumbnail((600, 1000))
    # main.save(in_mem_file, format="PNG")
    main.save(in_mem_file, format=main.format, filename=main.filename)
    in_mem_file.seek(0)

    try:
        relative_path = "secure_images/" + final_image_path
        s3 = get_client()
        s3.upload_fileobj(image_path, application.config['AWS_BUCKET'], relative_path)
        presigned_url = s3.generate_presigned_url('get_object', Params={'Bucket': application.config["AWS_BUCKET"],
                                                                        'Key': relative_path})

        original = {}

        original['original_filename'] = image_path.filename
        original['key'] = relative_path
        original['presigned_url'] = presigned_url
        original['generated_filename'] = image_path.filename

        response['original'] = original

        relative_path = "secure_images_copy/" + final_image_path
        s3.upload_fileobj(in_mem_file, application.config['AWS_BUCKET'], relative_path)
        presigned_url = s3.generate_presigned_url('get_object', Params={'Bucket': application.config["AWS_BUCKET"],
                                                                        'Key': relative_path})

        copy = {}
        copy['original_filename'] = image_path.filename
        copy['key'] = relative_path
        copy['presigned_url'] = presigned_url
        copy['generated_filename'] = image_path.filename

        response['copy'] = copy

        status_code = 200

        print("s3 transfert done")

        return response, status_code

    except Exception as error:
        response['ERROR'] = str(error)
        status_code = 400

        return response, status_code


"""
#------------------------------------------------------------------
   #vsalim pdf
#------------------------------------------------------------------
"""


def text2image(text):
    width = 854
    height = 480
    opacity = 0.8
    black = (200, 200, 200)
    white = (255, 255, 255)
    transparent = (0, 0, 0, 0)
    assert exists('Arial.ttf'), "Missing Font File Arial.ttf"
    font = ImageFont.truetype('Arial.ttf', 100)
    wm = Image.new('RGBA', (width, height), transparent)
    im = Image.new('RGBA', (width, height), transparent)  # Change this line too.

    draw = ImageDraw.Draw(wm)
    w, h = draw.textsize(text, font)
    draw.text(((width - w) / 2, (height - h) / 2), text, black, font)
    # draw.rotate(45)

    en = ImageEnhance.Brightness(wm)
    mask = en.enhance(1 - opacity)
    im.paste(wm, (25, 25), mask)
    return im.rotate(45)

def load_pdf(path):
    assert exists(path), "Your PDF file doesn't exist"
    return convert_from_path(path)
"""
def load_pdf2(filepath):
    assert exists(filepath), "Your PDF file doesn't exist"
    page_images = []
    with wimage(filename=filepath, resolution=200) as img:
        for page_wand_image_seq in img.sequence:
            page_wand_image = wimage(page_wand_image_seq)
            page_jpeg_bytes = page_wand_image.make_blob(format="jpeg")
            page_jpeg_data = BytesIO(page_jpeg_bytes)
            page_image = Image.open(page_jpeg_data)
            page_images.append(page_image)
    return page_images

def mark_pdf_bytes(text, pdf_file, main_width, main_heigth):
    output = '/tmp/' + get_random_name() + '.pdf'
    text_img = text2image(text)
    pdf_imgs = load_pdf2(pdf_file)
    for i in pdf_imgs:
        create_watermark2(i, text_img, [main_width, main_heigth])
    pdf_imgs[0].save(output, save_all=True, append_images=pdf_imgs[1:])
    out = open(output, 'rb').read()
    # remove(output)
    # remove(pdf_file)
    return out
"""
def create_watermark2(main, mark, main_size):
    print("starting...")
    # mask = mark.convert('L').point(lambda x: min(x, 25))
    # mark.putalpha(mask)
    mark = Image.open("assets/logo.png")
    mask = mark.convert('L').point(lambda x: min(x, 90))
    mark.putalpha(mask)

    mark_width = mark.size[0] * 3
    mark_height = mark.size[1] * 3
    # mark_width, mark_height = mark.size
    main_width, main_height = main.size
    aspect_ratio = mark_width / mark_height
    new_mark_width = main_width * 0.25
    mark.thumbnail((new_mark_width, new_mark_width / aspect_ratio), Image.ANTIALIAS)

    tmp_img = Image.new('RGB', main.size)

    for i in range(0, tmp_img.size[0], mark_width):
        for j in range(0, tmp_img.size[1], mark_height):
            main.paste(mark, (i, j), mark)
            main.thumbnail(main_size, Image.ANTIALIAS)

    in_mem_file = BytesIO()
    # in_mem_file = BytesIO(main)
    # image = Image.open(in_mem_file)
    # image.thumbnail((600, 1000))
    # main.save(in_mem_file, format="PNG")
    main.save(in_mem_file, format=main.format, filename=main.filename)
    in_mem_file.seek(0)


####################
# UTILS
####################

def get_random_name():
    return str(uuid.uuid4())


def make_temp_file(data):
    name = '/tmp/' + get_random_name() + '.pdf'
    open(name, 'wb').write(data)
    pdf = PdfFileReader(open(name, 'rb'))
    page_1 = pdf.getPage(0)
    if page_1.get('/Rotate', 0) in [90, 270]:

        return name, page_1['/MediaBox'][2], page_1['/MediaBox'][3]

    else:
        return name, page_1['/MediaBox'][3], page_1['/MediaBox'][2]


def bytes_to_image(data):
    return Image.open(BytesIO(data))


def create_random_id(filename):
    """
    Randomly generated key for file
    """
    file_ext = os.path.splitext(filename)[1]
    return ''.join([str(uuid.uuid4()), file_ext])


class CreateBucket(Resource):
    task_post_bck = reqparse.RequestParser()
    task_post_bck.add_argument('bckname', type=str, help="Task is required!", required=True, )

    def post(self):
        response = {}
        args = self.task_post_bck.parse_args()
        bcname = args["bckname"]
        return make_bucket(bcname, "public-read")


# API Endpoints
class UploadVideoFile(Resource):
    task_post = reqparse.RequestParser()
    task_post.add_argument('file', required=True, help="File is required!", type=FileStorage, location='files')
    task_post.add_argument('dir', type=str, help="Dir is required!", required=True, )

    def post(self):
        response = {}
        args = self.task_post.parse_args()
        p_file = args["file"]
        filename = secure_filename(p_file.filename)
        if filename == '':
            response['ERROR'] = "No file name was provided!"
            return response, 400
        else:
            # upload(p_file)
            fname = create_random_id(p_file.filename)
            fic = p_file
            if fic:
                fic.save(os.path.join(application.config['UPLOAD_FOLDER'], "original_" + fname))

            # a = treat_video(fic)
            try:
                mpath = path.join(application.config['UPLOAD_FOLDER'], "original_" + fname)
                opath = path.join(application.config['UPLOAD_FOLDER'], fname)
                # return resize_video(mpath, get_dimension(mpath), opath)
                m_size = get_dimension(mpath)

                overlay_file = ffmpeg.input('./assets/logo.png').filter('scale', 20, 20)
                stream = ffmpeg.input(mpath).filter("scale",
                                                    "{}x{}".format(int(m_size[0] / 5), int(m_size[1] / 5))).overlay(
                    overlay_file.hflip(), x=int(m_size[0] / 30), y=int(m_size[1] / 30)).output(opath)
                vid = ffmpeg.run(stream)
                # print(vid.stdout)
                print(vid)

                final_image_path = fname

                relative_path = "copies_videos/" + final_image_path
                s3 = get_client()
                s3.upload_file(mpath, application.config['AWS_BUCKET'], relative_path)
                presigned_url = s3.generate_presigned_url('get_object',
                                                          Params={'Bucket': application.config["AWS_BUCKET"],
                                                                  'Key': relative_path})

                original = {}

                original['original_filename'] = p_file.filename
                original['key'] = relative_path
                original['presigned_url'] = presigned_url
                original['generated_filename'] = final_image_path

                response['original'] = original

                relative_path = "secure_videos/" + final_image_path
                s3.upload_file(opath, application.config['AWS_BUCKET'], relative_path)
                presigned_url = s3.generate_presigned_url('get_object',
                                                          Params={'Bucket': application.config["AWS_BUCKET"],
                                                                  'Key': relative_path})

                copy = {}
                copy['original_filename'] = p_file.filename
                copy['key'] = relative_path
                copy['presigned_url'] = presigned_url
                copy['generated_filename'] = final_image_path

                response['copy'] = copy
                status_code = 200

                print("s3 transfert done")

                remove(mpath)
                remove(opath)


            except Exception as error:
                response['ERROR'] = str(error)
                status_code = 402

            return response, status_code



# API Endpoints
class UploadImageFile(Resource):
    task_post = reqparse.RequestParser()
    task_post.add_argument('imag', required=True, help="image is required!", type=FileStorage, location='files')
    task_post.add_argument('logo', required=True, help="logo is required!", type=FileStorage, location='files')
    task_post.add_argument('dir', type=str, help="Dir is required!", required=True, )

    def post(self):
        response = {}
        args = self.task_post.parse_args()
        p_file = args["imag"]
        p_watermake = args["logo"]
        filename = secure_filename(p_file.filename)
        if filename == '':
            response['ERROR'] = "No file name was provided!"
            return response, 400
        else:
            # upload_image(p_file)
            # fic.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(fic.filename)))
            securename = create_random_id(filename)
            image = Image.open(p_file)
            print(type(image))
            print(int(image.size[0]))
            print(int(image.size[1]))

            image_copy = image.copy()

            logo = Image.open(p_watermake)

            print(logo.width)
            print(logo.height)

            logosm = logo.resize((int(logo.size[0] / 2), int(logo.size[1] / 2)))

            return create_watermark(p_file, securename, p_watermake)

"""
# API Endpoints
class UploadPdfFile(Resource):
    task_post = reqparse.RequestParser()
    task_post.add_argument('pdf', required=True, help="pdf is required!", type=FileStorage, location='files')

    # task_post.add_argument('logo', required=True, help="logo is required!",  type=FileStorage, location='files')
    # task_post.add_argument('dir', type=str,help="Dir is required!", required=True,)

    def post(self):
        response = {}
        args = self.task_post.parse_args()
        p_file = args["pdf"]
        # p_watermake = Image.open(args["logo"])
        filename = secure_filename(p_file.filename)
        if filename == '':
            response['ERROR'] = "No file name was provided!"
            return response, 400
        else:

            try:
                # return mark_pdf("NOWORRI", BytesIO(p_file.read()), "./salim.pdf")

                # fic = request.files['pdf']
                fic = p_file
                # upl_file = fic.read()
                if fic.mimetype != 'application/pdf':
                    return jsonify({"status": "error not a pdf file"})
                data = fic.stream.read()
                print(fic.mimetype)
                data2 = mark_pdf_bytes("Noworri", make_temp_file(data)[0], make_temp_file(data)[1],
                                       make_temp_file(data)[2])
                # return Response(data2, mimetype='application/pdf')

                print("-----type data2")
                print(type(data2))

                # in_mem_file = BytesIO()
                # pdf_imgs[0].save(in_mem_file, save_all=True, append_images=pdf_imgs[1:])
                # in_mem_file.seek(0)

                final_image_path = create_random_id(filename)

                relative_path = "copies_pdfs/" + final_image_path
                s3 = get_client()
                s3.upload_fileobj(BytesIO(data2), application.config['AWS_BUCKET'], relative_path)
                presigned_url = s3.generate_presigned_url('get_object',
                                                          Params={'Bucket': application.config["AWS_BUCKET"],
                                                                  'Key': relative_path})

                original = {}

                original['original_filename'] = p_file.filename
                original['key'] = relative_path
                original['presigned_url'] = presigned_url
                original['generated_filename'] = final_image_path

                response['original'] = original

                relative_path = "secure_pdfs/" + final_image_path
                s3.upload_fileobj(BytesIO(data), application.config['AWS_BUCKET'], relative_path)
                presigned_url = s3.generate_presigned_url('get_object',
                                                          Params={'Bucket': application.config["AWS_BUCKET"],
                                                                  'Key': relative_path})

                copy = {}
                copy['original_filename'] = p_file.filename
                copy['key'] = relative_path
                copy['presigned_url'] = presigned_url
                copy['generated_filename'] = final_image_path

                response['copy'] = copy

                status_code = 200

                print("s3 transfert done")

                return response, status_code



            except Exception as error:
                response['ERROR'] = str(error)
                status_code = 402

            return response, status_code
"""

class DownloadSecureFile(Resource):
    task_post_fk = reqparse.RequestParser()
    task_post_fk.add_argument('filekey', type=str, help="Task is required!", required=True, )


    def post(self):
        response = {}
        args = self.task_post_fk.parse_args()
        bcname = args["filekey"]
        response['presigned_url'] = download_file(bcname)
        response['key'] = bcname
        status_code = 200
        return response, status_code


class UploadSecureFile(Resource):
    put_parser = reqparse.RequestParser()
    put_parser.add_argument('file', required=True, help="File is required!", type=FileStorage, location='files')
    put_parser.add_argument('dir', type=str, help="Dir is required!", required=True, )

    def post(self):
        response = {}
        args = self.put_parser.parse_args()
        p_file = args["file"]
        # uploaded_file = request.files['file']
        # check  extension
        filename = secure_filename(p_file.filename)
        if filename == '':
            response['ERROR'] = "No file name was provided!"
            return response, 400
        else:
            generated_filename = create_random_id(filename)
            file_ext = os.path.splitext(filename)[1]
            try:

                relative_path = args["dir"] + "/" + generated_filename
                s3 = get_client()
                s3.upload_fileobj(p_file, application.config['AWS_BUCKET'], relative_path)
                presigned_url = s3.generate_presigned_url('get_object',
                                                          Params={'Bucket': application.config["AWS_BUCKET"],
                                                                  'Key': relative_path})

            except Exception as error:
                response['ERROR'] = str(error)
                status_code = 400
            else:
                response['original_filename'] = p_file.filename
                response['key'] = relative_path
                response['presigned_url'] = presigned_url
                response['generated_filename'] = generated_filename
                status_code = 200
            # return redirect("/form")
            return response, status_code



















class HelloWorld(Resource):
    @staticmethod
    def get():
        return {
            'data': 'Hello world!'
        }


class HelloName(Resource):
    @staticmethod
    def get(name):
        return {
            'data': 'Hello {}'.format(name)
        }


todos = {
    1: {"task": "writte an api endpoint", "summary": "write the code with python"}
}

task_post_arg = reqparse.RequestParser()
task_post_arg.add_argument('task', type=str, help="Task is required!", required=True, )
task_post_arg.add_argument('summary', type=str, help="Summary is required!", required=True, )

task_put_arg = reqparse.RequestParser()
task_put_arg.add_argument('task', type=str, )
task_put_arg.add_argument('summary', type=str, )

ressources_fields = {
    'id': fields.Integer,
    'task': fields.String,
    'summary': fields.String
}


class ToDo(Resource):
    @marshal_with(ressources_fields)
    def get(self, todo_id):
        return todos[todo_id]

    @marshal_with(ressources_fields)
    def post(self, todo_id):
        args = task_post_arg.parse_args()
        if todo_id in todos:
            abort(409)
        todos[todo_id] = {'task': args["task"], "summary": args["summary"]}
        return todos

    @staticmethod
    def delete(todo_id):
        del todos[todo_id]
        return todos

    @marshal_with(ressources_fields)
    def put(self, todo_id):
        args = task_put_arg.parse_args()
        if todo_id not in todos:
            abort(409)

        if args['task']:
            todos[todo_id]['task'] = args['task']

        if args['summary']:
            todos[todo_id]['summary'] = args['summary']
        return todos[todo_id]


class ToDoList(Resource):
    @staticmethod
    def get():
        return todos


@application.route('/')
def hello():
    return 'Hello, World from kader added complet requirements!'


api.add_resource(HelloWorld, '/helloworld')
api.add_resource(HelloName, '/helloworld/<string:name>')
api.add_resource(ToDo, '/todos/<int:todo_id>')
api.add_resource(ToDoList, '/todos')

api.add_resource(UploadSecureFile, '/upload_file')
api.add_resource(CreateBucket, '/createbucket')
api.add_resource(DownloadSecureFile, '/getfile')
api.add_resource(UploadVideoFile, '/uploadvideo')
api.add_resource(UploadImageFile, '/uploadimage')
# api.add_resource(UploadPdfFile, '/noworriuploadpdf')
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=8080)
