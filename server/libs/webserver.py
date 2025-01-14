from flask import Flask, render_template, request, jsonify, send_file
from waitress import serve
from time import sleep
import logging
import copy
import json

from libs.webserver_executer import WebserverExecuter  # pylint: disable=E0611, E0401
from libs.config_service import ConfigService  # pylint: disable=E0611, E0401


server = Flask(__name__)


class Webserver():
    def start(self, config_lock, notification_queue_in, notification_queue_out, effects_queue):
        self.logger = logging.getLogger(__name__)

        self._config_lock = config_lock
        self.notification_queue_in = notification_queue_in
        self.notification_queue_out = notification_queue_out
        self.effects_queue = effects_queue

        self.webserver_executer = WebserverExecuter(config_lock, notification_queue_in, notification_queue_out, effects_queue)
        Webserver.instance = self

        config_instance = ConfigService.instance(self._config_lock)
        self.export_config_path = config_instance.get_config_path()

        server.config["TEMPLATES_AUTO_RELOAD"] = True
        webserver_port = self.webserver_executer.GetWebserverPort()
        serve(server, host='0.0.0.0', port=webserver_port)

        while True:
            sleep(10)

    #####################################################################
    #   Dashboard                                                       #
    #####################################################################

    @server.route('/', methods=['GET'])
    @server.route('/index', methods=['GET'])
    @server.route('/dashboard', methods=['GET'])
    def index():  # pylint: disable=E0211
        # First handle with normal GET and render the template.
        return render_template('dashboard.html')

    #####################################################################
    #   Settings                                                        #
    #####################################################################
    @server.route('/settings/<template>', methods=['GET', 'POST'])
    def settings(template):  # pylint: disable=E0211
        if not template.endswith('.html'):
            template += '.html'
        return render_template("/settings/" + template)

    @server.route('/export_config')
    def export_config():  # pylint: disable=E0211
        Webserver.instance.logger.debug(f"Send file: {Webserver.instance.export_config_path}")
        return send_file(Webserver.instance.export_config_path, as_attachment=True, cache_timeout=-1)

    @server.route('/import_config', methods=['POST'])
    def import_config():  # pylint: disable=E0211
        Webserver.instance.logger.debug("Import Config Request received.")
        if 'imported_config' not in request.files:
            Webserver.instance.logger.error("Could not find the file key.")
            return "Could not import file.", 404
        imported_config = request.files['imported_config']
        content = imported_config.read()
        if content:
            try:
                Webserver.instance.logger.debug(f"File Received: {json.dumps(json.loads(content), indent=4)}")
                if Webserver.instance.webserver_executer.ImportConfig(json.loads(content, encoding='utf-8')):
                    return "File imported.", 200
                else:
                    return "Could not import file.", 400
            except json.decoder.JSONDecodeError:
                return "File is not valid JSON.", 400
        else:
            return "No config file selected.", 400

    #####################################################################
    #   Effects                                                         #
    #####################################################################
    @server.route('/effects/<template>', methods=['GET', 'POST'])
    def route_effects(template):  # pylint: disable=E0211
        if not template.endswith('.html'):
            template += '.html'

        # Serve the file (if exists) from templates/effects/FILE.html
        return render_template("/effects/" + template)

    #####################################################################
    #   Ajax Endpoints                                                  #
    #####################################################################

    # /GetDevices
    # in
    # {
    # }

    # return
    # {
    # "<device_id1>" = <device_name1>
    # "<device_id2>" = <device_name2>
    # "<device_id3>" = <device_name3>
    # ...
    # }

    @server.route('/GetDevices', methods=['GET'])
    def GetDevices():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            devices = Webserver.instance.webserver_executer.GetDevices()
            data_out = devices

            if devices is None:
                return "Could not find devices: ", 403
            else:
                return jsonify(data_out)

    #################################################################

    # /GetActiveEffect
    # in
    # {
    # "device" = <deviceID>
    # }

    # return
    # {
    # "device" = <deviceID>
    # "effect" = <effectID>
    # }
    @server.route('/GetActiveEffect', methods=['GET'])
    def GetActiveEffect():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device",)):
                return "Input data are wrong.", 403

            active_effect = Webserver.instance.webserver_executer.GetActiveEffect(data_in["device"])
            data_out["effect"] = active_effect

            if active_effect is None:
                return "Could not find active effect: ", 403
            else:
                return jsonify(data_out)

    # /SetActiveEffect
    # {
    # "device" = <deviceID>
    # "effect" = <effectID>
    # }
    @server.route('/SetActiveEffect', methods=['POST'])
    def SetActiveEffect():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "effect",)):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetActiveEffect(data_in["device"], data_in["effect"])

            return jsonify(data_out)

    # SetActiveEffectForAll
    # {
    # "effect" = <effectID>
    # }
    @server.route('/SetActiveEffectForAll', methods=['POST'])
    def SetActiveEffectForAll():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("effect",)):
                return "Input data is wrong.", 403

            Webserver.instance.webserver_executer.SetActiveEffectForAll(data_in["effect"])

            return jsonify(data_out)

    # /GetEffectSetting
    # in
    # {
    # "device" = <deviceID>
    # "effect" = <effectID>
    # "setting_key" = <setting_key>
    # }
    #
    # return
    # {
    # "device" = <deviceID>
    # "effect" = <effectID>
    # "setting_key" = <setting_key>
    # "setting_value" = <setting_value>
    # }
    @server.route('/GetEffectSetting', methods=['GET'])
    def GetEffectSetting():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "effect", "setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Webserver.instance.webserver_executer.GetEffectSetting(data_in["device"], data_in["effect"], data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

    # /GetColors
    #
    # return
    # {
    # "<colorID1>" = <colorName1>
    # "<colorID2>" = <colorName2>
    # "<colorID3>" = <colorName3>
    # ...
    # }
    @server.route('/GetColors', methods=['GET'])
    def GetColors():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            colors = Webserver.instance.webserver_executer.GetColors()
            data_out = colors

            if data_out is None:
                return "Could not find colors.", 403
            else:
                return jsonify(data_out)

    # /GetGradients
    #
    # return
    # {
    # "<gradientID1>" = <gradientName1>
    # "<gradientID2>" = <gradientName2>
    # "<gradientID3>" = <gradientName3>
    # ...
    # }
    @server.route('/GetGradients', methods=['GET'])
    def GetGradients():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            gradients = Webserver.instance.webserver_executer.GetGradients()
            data_out = gradients

            if data_out is None:
                return "Could not find gradients.", 403
            else:
                return jsonify(data_out)

    # /GetLEDStrips
    #
    # return
    # {
    # "<LEDStripID1>" = <LEDStripName1>
    # "<LEDStripID2>" = <LEDStripName2>
    # "<LEDStripID3>" = <LEDStripName3>
    # ...
    # }
    @server.route('/GetLEDStrips', methods=['GET'])
    def GetLEDStrips():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            led_strips = Webserver.instance.webserver_executer.GetLEDStrips()
            data_out = led_strips

            if data_out is None:
                return "Could not find led_strips.", 403
            else:
                return jsonify(data_out)

    # /GetLoggingLevels
    #
    # return
    # {
    # "<GetLoggingLevelID1>" = <LoggingLevelName1>
    # "<GetLoggingLevelID2>" = <LoggingLevelName2>
    # "<GetLoggingLevelID3>" = <LoggingLevelName3>
    # ...
    # }
    @server.route('/GetLoggingLevels', methods=['GET'])
    def GetLoggingLevels():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            logging_levels = Webserver.instance.webserver_executer.GetLoggingLevels()
            data_out = logging_levels

            if data_out is None:
                return "Could not find logging_levels.", 403
            else:
                return jsonify(data_out)

    # /SetEffectSetting
    # {
    # "device" = <deviceID>
    # "effect" = <effectID>
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetEffectSetting', methods=['POST'])
    def SetEffectSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "effect", "settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetEffectSetting(data_in["device"], data_in["effect"], data_in["settings"])

            return jsonify(data_out)

    # /SetEffectSettingForAll
    # {
    # "effect" = <effectID>
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetEffectSettingForAll', methods=['POST'])
    def SetEffectSettingForAll():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("effect", "settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetEffectSettingForAll(data_in["effect"], data_in["settings"])

            return jsonify(data_out)

    #################################################################

    # /GetGeneralSetting
    # in
    # {
    # "setting_key" = <setting_key>
    # }
    #
    # return
    # {
    # "setting_key" = <setting_key>
    # "setting_value" = <setting_value>
    # }
    @server.route('/GetGeneralSetting', methods=['GET'])
    def GetGeneralSetting():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Webserver.instance.webserver_executer.GetGeneralSetting(data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

    # /SetGeneralSetting
    # {
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetGeneralSetting', methods=['POST'])
    def SetGeneralSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetGeneralSetting(data_in["settings"])

            return jsonify(data_out)

    #################################################################

    # /GetDeviceSetting
    # in
    # {
    # "device" = <deviceID>
    # "setting_key" = <setting_key>
    # }
    #
    # return
    # {
    # "device" = <deviceID>
    # "setting_key" = <setting_key>
    # "setting_value" = <setting_value>
    # }
    @server.route('/GetDeviceSetting', methods=['GET'])
    def GetDeviceSetting():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Webserver.instance.webserver_executer.GetDeviceSetting(data_in["device"], data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

    # /SetDeviceSetting
    # {
    # "device" = <deviceID>
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetDeviceSetting', methods=['POST'])
    def SetDeviceSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetDeviceSetting(data_in["device"], data_in["settings"])

            return jsonify(data_out)

    # /GetOutputTypes
    #
    # return
    # {
    # "<outputTypeID1>" = <outputTypeName1>
    # "<outputTypeID2>" = <outputTypeName2>
    # "<outputTypeID3>" = <outputTypeName3>
    # ...
    # }
    @server.route('/GetOutputTypes', methods=['GET'])
    def GetOutputTypes():  # pylint: disable=E0211
        if request.method == 'GET':
            data_out = dict()

            output_types = Webserver.instance.webserver_executer.GetOutputTypes()
            data_out = output_types

            if data_out is None:
                return "Could not find output_types.", 403
            else:
                return jsonify(data_out)

    # /GetOutputTypeDeviceSetting
    # in
    # {
    # "device" = <deviceID>
    # "output_type_key" = <output_type_key>
    # "setting_key" = <setting_key>
    # }
    #
    # return
    # {
    # "device" = <deviceID>
    # "output_type_key" = <output_type_key>
    # "setting_key" = <setting_key>
    # "setting_value" = <setting_value>
    # }
    @server.route('/GetOutputTypeDeviceSetting', methods=['GET'])
    def GetOutputTypeDeviceSetting():  # pylint: disable=E0211
        if request.method == 'GET':
            data_in = request.args.to_dict()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "output_type_key", "setting_key",)):
                return "Input data are wrong.", 403

            setting_value = Webserver.instance.webserver_executer.GetOutputTypeDeviceSetting(data_in["device"], data_in["output_type_key"], data_in["setting_key"])
            data_out["setting_value"] = setting_value

            if setting_value is None:
                return "Could not find settings value: ", 403
            else:
                return jsonify(data_out)

    # /SetOutputTypeDeviceSetting
    # {
    # "device" = <deviceID>
    # "output_type_key" = <output_type_key>
    # "settings" = {
    #   "<settings_key>" = <setting_value>
    # }
    # }
    @server.route('/SetOutputTypeDeviceSetting', methods=['POST'])
    def SetOutputTypeDeviceSetting():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device", "output_type_key", "settings", )):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.SetOutputTypeDeviceSetting(data_in["device"], data_in["output_type_key"], data_in["settings"])

            return jsonify(data_out)

    # /CreateNewDevice
    # {
    # }
    @server.route('/CreateNewDevice', methods=['POST'])
    def CreateNewDevice():  # pylint: disable=E0211
        if request.method == 'POST':

            data_out = dict()

            Webserver.instance.webserver_executer.CreateNewDevice()

            return jsonify(data_out)

    # /DeleteDevice
    # {
    # "device" = <deviceID>
    # }
    @server.route('/DeleteDevice', methods=['POST'])
    def DeleteDevice():  # pylint: disable=E0211
        if request.method == 'POST':
            data_in = request.get_json()
            data_out = copy.deepcopy(data_in)

            if not Webserver.instance.webserver_executer.ValidateDataIn(data_in, ("device",)):
                return "Input data are wrong.", 403

            Webserver.instance.webserver_executer.DeleteDevice(data_in["device"])

            return jsonify(data_out)

    # /ResetSettings
    # {
    # }
    @server.route('/ResetSettings', methods=['POST'])
    def ResetSettings():  # pylint: disable=E0211
        if request.method == 'POST':

            data_out = dict()

            Webserver.instance.webserver_executer.ResetSettings()

            return jsonify(data_out)
