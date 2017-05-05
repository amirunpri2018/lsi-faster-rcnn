#!/usr/bin/env python

# --------------------------------------------------------
# Faster R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# Modified by C. Guindel at UC3M
# --------------------------------------------------------

"""
Demo script showing detections in sample images.

See README.md for installation instructions before running.
"""

import _init_paths
from fast_rcnn.config import cfg
from fast_rcnn.test import im_detect
from fast_rcnn.nms_wrapper import nms
from utils.timer import Timer
import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import caffe, os, sys, cv2
import argparse
import glob

CLASSES = ('__background__',
           'aeroplane', 'bicycle', 'bird', 'boat',
           'bottle', 'bus', 'car', 'cat', 'chair',
           'cow', 'diningtable', 'dog', 'horse',
           'motorbike', 'person', 'pottedplant',
           'sheep', 'sofa', 'train', 'tvmonitor')

NETS = {'vgg16': ('VGG16',
                  'VGG16_faster_rcnn_final.caffemodel'),
        'zf': ('ZF',
                'ZF_faster_rcnn_final.caffemodel'),
        'caviar': ('caviar',
                'caviar.caffemodel')}

# video recorder
fourcc = cv2.VideoWriter_fourcc(*'H264')
record_flag = None;

def vis_detections(im, class_name, dets, thresh=0.5):

    """Draw detected bounding boxes."""
    inds = np.where(dets[:, -1] >= thresh)[0]
    if len(inds) == 0:
        return

    show_im = im.copy()

    for i in inds:
        bbox = dets[i, :4]
        score = dets[i, -1]

        cv2.rectangle(show_im,(int(bbox[0]), int(bbox[1])),
            (int(bbox[2]), int(bbox[3])), (0,0,255), 3)

        cv2.putText(show_im, '{:.0f}%'.format(score*100),
            (int(bbox[0]), int(bbox[1])-10), cv2.FONT_HERSHEY_DUPLEX,
            0.6, (0,0,255))

    cv2.imshow("result", show_im)
    key = cv2.waitKey(3)
    if args.record>0:
        video_writer.write(show_im)

    if key==27:    # Esc key to stop
        sys.exit(0)

def demo(net, image_name):
    """Detect object classes in an image using pre-computed object proposals."""

    # Load the demo image
    im_file = os.path.join(cfg.DATA_DIR, 'surveillance', image_name)
    im = cv2.imread(im_file)

    # Detect all object classes and regress object bounds
    timer = Timer()
    timer.tic()
    scores, boxes = im_detect(net, im, np.zeros((0,4), dtype=np.float32))
    timer.toc()
    print ('Detection took {:.3f}s for '
           '{:d} object proposals').format(timer.total_time, boxes.shape[0])

    # Visualize detections for each class
    CONF_THRESH = 0.01
    NMS_THRESH = 0.3
    if args.demo_net == 'caviar':
        cls_ind = 1
    else:
        cls_ind = 15
    cls = 'person'
    cls_boxes = boxes[:, 4*cls_ind:4*(cls_ind + 1)]
    cls_scores = scores[:, cls_ind]
    dets = np.hstack((cls_boxes,
    cls_scores[:, np.newaxis])).astype(np.float32)
    keep = nms(dets, NMS_THRESH)
    dets = dets[keep, :]
    vis_detections(im, cls, dets, thresh=CONF_THRESH)

def parse_args():
    """Parse input arguments."""
    parser = argparse.ArgumentParser(description='Faster R-CNN demo')
    parser.add_argument('--gpu', dest='gpu_id', help='GPU device id to use [0]',
                        default=0, type=int)
    parser.add_argument('--cpu', dest='cpu_mode',
                        help='Use CPU mode (overrides --gpu)',
                        action='store_true')
    parser.add_argument('--net', dest='demo_net', help='Network to use [caviar]',
                        choices=NETS.keys(), default='caviar')
    parser.add_argument('--record', dest='record', help='Record video [0]',
                        default=0)

    args = parser.parse_args()

    return args

if __name__ == '__main__':

    cfg.TEST.HAS_RPN = True  # Use RPN for proposals
    cfg.VIEWPOINTS = False
    cfg.TEST.SCALES = [500]
    cfg.TEST.MAX_SIZE = 3000
    #cfg.TEST.RPN_POST_NMS_TOP_N = 600
    #cfg.TEST.EXTERNAL_ROIS = True

    args = parse_args()

    prototxt = os.path.join(cfg.MODELS_DIR, NETS[args.demo_net][0],
                            'faster_rcnn_alt_opt', 'faster_rcnn_test.pt')
    caffemodel = os.path.join(cfg.DATA_DIR, 'faster_rcnn_models',
                              NETS[args.demo_net][1])

    if args.record>0:
        video_writer = cv2.VideoWriter("output.avi", fourcc, 25, (384, 288))

    # prototxt = '/home/cguindel/lsi-faster-rcnn/models/kitti/VGG16/caviar/test.prototxt'
    # caffemodel = '/home/cguindel/lsi-faster-rcnn/output/caviar/kitti_caviar_train/vgg16_faster_rcnn_iter_100000.caffemodel'

    if not os.path.isfile(caffemodel):
        raise IOError(('{:s} not found.\nDid you run ./data/script/'
                       'fetch_faster_rcnn_models.sh?').format(caffemodel))

    if args.cpu_mode:
        caffe.set_mode_cpu()
    else:
        caffe.set_mode_gpu()
        caffe.set_device(args.gpu_id)
        cfg.GPU_ID = args.gpu_id
    net = caffe.Net(prototxt, caffemodel, caffe.TEST)

    print '\n\nLoaded network {:s}'.format(caffemodel)

    # Warmup on a dummy image
    im = 128 * np.ones((300, 500, 3), dtype=np.uint8)
    for i in xrange(2):
        _, _= im_detect(net, im, np.zeros((0,4), dtype=np.float32))

    for filename in sorted(glob.glob(os.path.join(cfg.DATA_DIR, 'surveillance','*.png'))):
        demo(net, filename)

    if args.record>0:
        video_writer.release()
