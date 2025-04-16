
import os
import json

classes = ['ph5', 'p26', 'pl40', 'pl60', 'pn', 'i5', 'p11', 'pne', 'pcl', 'pl50',  'w55', 'pl5', 'ph4.5',
            'pl80', 'pg',  'w30', 'pl30', 'p19', 'i4l', 'i2r',  'pm20', 'pbp', 'p5', 'pl120',
            'p13', 'w57', 'ip', 'p10', 'il100', 'il60', 'il90', 'pb', 'w59', 'il80', 'pl100', 'ph4',
            'pl15', 'i4',  'p3', 'pl70',  'w13', 'w32', 'i2', 'pr40', 'pm30', 'w63',
            'p12', 'p18', 'im', 'pl20', 'p6', 'p27',  'p1', 'i10',
            'p23', 'w58', 'pl90', 'pbm', 'pm55',
            'pr60',  'w22',  'p9',  'ps',
            'w21', 'pa14', 'pm10',
            ]



def convert(size, box):
    '''
    @size: (w, h)， 图片的高宽
    @box: (xmin, xmax, ymin, ymax), 标注框的坐标
    @return: (x_center, y_center, w2, h2), 返回目标中心坐标与相对高宽
    '''
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[1]) / 2.0
    y = (box[2] + box[3]) / 2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    x = x * dw
    w = w * dw
    y = y * dh
    h = h * dh
    return (x, y, w, h)


def annos2txt(annos, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    h, w = 2048, 2048  # 图片大小
    image_name = annos["path"]  # eg test/10056.jpg
    out_txt = os.path.join(out_dir, image_name[:-4] + '.txt')
    with open(out_txt, 'a') as f:  # 新建对应 txt 文件

        for obj in annos['objects']:  # 遍历每个子列表即原 txt 的每一行
            cls = obj['category']
            if cls in classes:
                cls_id = classes.index(cls)  # 写入编号对应类别标签

                '''读取框的坐标'''
                xmin = obj['bbox']['xmin']
                ymin = obj['bbox']['ymin']
                xmax = obj['bbox']['xmax']
                ymax = obj['bbox']['ymax']
                bndbox = convert((w, h), (xmin, xmax, ymin, ymax))

                f.write(str(cls_id) + " " + " ".join([str(a) for a in bndbox]) + '\n')  # 写入


def main():
    filedir = "./annotations_all.json"  # json文件
    ids_file = "./other/ids.txt"  # 指定为 train/test
    ids = open(ids_file).read().splitlines()  # 获取 id 编号
    annos = json.loads(open(filedir).read())
    outdir = './'  # txt 保存目录

    img_num = len(ids)  # 统计当前图片数量
    cnt_id = 1  # 计数变量

    for imgid in ids:
        print('\rprocessing :[{} / {}]'.format(cnt_id, img_num), end="")
        cnt_id += 1

        # 跳过没有目标的图片
        if imgid in annos['imgs']:
            xml_cls = annos['imgs'][imgid]
            annos2txt(xml_cls, outdir)  # 生成 txt 文件


if __name__ == "__main__":
    main()

