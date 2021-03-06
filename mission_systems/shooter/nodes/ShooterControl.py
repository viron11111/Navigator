#!/usr/bin/env python
from Sabertooth2x12 import Sabertooth2x12
from sensor_msgs.msg import Joy
import rospy
import actionlib
import time
from navigator_msgs.msg import ShooterDoAction, ShooterDoActionFeedback, ShooterDoActionResult, ShooterDoActionGoal
from navigator_msgs.srv import ShooterManual, ShooterManualResponse
from std_srvs.srv import Trigger,TriggerResponse

class ShooterControl:
    def __init__(self):
        self.controller_file = rospy.get_param('~controller/controller_serial', '/dev/ttyUSB0')
        use_sim = rospy.get_param('/is_simulation',False)
        if use_sim:
          rospy.loginfo("Shooter controller running in simulation mode")
          print "Running in sim"
          self.motor_controller = Sabertooth2x12(self.controller_file,sim=True)
        else:
          self.motor_controller = Sabertooth2x12(self.controller_file)
        rospy.loginfo("Shooter connecting to motor controller at: %s", self.controller_file)
        self.load_retract_time = rospy.Duration(0, rospy.get_param('~controller/load/retract_time_millis', 950)*1000000)
        self.load_extend_time = rospy.Duration(0, rospy.get_param('~controller/load/extend_time_millis', 500)*1000000)
        self.load_pause_time = rospy.Duration(0, rospy.get_param('~controller/load/pause_time_millis', 100)*1000000)
        self.load_total_time = self.load_retract_time + self.load_pause_time + self.load_extend_time
        self.fire_extend_time = rospy.Duration(0, rospy.get_param('~controller/fire/extend_time_millis', 400)*1000000)
        self.fire_shoot_time = rospy.Duration(0, rospy.get_param('~controller/fire/shoot_time_millis', 1000)*1000000)
        self.total_fire_time = max(self.fire_shoot_time,self.fire_extend_time)
        self.loaded = False #Assume linear actuator starts forward
        self.stop = False
        self.motor1_stop = 0
        self.motor2_stop = 0
        self.fire_server = actionlib.SimpleActionServer('/shooter/fire', ShooterDoAction, self.fire_execute_callback, False)
        self.fire_server.start()
        self.load_server = actionlib.SimpleActionServer('/shooter/load', ShooterDoAction, self.load_execute_callback, False)
        self.load_server.start()
        self.cancel_service = rospy.Service('/shooter/cancel', Trigger, self.cancel_callback)
        self.manual_service = rospy.Service('/shooter/manual', ShooterManual, self.manual_callback)
        self.fire_client = actionlib.SimpleActionClient('/shooter/fire', ShooterDoAction)
        self.load_client = actionlib.SimpleActionClient('/shooter/load', ShooterDoAction)
        self.joy_sub = rospy.Subscriber("/joy", Joy,self.joy_callback)
        self.last_shoot_joy = False
        self.last_cancel_joy = False
        self.last_load_joy = False


    def load_execute_callback(self, goal):
        result = ShooterDoActionResult()
        if self.fire_server.is_active():
            rospy.loginfo("Something already running, aborting")
            result.result.success = False
            result.result.error = result.result.ALREADY_RUNNING
            self.load_server.set_aborted(result.result)
            return
        if self.loaded:
            rospy.loginfo("Already loaded, aborting")
            result.result.success = False
            result.result.error = result.result.ALREADY_LOADED
            self.load_server.set_aborted(result.result)
            return
        start_time = rospy.get_rostime()
        dur_from_start = rospy.Duration(0, 0)
        rospy.loginfo("starting load")
        rate = rospy.Rate(50) # 50hz
        feedback = ShooterDoActionFeedback()
        while dur_from_start < self.load_total_time and not self.stop:
            dur_from_start = rospy.get_rostime() - start_time
            feedback.feedback.time_remaining = self.load_total_time - dur_from_start
            self.load_server.publish_feedback(feedback.feedback)
            if dur_from_start < self.load_retract_time:
                self.motor_controller.setMotor1(1.0)
            elif dur_from_start < self.load_retract_time + self.load_pause_time:
                self.motor_controller.setMotor1(0)
            elif dur_from_start < self.load_total_time:
                self.motor_controller.setMotor1(-1.0)
            rate.sleep()
        if self.stop:
            result = ShooterDoActionResult()
            result.result.success = False
            result.result.error = result.result.MANUAL_CONTROL_USED
            self.motor_controller.setMotor1(self.motor1_stop)
            self.motor_controller.setMotor2( self.motor2_stop)
            self.stop = False
            self.load_server.set_preempted (result=result.result)
            return
        self.motor_controller.setMotor1(0)
        self.motor_controller.setMotor2(1)
        result.result.success = True
        self.loaded = True
        self.load_server.set_succeeded(result.result)
        rospy.loginfo("Finished loaded")


    def fire_execute_callback(self, goal):
        result = ShooterDoActionResult()
        if self.load_server.is_active():
            rospy.loginfo("Something already running, aborting fire")
            result.result.success = False
            result.result.error = result.result.ALREADY_RUNNING
            self.fire_server.set_aborted(result.result)
            return
        if not self.loaded:
            rospy.loginfo("Not loaded, aborting fire")
            result.result.success = False
            result.result.error = result.result.NOT_LOADED
            self.fire_server.set_aborted(result.result)
            return
        start_time = rospy.get_rostime()
        dur_from_start = rospy.Duration(0, 0)
        rospy.loginfo("starting fire")
        rate = rospy.Rate(50) # 50hz
        feedback = ShooterDoActionFeedback()
        self.motor_controller.setMotor1(-1)
        self.motor_controller.setMotor2(1)
        while dur_from_start < self.total_fire_time and not self.stop:
            dur_from_start = rospy.get_rostime() - start_time
            feedback.feedback.time_remaining = self.total_fire_time - dur_from_start
            self.fire_server.publish_feedback(feedback.feedback)
            if dur_from_start > self.fire_extend_time:
                self.motor_controller.setMotor1(0)
            if dur_from_start > self.fire_shoot_time:
                self.motor_controller.setMotor2(0)
        if self.stop:
            result.result.success = False
            result.result.error = result.result.MANUAL_CONTROL_USED
            self.motor_controller.setMotor1(self.motor1_stop)
            self.motor_controller.setMotor2( self.motor2_stop)
            self.stop = False
            self.fire_server.set_preempted (result=result.result)
            return
        self.motor_controller.setMotor1(0)
        self.motor_controller.setMotor2(0)
        result.result.success = True
        self.loaded = False
        self.fire_server.set_succeeded(result.result)
        rospy.loginfo("Finished fire")

    def stop_actions(self):
        if self.load_server.is_active() or self.fire_server.is_active():
          self.stop = True
        else:
          self.stop = False
          self.motor1_stop = 0
          self.motor2_stop = 0       
    def cancel_callback(self, req):
        self.motor1_stop = 0
        self.motor2_stop = 0
        self.stop_actions()
        rospy.loginfo("canceled")
        return TriggerResponse(success=True)
    def manual_callback(self, req):
        self.motor1_stop = -req.feeder
        self.motor2_stop = req.shooter
        self.stop_actions()
        res = ShooterManualResponse()
        res.success = True
        return res

    def is_joy_shoot(self,data): #Shoot if right trigger is held down
      return data.axes[5] < -0.9
    def is_joy_load(self,data): #load if left bumper is pressed
      return data.buttons[4] == 1
    def is_joy_cancel(self,data): #cancel if right bumper is pressed
      return data.buttons[5] == 1
    def joy_callback(self,data):
        joy_shoot = self.is_joy_shoot(data)
        joy_load = self.is_joy_load(data)
        joy_cancel = self.is_joy_cancel(data)
        if joy_shoot and not self.last_shoot_joy:
          rospy.loginfo("Joystick input : Shoot")
          self.fire_client.send_goal(goal=ShooterDoActionGoal())
        if joy_load and not self.last_load_joy:
          rospy.loginfo("Joystick input : Load")
          self.load_client.send_goal(goal=ShooterDoActionGoal())
        if joy_cancel and not self.last_cancel_joy:
          rospy.loginfo("Joystick input : Cancel")
          self.cancel_callback(None)
        #print "Data: ", data
        self.last_shoot_joy = joy_shoot
        self.last_load_joy = joy_load
        self.last_cancel_joy = joy_cancel
      
        

if __name__ == '__main__':
    rospy.init_node('shooter_control')
    control = ShooterControl()
    #rate = rospy.Rate(10) # 10hz
    rospy.spin()
