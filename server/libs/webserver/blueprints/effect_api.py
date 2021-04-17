from flask import Blueprint, request, jsonify
from flask_login import login_required
from libs.webserver.executer import Executer

import copy
import json

effect_api = Blueprint('effect_api', __name__)

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
@effect_api.route('/GetActiveEffect', methods=['GET'])
@login_required
def GetActiveEffect():  # pylint: disable=E0211
    if request.method == 'GET':
        data_in = request.args.to_dict()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_executer.ValidateDataIn(data_in, ("device",)):
            return "Input data are wrong.", 403

        active_effect = Executer.instance.effect_executer.GetActiveEffect(data_in["device"])
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
@effect_api.route('/SetActiveEffect', methods=['POST'])
@login_required
def SetActiveEffect():  # pylint: disable=E0211
    if request.method == 'POST':
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_executer.ValidateDataIn(data_in, ("device", "effect",)):
            return "Input data are wrong.", 403

        Executer.instance.effect_executer.SetActiveEffect(data_in["device"], data_in["effect"])

        return jsonify(data_out)

# SetActiveEffectForAll
# {
# "effect" = <effectID>
# }
@effect_api.route('/SetActiveEffectForAll', methods=['POST'])
@login_required
def SetActiveEffectForAll():  # pylint: disable=E0211
    if request.method == 'POST':
        data_in = request.get_json()
        data_out = copy.deepcopy(data_in)

        if not Executer.instance.effect_executer.ValidateDataIn(data_in, ("effect",)):
            return "Input data is wrong.", 403

        Executer.instance.effect_executer.SetActiveEffectForAll(data_in["effect"])

        return jsonify(data_out)