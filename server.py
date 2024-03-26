from flask import Flask, request, send_file
import tensorflow as tf
from keras.preprocessing.image import load_img
from keras.preprocessing.image import img_to_array
import numpy as np
from flask_cors import CORS
import cv2
from skimage.graph import route_through_array
import matplotlib.pyplot as plt
from PIL import Image, ImageFilter

# Initializing flask app
app = Flask(__name__)
CORS(app)

model = tf.keras.models.load_model('roadseg.h5', compile = False)
H = 256
W = 256

def read_image(path):
    try:
        img = Image.open(path)
        img = img.resize((W, H))
        x = np.array(img, dtype=np.float32)
        x = x / 255.0
        return x
    except Exception as e:
        print(f"Error while reading image: {e}")
        return None

def make_square(image_path, output_size):
    # Open the image
    img = Image.open(image_path)
    
    # Get the dimensions of the image
    width, height = img.size
    
    # Determine the size of the output square image
    new_size = (max(width, height), max(width, height))
    
    # Create a new square image with black background
    new_img = Image.new("RGB", new_size, (0, 0, 0))
    
    # Calculate the position to paste the original image
    left = 0
    top = 0
    
    # Paste the original image onto the new square image
    new_img.paste(img, (left, top))
    
    # Resize the image to the desired output size
    new_img = new_img.resize((output_size, output_size))
    
    # Save or display the new square image
    # new_img.show()  # To display the image
    new_img.save("img.jpg")  # To save the image
    
def within_bounds(r, c):
    return r >= 0 and c >= 0 and c <= W - 1 and r <= W - 1 

@app.route("/predict", methods=["POST"])
def processReq():
    
    data = request.files["file"]
    data.save("img.jpg")
    # make_square("img.jpg", output_size=256)
    img = read_image("img.jpg")

    def get_image_dimensions(image_path):
        with Image.open(image_path) as img:
            width, height = img.size
        return width, height

    width, height = get_image_dimensions("img.jpg")
    print(f"Image dimensions: {width} x {height}")

    form = request.form

    # startY = int(round(256 * float(form["startY"]) / height))
    # startX = int(round(256 * float(form["startX"]) / width))
    # endY = int(round(256 * float(form["endY"]) / height))
    # endX = int(round(256 * float(form["endX"]) / width))
    # middleY = int(round(256 * float(form["middleY"]) / height))
    # middleX = int(round(256 * float(form["middleX"]) / width))

    startY = int(round(float(form["startY"])))
    startX = int(round(float(form["startX"])))
    endY = int(round(float(form["endY"])))
    endX = int(round(float(form["endX"])))
    middleY = int(round(float(form["middleY"])))
    middleX = int(round(float(form["middleX"])))
    
    start = [255 - startY, startX]
    end = [255 - endY, endX]

    print(start)
    print(end)
    middle = []
    if(form["middleY"]):
         middle = [255 - middleY, middleX]
    thresh = int(form["threshold"])

    img_array = tf.keras.preprocessing.image.img_to_array(img)
    img_array = tf.expand_dims(img_array, 0)
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img)

    result = pred[0,...]
    result = np.squeeze(result, axis=2)
    im = Image.fromarray((result * 255).astype(np.uint8))
    im.save("segmented.png")

    seg  = cv2.imread('segmented.png',cv2.IMREAD_GRAYSCALE)

    # cv2.imwrite('seg.png',seg)
    # main = cv2.imread(src,cv2.IMREAD_GRAYSCALE)

    main = cv2.imread("img.jpg")
    main = cv2.resize(main, (W, H))
    # main = cv2.cvtColor(main,cv2.COLOR_GRAY2BGR)
    # print(main.shape)
    
    im_bw = cv2.threshold(seg, thresh, 255, cv2.THRESH_BINARY)[1]
    # print(thresh)

    

    print(im_bw.shape)
    cv2.imwrite('binary_image.png', im_bw)
    cv2.imwrite('256image.png', main)
    costs = np.where(im_bw, 1, 1000)

    split_index = -1
    if(middle):
        path1, cost1 = route_through_array(costs, start=(start[0],start[1]), end=(middle[0],middle[1]), fully_connected=True)
        path2, cost2 = route_through_array(costs, start=(middle[0],middle[1]), end=(end[0],end[1]), fully_connected=True)
        path = path1 + path2
        split_index = len(path1)
    else:
         path, cost = route_through_array(costs, start=(start[0],start[1]), end=(end[0],end[1]), fully_connected=True)
    print(len(path))
    # print(cost)
    seg_color = [255,255,255]
    path_color = [255, 0, 0]
    path2_color = [255, 255, 0]
    start_color = [0, 255, 0]
    middle_color = [0, 255, 255]
    end_color = [0, 0, 255]
    


    color = np.array(seg_color, dtype='uint8')
    # masked_img = np.where(im_bw[...,None], color, main)
    masked_img = main
    cv2.imwrite('maskoverlay.png', masked_img)
    deltas = [-1, 0], [1, 0], [0, 1], [0, -1], [-1, -1], [-1, 1], [1, 1], [1, -1]
    i = 0
    for point in path:
        masked_img[point[0]][point[1]] = path_color
        
        for delta in deltas:
            r = point[0] + delta[0]
            c = point[1] + delta[1]
            if(within_bounds(r, c)):
                masked_img[r][c] = path_color if i < split_index else path2_color
        i += 1

    masked_img[start[0]][start[1]] = start_color
    masked_img[end[0]][end[1]] = end_color

    if(middle):
         masked_img[middle[0]][middle[1]] = middle_color

    for delta in deltas:
            sr = start[0] + delta[0]
            sc = start[1] + delta[1]
            er = end[0] + delta[0]
            ec = end[1] + delta[1]
            if(within_bounds(sr, sc)):
                masked_img[sr][sc] = start_color
            if(within_bounds(er, ec)):
                masked_img[er][ec] = end_color
            if(middle):
                mr = middle[0] + delta[0]
                mc = middle[1] + delta[1]
                if(within_bounds(mr, mc)):
                    masked_img[mr][mc] = middle_color
    
    cv2.imwrite('pathoverlay.png', masked_img)
    out = cv2.addWeighted(main, 0.8, masked_img, 0.4,0)
    cv2.imwrite('result.png',out)
    print(masked_img.shape)
    print(masked_img[start[0]][start[1]])

    return send_file('pathoverlay.png', mimetype='image/jpeg')

	
# Running app
if __name__ == '__main__':
	app.run(debug=True, port=5001)
