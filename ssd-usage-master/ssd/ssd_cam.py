#!/usr/bin/env python

import os
import math
import random
import pandas as pd
import numpy as np
import tensorflow as tf
import cv2
from cv_bridge import CvBridge, CvBridgeError
import rospy
from sensor_msgs.msg import Image
from object_detector_ssd_tf_ros.msg import SSD_Output,SSD_Outputs
from std_msgs import Float64


slim = tf.contrib.slim

#matplotlib inline
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

import sys
sys.path.append('../')
sys.path.insert(0, '/home/elbazam/catkin_ws/src/ssd_slam/ssd-usage-master/ssd')
#from ssd 
import ssd_wrapper
# TensorFlow session: grow memory when needed. TF, DO NOT USE ALL MY GPU MEMORY!!!
gpu_options = tf.GPUOptions(allow_growth=True)
config = tf.ConfigProto(log_device_placement=False, gpu_options=gpu_options)

ssd = ssd_wrapper.ssdWrapper(config = config)


labels = pd.read_csv('../model/labels.txt')
colors = dict()
for cls_id in range(len(np.array(labels))):
    colors[cls_id] = (int(random.random()*255), int(random.random()*255), int(random.random()*255))

cam = cv2.VideoCapture(0)


cv_img = 0

def img_callback (ros_img):
    global bridge, cv_img
    try: 
        cv_img = bridge.imgmsg_to_cv2(ros_img,"rgb8")
    except CvBridgeError as e:
        print (e)

bridge = CvBridge()

rospy.init_node('img', anonymous = True)
img_sub = rospy.Subscriber('camera/image_raw/', Image, img_callback)
ros_img = rospy.wait_for_message('camera/image_raw/', Image)
Im_outs_Pub = rospy.Publisher('im_info',SSD_Outputs)




while not rospy.is_shutdown():
    #ret_val, img = cam.read()
    global cv_img
    L_output = SSD_Outputs()
    flag = 0
    img = cv_img
    img = cv2.resize(img, (300, 300),interpolation = cv2.INTER_AREA)
    rclasses, rscores, rbboxes, probs =  ssd.process_image(img)
    height = img.shape[0]
    width = img.shape[1]
   
    for i in range(len(rclasses)):
        output = SSD_Output()
        cls_id = int(rclasses[i])
        if cls_id >= 0:          
            ymin = int(rbboxes[i, 0] * height)
            xmin = int(rbboxes[i, 1] * width)
            ymax = int(rbboxes[i, 2] * height)
            xmax = int(rbboxes[i, 3] * width)
            flag = 1

            output.x_min = xmin
            output.x_max = xmax
            output.cls = cls_id

            for p in probs[i]:
                p_out = Float64()
                p_out.data = p
                output.probability_distribution.append(p_out)

            L_output.outputs.append(output)
            
        
            img = cv2.rectangle(img,(xmin,ymin),(xmax,ymax),colors[cls_id],2)
            font                   = cv2.FONT_HERSHEY_SIMPLEX
            bottomLeftCornerOfText = (xmin,ymin + 20)
            fontScale              = 1
            fontColor              =colors[cls_id]
            lineType               = 2
            
            img = cv2.putText(img,str(labels.iloc[cls_id][0]), 
                    bottomLeftCornerOfText, 
                    font, 
                    fontScale,
                    fontColor,
                    lineType)
    
    if flag == 0:
        output = SSD_Output()    
        output.x_min = -1
        output.x_max = -1
        output.cls = -1
        L_output.outputs.append(output)
        
    Im_outs_Pub.publish(L_output)  
    cv2.imshow('SSD output', img)

    
    if cv2.waitKey(1) == 27: 
        cam.release()
        cv2.destroyAllWindows()
        break  # esc to quit
