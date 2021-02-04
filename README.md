README
===========================
该插件用于HOMEASSISTANT，采用了百度人体统计V3接口，通过轮询，来获取图像，先本地进行图像对比，如果低于设定值，不进行人体识别，高于设定值，通过百度人体统计接口进行人体识别

***
#### 安装步骤：
1. 下载[baidu_renti](./config/custom_components)目录放到HOMEASSISTANT的config/custom_components目录下
1. 申请[百度开发者网站](https://ai.baidu.com/tech/body/numh) 的账户并创建应用拿到key，完善以下内容
``` YAML {.line-numbers}
sensor:
  - platform: baidu_renti
    baidu:
      clientid: xxxxxxxxxxxxxx # 替换你的百度clientid
      clientSecret: xxxxxxxxxx # 替换你的百度clientSecret
    cameras:
      - entity_id: camera.xxxx1  # 摄像头实体
        scan_interval: 3        # 此摄像头的轮询实体
        changes: 90             # 本地对比值（相当于灵敏度），取当前画面跟上次画面进行对比
#如果高于就进行人体识别（减少百度API使用量，一天只有5w）设为0为不对比，直接百度识别
        frame:                  #单个摄像头分区域（没有区域就不填，默认全图识别）
          - name: in            #区域的名称
            area: 478,73,565,127,537,476,508,479,468,281 #区域的范围，
# 区域范围规则（第一个x坐标，第一个y坐标，第二个x坐标，第二个y坐标........）需要围城一个封闭空间，详见下方百度开发文档
          - name: out           #第二个区域
            area: 343,93,463,93,453,272,491,467,215,470,315,188
          #后面可以按上面加多个区域
      - entity_id: camera.xxxx2 #第2个摄像头实体
        scan_interval: 4
        changes: 90
```
3. 把上面完善的内容加入config目录里的configuration.yml文件里
3. 重启HOMEASSISTANT

#### 界面预览：
![界面图](/assets/mian.png)

### 服务调用
可以调用服务baidu_renti.get_img，给入数据img: true，可开启保存图片，在有人的情况下，会自动保存图片到media/camera_pic/{你的摄像头名称}目录下
也可以直接在前端媒体游览器直接观看
---
![界面图](/assets/services.png)
![界面图](/assets/media_browse.png)

参考的地方
===
- https://developers.home-assistant.io/
- 百度开发文档:https://ai.baidu.com/ai-doc/BODY/7k3cpyy1t