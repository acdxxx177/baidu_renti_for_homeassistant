import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from datetime import datetime, timedelta

from homeassistant.const import CONF_ENTITY_ID, CONF_SCAN_INTERVAL
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorDevice, DEVICE_CLASS_MOTION
from homeassistant.core import split_entity_id
from .compare_the_task import compareTask
from .baiduBodyAnalysis import baiduBody
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

# 百度
CLIENT_ID = "clientid"
CLIENT_SECRET = "clientSecret"
# 验证数据
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required("baidu"): {
        vol.Required(CLIENT_ID): cv.string,
        vol.Required(CLIENT_SECRET): cv.string
    },
    vol.Required("cameras"): [{
        vol.Required(CONF_ENTITY_ID): cv.entity_domain("camera"),
        vol.Optional(CONF_SCAN_INTERVAL, default=5): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("changes", default=100): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("frame"): [{vol.Required("name"): cv.string, vol.Required("area"): cv.matches_regex("^([1-9][0-9]*)+(,[1-9][0-9]*){5,}$")}]
    }]
})


async def async_setup_platform(hass,
                               config,
                               async_add_devices,
                               discovery_info=None):
    _LOGGER.info("人体识别加载成功.....")

    client_id = config.get('baidu')[CLIENT_ID]
    client_secret = config.get('baidu')[CLIENT_SECRET]
    camera_entitys = config.get('cameras')
    # 初始化百度并获取token
    _baidubody = baiduBody(hass, client_id, client_secret)
    await _baidubody.async_get_baidu_token(datetime.now())

    # 创建实体
    creat_entiy = []
    _compareTask_list = []

    for camera_entity in camera_entitys:

        _compareTask = compareTask(
            hass, camera_entity[CONF_ENTITY_ID], camera_entity["changes"], _baidubody)
        _compareTask_list.append(_compareTask)
        _camera_name = f"baidu_renti_{split_entity_id(camera_entity[CONF_ENTITY_ID])[1]}"
        _coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=_camera_name,
            update_method=_compareTask.async_process_img,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(
                seconds=camera_entity[CONF_SCAN_INTERVAL])
        )

        if "frame" in camera_entity.keys():
            for index, pframe in enumerate(camera_entity["frame"]):
                _compareTask.set_area(pframe["area"])
                creat_entiy.append(BaidurentiEntity(
                    _coordinator, pframe["name"], _camera_name, index))
        else:
            creat_entiy.append(BaidurentiEntity(
                _coordinator, _camera_name, _camera_name))

    # Fetch initial data so we have data when entities subscribe
    # await coordinator.async_refresh()

    async_add_devices(creat_entiy)

    async def get_img(call):
        """是否获得图片"""
        value = call.data.get("img", False)
        for _list in _compareTask_list:
            _list.set_return_img(value)
        _LOGGER.info("更改图像获得%s" % value)

    # 增加一个服务,开关更新状态
    hass.services.async_register("baidu_renti", "get_img", get_img)


class BaidurentiEntity(CoordinatorEntity, BinarySensorDevice):
    """Representation of the Microsoft Face API entity for identify."""

    def __init__(self, coordinator, name, unique_id, index=0):
        super().__init__(coordinator)
        self._name = name
        self._index = index
        self._unique_id = unique_id
        self._status = False
        self._prson_number = 0

    @property
    def name(self):
        """实体名字"""
        return self._name

    @property
    def unique_id(self):
        return f"{self._unique_id}_{self._index}"

    @property
    def is_on(self):
        """状态"""
        data = self.coordinator.data
        if not isinstance(data, list):
            self._prson_number = 0
            return False
        elif len(data) >= self._index:
            self._prson_number = data[self._index]
            return data[self._index] > 0
        else:
            self._prson_number = 0
            _LOGGER.error("%s区域错误，请检查区域范围是否正确!!!")
            return False

    @property
    def device_state_attributes(self):
        """设置其它一些属性值."""
        return {"检测到的人数:": self._prson_number}

    @property
    def device_class(self):
        """类型，这里设置运动"""
        return DEVICE_CLASS_MOTION
