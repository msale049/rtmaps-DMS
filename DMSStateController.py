import rtmaps.core as rt
import rtmaps.types
from rtmaps.base_component import BaseComponent
from statemachine import StateMachine, State
from dataclasses import dataclass
import time

class rtmaps_python(BaseComponent):
    def __init__(self):
        BaseComponent.__init__(self)
        self.haptic_seq = 0
        self.prev_warn2 = False

    def Dynamic(self):
        # Inputs
        self.add_input("ress_soc", rtmaps.types.FLOAT64)
        self.add_input("regen_braking", rtmaps.types.INTEGER64)  
        self.add_input("twelve_volt_switch", rtmaps.types.INTEGER64)  
        # self.add_input("dms_gaze_status", rtmaps.types.INTEGER64)
        # self.add_input("dms_confidence", rtmaps.types.INTEGER64)
        # self.add_input("hands_off_wheel", rtmaps.types.INTEGER64)
        self.add_input("dms_gaze_status", rtmaps.types.INTEGER32)
        self.add_input("dms_confidence", rtmaps.types.INTEGER32)
        self.add_input("hands_off_wheel", rtmaps.types.INTEGER32)
        self.add_input("dms_requested", rtmaps.types.INTEGER32)
        self.add_input("dms_gaze_invalid", rtmaps.types.INTEGER32)
    
        
        # Outputs
        self.add_output("state", rtmaps.types.INTEGER64)
        self.add_output("cav_lock", rtmaps.types.INTEGER64)

        self.add_output("chime_lvl1", rtmaps.types.INTEGER64)
        self.add_output("warn_ind_req", rtmaps.types.INTEGER64)
        self.add_output("warn_disp_lvl", rtmaps.types.INTEGER64)
        self.add_output("chime_lvl2", rtmaps.types.INTEGER64)
        self.add_output("haptic_pulses", rtmaps.types.INTEGER64)
        self.add_output("haptic_seq", rtmaps.types.INTEGER64)

        # Properties
        self.add_property("ress_soc_threshold", 10.0, rtmaps.types.FLOAT64)
        self.add_property("dms_confidence_threshold", 4.0, rtmaps.types.FLOAT64)
        self.add_property("attention_loss_warning_time", 5.0, rtmaps.types.FLOAT64)
        self.add_property("attention_loss_critical_time", 15.0, rtmaps.types.FLOAT64)
        self.add_property("hands_off_warning_time", 5.0, rtmaps.types.FLOAT64)
        self.add_property("hands_off_critical_time", 15.0, rtmaps.types.FLOAT64)
        self.add_property("cav_lock_duration", 30.0, rtmaps.types.FLOAT64)

    def Birth(self):
        self.DMS_machine = DMSStateMachine(
            ress_soc_threshold=float(self.properties["ress_soc_threshold"].data),
            dms_confidence_threshold=float(self.properties["dms_confidence_threshold"].data),
            attention_loss_warning_time=float(self.properties["attention_loss_warning_time"].data),
            attention_loss_critical_time=float(self.properties["attention_loss_critical_time"].data),
            hands_off_warning_time=float(self.properties["hands_off_warning_time"].data),
            hands_off_critical_time=float(self.properties["hands_off_critical_time"].data),
            cav_lock_duration=float(self.properties["cav_lock_duration"].data)
        )
        print("DMS State Controller initialized")

    def Core(self):
        inputs = DMSInputs(
            ress_soc=self.inputs["ress_soc"].ioelt.data if self.inputs["ress_soc"].ioelt is not None else None,
            regen_braking=bool(self.inputs["regen_braking"].ioelt.data) if self.inputs["regen_braking"].ioelt is not None else None,
            twelve_volt_switch=bool(self.inputs["twelve_volt_switch"].ioelt.data) if self.inputs["twelve_volt_switch"].ioelt is not None else None,
            dms_gaze_status=self.inputs["dms_gaze_status"].ioelt.data if self.inputs["dms_gaze_status"].ioelt is not None else None,
            dms_confidence=self.inputs["dms_confidence"].ioelt.data if self.inputs["dms_confidence"].ioelt is not None else None,
            hands_off_wheel=bool(self.inputs["hands_off_wheel"].ioelt.data) if self.inputs["hands_off_wheel"].ioelt is not None else None,
            dms_requested=bool(self.inputs["dms_requested"].ioelt.data) if self.inputs["dms_requested"].ioelt is not None else None,
            dms_gaze_invalid=bool(self.inputs["dms_gaze_invalid"].ioelt.data) if self.inputs["dms_gaze_invalid"].ioelt is not None else False

        )
        self.DMS_machine.update(inputs)
        # if self.DMS_machine.current_state.id is not None:
        #     self.outputs["state"].write(self.DMS_machine.current_state.value)
        # self.outputs["cav_lock"].write(1 if self.DMS_machine.cav_lock else 0)

        state_val = int(self.DMS_machine.current_state.value) if self.DMS_machine.current_state is not None else 0
        cav = 1 if self.DMS_machine.cav_lock else 0

        self.outputs["state"].write(state_val)
        self.outputs["cav_lock"].write(cav)

        # Warning 1 outputs 
        self.outputs["chime_lvl1"].write(1 if (state_val == 3 and cav == 0) else 0)
        # self.outputs["warn_ind_req"].write(1 if (state_val == 3 and cav == 0) else 0)
        # self.outputs["warn_disp_lvl"].write(1 if (state_val == 3 and cav == 0) else 0)

        # Warning 1 outputs 
        warn2 = (state_val == 4 and cav == 0)
        warn_ind = 0
        warn_disp = 0

        if cav == 0:
            if state_val == 3:
                warn_ind = 1
                warn_disp = 3
            elif state_val == 4:
                warn_ind = 4   # (or 2/3 depending on your enum)
                warn_disp = 1

        self.outputs["warn_ind_req"].write(warn_ind)
        self.outputs["warn_disp_lvl"].write(warn_disp)
        

        # haptic
        self.outputs["haptic_pulses"].write(10 if warn2 else 0)   # pulses > 0 triggers request

        if warn2 and not self.prev_warn2:
            self.haptic_seq = (self.haptic_seq + 1) % 4
        self.prev_warn2 = warn2
        self.outputs["haptic_seq"].write(self.haptic_seq if warn2 else 0)

    def Death(self):
        print("DMS State Controller terminated")

@dataclass
class DMSInputs:
    ress_soc: float
    regen_braking: bool
    twelve_volt_switch: bool
    dms_gaze_status: int
    dms_confidence: float
    hands_off_wheel: bool
    dms_requested: bool
    dms_gaze_invalid: bool


class DMSStateMachine(StateMachine):
    """Driver Monitoring System state machine"""
    inactive = State(initial=True, value=0)
    standby = State(value=1)
    active = State(value=2)
    warning1 = State(value=3)
    warning2 = State(value=4)

    transitions = (
        inactive.to(standby, cond="not is_ress_soc_low and is_regen_braking and is_twelve_volt_switch")
        | standby.to(active, cond="is_dms_requested")
        | standby.to(inactive, cond="is_ress_soc_low or not is_regen_braking or not is_twelve_volt_switch")
        | active.to(inactive, cond="is_ress_soc_low or not is_regen_braking or not is_twelve_volt_switch")
        | active.to(standby, cond="not is_dms_requested")
        | active.to(warning1, cond="is_attention_lost_5s or is_hands_off_5s")
        | warning1.to(active, cond="is_driver_reengaged")
        | warning1.to(warning2, cond="is_attention_lost_15s or is_hands_off_15s")
        | warning2.to(inactive, cond="is_cav_lock_complete")
    )

    def __init__(self, ress_soc_threshold: float, dms_confidence_threshold: float, 
                 attention_loss_warning_time: float, attention_loss_critical_time: float,
                 hands_off_warning_time: float, hands_off_critical_time: float,
                 cav_lock_duration: float, *args, **kwargs):
        self.inputs = None
        self.attention_loss_start = None
        self.hands_off_start = None
        self.cav_lock_start_time = None
        self.ress_soc_threshold = ress_soc_threshold
        self.dms_confidence_threshold = dms_confidence_threshold
        self.attention_loss_warning_time = attention_loss_warning_time
        self.attention_loss_critical_time = attention_loss_critical_time
        self.hands_off_warning_time = hands_off_warning_time
        self.hands_off_critical_time = hands_off_critical_time
        self.cav_lock_duration = cav_lock_duration
        self.cav_lock = False
        super().__init__(*args, **kwargs, allow_event_without_transition=True)

    def update(self, inputs: DMSInputs):
        self.inputs = inputs
        self.transitions()

    def is_ress_soc_low(self):
        if not self.inputs:
            return False
        return self.inputs.ress_soc < self.ress_soc_threshold

    def is_regen_braking(self):
        if not self.inputs:
            return False
        return self.inputs.regen_braking

    def is_twelve_volt_switch(self):
        if not self.inputs:
            return False
        return self.inputs.twelve_volt_switch

    def is_dms_requested(self):
        if not self.inputs:
            return False
        return self.inputs.dms_requested

    def is_attention_lost_5s(self):
        if not self.inputs:
            return False
        return self.get_attention_loss_time() >= self.attention_loss_warning_time

    def is_attention_lost_15s(self):
        if not self.inputs:
            return False
        return self.get_attention_loss_time() >= self.attention_loss_critical_time

    def is_hands_off_5s(self):
        if not self.inputs:
            return False
        return self.get_hands_off_time() >= self.hands_off_warning_time

    def is_hands_off_15s(self):
        if not self.inputs:
            return False
        return self.get_hands_off_time() >= self.hands_off_critical_time

    def is_driver_reengaged(self):
        if not self.inputs:
            return False
        if self.inputs.dms_gaze_invalid:
            return False  # cannot trust gaze
        return (self.inputs.dms_gaze_status == 1 and 
                self.inputs.dms_confidence >= self.dms_confidence_threshold and 
                not self.inputs.hands_off_wheel)

    def is_cav_lock_complete(self):
        if not self.inputs:
            return False
        # Only start the timer when in warning2 and driver reengaged
        if self.is_driver_reengaged():
            if self.cav_lock_start_time is None:
                self.cav_lock_start_time = time.time()
                self.cav_lock = True
        # If timer is running, check if 30s has elapsed
        if self.cav_lock_start_time is not None:
            elapsed = time.time() - self.cav_lock_start_time
            if elapsed >= self.cav_lock_duration:
                self.cav_lock = False
                self.cav_lock_start_time = None
                # Reset gaze and hands timers after CAV lock period
                self.attention_loss_start = None
                self.hands_off_start = None
                return True
            else:
                self.cav_lock = True
                return False
        self.cav_lock = False
        return False

    def get_attention_loss_time(self):
        if not self.inputs:
            self.attention_loss_start = None
            return 0.0
        # if self.inputs.dms_gaze_status != 1 and self.inputs.dms_confidence >= self.dms_confidence_threshold:
        if (not self.inputs.dms_gaze_invalid and self.inputs.dms_gaze_status != 1 and self.inputs.dms_confidence >= self.dms_confidence_threshold):
            if self.attention_loss_start is None:
                self.attention_loss_start = time.time()
            return time.time() - self.attention_loss_start
        else:
            self.attention_loss_start = None
            return 0.0

    def get_hands_off_time(self):
        if not self.inputs:
            self.hands_off_start = None
            return 0.0
        if self.inputs.hands_off_wheel:
            if self.hands_off_start is None:
                self.hands_off_start = time.time()
            return time.time() - self.hands_off_start
        else:
            self.hands_off_start = None
            return 0.0

