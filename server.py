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

# model = tf.keras.models.load_model('./potatoes.h5')
# IMAGE_SIZE = 256
# BATCH_SIZE = 32

# dataset = tf.keras.preprocessing.image_dataset_from_directory(
#     "PlantVillage",
#     seed=123,
#     shuffle=True,
#     image_size=(IMAGE_SIZE,IMAGE_SIZE),
#     batch_size=BATCH_SIZE
# )

# class_names = dataset.class_names
# print(class_names)

# def load_image(filename):
#     img = load_img(filename, target_size=(IMAGE_SIZE, IMAGE_SIZE))
#     return img

# Route for seeing a data
@app.route('/data')
async def get_time():

	# Returning an api for showing in reactjs
	return {
		'Name':"geek", 
		"Age":"22",
		"programming":"python"
		}

# @app.route('/dummypredict')
# async def predict():
#     src = 'PlantVillage/Potato___Late_blight/0acdc2b2-0dde-4073-8542-6fca275ab974___RS_LB 4857.JPG'
#     img = load_image(src);
	
#     img_array = tf.keras.preprocessing.image.img_to_array(img)
#     img_array = tf.expand_dims(img_array, 0)

#     predictions = model.predict(img_array)
#     predicted_class = class_names[np.argmax(predictions[0])]
#     actual_class = src.split("/")[1];
#     confidence = round(100 * (np.max(predictions[0])), 2)
#     print(f"Actual: {actual_class},\n Predicted: {predicted_class}.\n Confidence: {confidence}%")

#     # img_array = tf.keras.preprocessing.image.img_to_array(img)
#     # img_array = tf.expand_dims(img_array, 0)

#     # # image = read_file_as_image(await file.read())
#     # # img_batch = np.expand_dims(image, 0)
#     # # predictions = MODEL.predict(img_batch)
    
#     # predictions = MODEL.predict(img_array)

#     # predicted_class = CLASS_NAMES[np.argmax(predictions[0])]
#     # confidence = np.max(predictions[0])

# 	# Returning an api for showing in reactjs
#     return {
#         'class': predicted_class,
#         'confidence': confidence
#     }

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
    
def within_bounds(r, c):
    return r >= 0 and c >= 0 and c <= W - 1 and r <= W - 1 

@app.route("/predict", methods=["POST"])
def processReq():
    # start = [20, 200]
    # end = [220, 50]
    form = request.form
    # print(type(form["startX"]))
    start = [255 - int(form["startY"]), int(form["startX"])]
    end = [255 - int(form["endY"]), int(form["endX"])]
    thresh = int(form["threshold"])
    # print(request.form)

    data = request.files["file"]
    data.save("img.jpg")
    img = read_image("img.jpg");

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
    path, cost = route_through_array(costs, start=(start[0],start[1]), end=(end[0],end[1]), fully_connected=True)
    print(len(path))
    # print(cost)
    seg_color = [255,255,255]
    path_color = [255, 0, 0]
    start_color = [0, 255, 0]
    end_color = [0, 0, 255]
    


    color = np.array(seg_color, dtype='uint8')
    masked_img = np.where(im_bw[...,None], color, main)
    cv2.imwrite('maskoverlay.png', masked_img)
    deltas = [-1, 0], [1, 0], [0, 1], [0, -1], [-1, -1], [-1, 1], [1, 1], [1, -1]
    for point in path:
        masked_img[point[0]][point[1]] = path_color
        
        for delta in deltas:
            r = point[0] + delta[0]
            c = point[1] + delta[1]
            if(within_bounds(r, c)):
                masked_img[r][c] = path_color

    masked_img[start[0]][start[1]] = start_color
    masked_img[end[0]][end[1]] = end_color

    for delta in deltas:
            sr = start[0] + delta[0]
            sc = start[1] + delta[1]
            er = end[0] + delta[0]
            ec = end[1] + delta[1]
            if(within_bounds(sr, sc)):
                masked_img[sr][sc] = start_color
            if(within_bounds(er, ec)):
                masked_img[er][ec] = end_color
    
    cv2.imwrite('pathoverlay.png', masked_img)
    out = cv2.addWeighted(main, 0.8, masked_img, 0.4,0)
    cv2.imwrite('result.png',out)
    print(masked_img.shape)
    print(masked_img[start[0]][start[1]])

    # return {
    #     'class': 0,
    #     'confidence': 0,
    # }
    return send_file('pathoverlay.png', mimetype='image/jpeg')

	
# Running app
if __name__ == '__main__':
	app.run(debug=True)
