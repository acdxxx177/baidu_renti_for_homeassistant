#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from PIL import Image
from io import BytesIO
import os.path
import math
import operator
from functools import reduce
from datetime import datetime
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import split_entity_id
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)


class compareTask(object):

    def __init__(self, hass, camera_id, changes, baidubody):
        """
            初始化
        """
        self._hass = hass
        self._camera = camera_id
        self._changes = changes
        self._baidubody = baidubody
        self._oldimg = None
        self._timeout = 10
        self._area = ""
        self._return_img = "false"
        self.prosen_num = []

    @property
    def camera_id(self):
        return self._camera

    def set_area(self, area):
        """添加范围"""
        if len(self._area) > 0:
            self._area += ";"+area
        else:
            self._area = area

    def set_return_img(self, value=False):
        if value:
            self._return_img = "true"
        else:
            self._return_img = "false"

    async def async_process_img(self):
        """执行感应"""
        try:
            img = await self.async_get_image()
            change = 10
            if self._changes > 0 and self._return_img:
                change = await self.async_image_contrast(img)
            _LOGGER.debug("图片对比为:%d", change)
            if change > self._changes:
                options = {}
                if len(self._area) > 0:
                    options["area"] = self._area
                options["show"] = self._return_img
                result, img_data, total_number = await self._baidubody.async_baidu_prosen_number(img, options)
                _LOGGER.debug(result)
                self.prosen_num = result
                if img_data and total_number:
                    await self.async_save_img(img_data)
            return self.prosen_num
        except Exception as e:
            raise UpdateFailed("获取数据错误!%s" % e)

    async def async_get_image(self):
        """从摄像头获取图像"""
        camera = self._hass.components.camera
        image = None
        try:
            image = await camera.async_get_image(
                self._camera, timeout=self._timeout
            )
        except HomeAssistantError as err:
            _LOGGER.error("获取摄像头%s错误: %s", self._camera, err)
            raise
        return image.content

    async def async_image_contrast(self, newimg):
        """对比图片差异化"""
        h1 = Image.open(BytesIO(newimg)).convert('L').histogram()
        result = 0
        if self._oldimg is None:
            result = self._changes+1
        else:
            result = math.sqrt(reduce(operator.add, list(
                map(lambda a, b: (a - b)**2, h1, self._oldimg))) / len(h1))
        self._oldimg = h1
        return result

    async def async_save_img(self, img):
        """保存图像到目录"""
        _camera_name = split_entity_id(self._camera)[1]
        _config_dir = self._hass.config.media_dirs["local"] + \
            "/camera_pic/"+_camera_name
        _path = "%s/%s_%s.jpg" % (_config_dir,
                                  _camera_name, str(datetime.now()))
        if not os.path.exists(_config_dir):
            os.makedirs(_config_dir)
        with open(_path, 'wb') as fp:
            fp.write(img)
        _LOGGER.debug("保存路径:%s" % _path)
