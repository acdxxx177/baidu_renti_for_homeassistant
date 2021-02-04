#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
百度请求数据类

"""
import logging
import datetime
import base64
import json
# HTTP请求库
import asyncio
import aiohttp
import async_timeout
from homeassistant.helpers.aiohttp_client import (async_get_clientsession)
# 事件处理
from homeassistant.helpers.event import async_track_point_in_time

_LOGGER = logging.getLogger(__name__)


class baiduBody(object):
    def __init__(self, hass, client_id, client_secret):
        self._hass = hass
        self.client_id = client_id
        self.client_secret = client_secret
        self._baidu_accessToken = None
        self._baidu_token_lock = False

    async def async_baidu_prosen_number(self, image, options=None):
        """
            人流量统计
        """
        prosen_number = []
        img_data = None
        total_number = 0
        try:
            geturl = "https://aip.baidubce.com/rest/2.0/image-classify/v1/body_num?access_token=%s" % self._baidu_accessToken
            options = options or {}
            data = {}
            data['image'] = base64.b64encode(image).decode()
            data.update(options)
            result = await self.async_fetch_data(geturl, data,
                                                 "人体识别统计")
            if "area_counts" in result:
                prosen_number += result["area_counts"]
            else:
                prosen_number.append(result["person_num"])
            if "image" in result:
                img_data = base64.b64decode(result["image"])
                total_number = result["person_num"]
        except Exception:
            raise
        return prosen_number, img_data, total_number

    async def async_get_baidu_token(self, datetimenow=datetime.datetime.now()):
        """获取百度Token"""
        # 加个同步锁，多设备的时候有时请求两次token
        if self._baidu_token_lock:
            return
        self._baidu_token_lock = True
        try:
            getTokenUrl = "https://aip.baidubce.com/oauth/2.0/token"
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            _LOGGER.debug("时间:%s正在获取百度Token....", datetimenow)
            result = await self.async_fetch_data(getTokenUrl, payload, "百度Tkoen")
            if "access_token" in result:
                token = result["access_token"]
                _LOGGER.debug("获取的百度token为:%s", token)
                self._baidu_accessToken = token
                expireTime = int(result['expires_in'])
                dateArray = datetime.datetime.now() + datetime.timedelta(
                    seconds=expireTime)
                _LOGGER.debug("百度token下次更新时间:%s", dateArray)
                # 添加一个事件，在指定时间再次获取token
                async_track_point_in_time(hass=self._hass,
                                          action=self.async_get_baidu_token,
                                          point_in_time=dateArray)
            else:
                _LOGGER.error("获取百度Token错误:%s", result)
                self._baidu_accessToken = None
                raise ValueError("获取百度Token错误%s" % result)
        except Exception:
            raise
        finally:
            self._baidu_token_lock = False

    async def async_fetch_data(
            self,
            url,
            payload,
            fetchname="数据",
            headers={'content-type': 'application/x-www-form-urlencoded'}):
        """POST获取数据"""
        websession = async_get_clientsession(self._hass)
        try:
            with async_timeout.timeout(15):
                response = await websession.post(url,
                                                 data=payload,
                                                 headers=headers)
                result = await response.json()
                if response.status != 200:
                    raise ValueError("%s请求返回码错误:%s" %
                                     (fetchname, response.status))
                elif result is None:
                    raise ValueError("%s请求未知错误" % fetchname)
                elif "error_msg" in result:
                    raise ValueError("%s请求错误%s" %
                                     (fetchname, result["error_msg"]))
                return result
        except asyncio.TimeoutError:
            _LOGGER.error("获取%s超时", fetchname)
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("获取%s错误: %s", fetchname, err)
            raise
        except Exception as err:
            raise
