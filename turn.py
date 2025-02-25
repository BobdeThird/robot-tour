import time
from pololu_3pi_2040_robot import robot
import math

# Initialize hardware
motors = robot.Motors()
encoders = robot.Encoders()
display = robot.Display()
yellow_led = robot.YellowLED()

# Robot Parameters
MAX_TURN_SPEED = 1250  # Maximum turning speed
MIN_TURN_SPEED = 400   # Minimum turning speed
WHEEL_BASE = 8.6  # Distance between wheels in cm
WHEEL_CIRCUMFERENCE = 3.315 * math.pi  # Adjusted from 3.35 to 3.32 to compensate for underturn
COUNTS_PER_ROTATION = 358.2  # Encoder counts per wheel rotation

def turn(target_angle):
    """
    Turn the robot in place using encoder counts.
    Positive angles turn left, negative angles turn right.
    
    :param target_angle: Angle to turn in degrees
    """
    # if turning left, overturn by 1 deg
    if target_angle < 0:
        target_angle += 2.25

    
    # Calculate target encoder counts
    arc_length = (abs(target_angle) / 360) * (math.pi * WHEEL_BASE)
    target_counts = int((arc_length / WHEEL_CIRCUMFERENCE) * COUNTS_PER_ROTATION)
    
    # Get initial encoder values
    left_start, right_start = encoders.get_counts()
    
    

    # Set turn direction
    turning_left = target_angle > 0
    
    while True:
        # Get current encoder counts
        left_count, right_count = encoders.get_counts()
        left_diff = abs(left_count - left_start)
        right_diff = abs(right_count - right_start)
        
        # Use average of both wheels
        avg_counts = (left_diff + right_diff) / 2
        
        # Calculate remaining counts
        remaining_counts = target_counts - avg_counts
        
        # Check if turn is complete
        if remaining_counts <= 1:
            break
        
        # Calculate speed based on remaining distance
        if remaining_counts > target_counts * 0.5:
            # First half: Full speed
            turn_speed = MAX_TURN_SPEED
        else:
            # Second half: Gradual slowdown
            speed_factor = remaining_counts / (target_counts * 0.5)
            turn_speed = MAX_TURN_SPEED * speed_factor
            turn_speed = max(turn_speed, MIN_TURN_SPEED)
        
        # Set motor speeds based on direction
        if turning_left:
            motors.set_speeds(-turn_speed, turn_speed)
        else:
            motors.set_speeds(turn_speed, -turn_speed)
        
        # Update display
        display.fill(0)
        display.text(f"Target: {target_counts}", 0, 0, 1)
        display.text(f"Current: {int(avg_counts)}", 0, 10, 1)
        display.text(f"Remain: {int(remaining_counts)}", 0, 20, 1)
        display.text(f"Speed: {int(turn_speed)}", 0, 30, 1)
        display.show()
        
        yellow_led.value(1)
        time.sleep(0.01)
    
    # Stop motors
    motors.off()
    yellow_led.value(0)
    
    # Calculate final error
    left_count, right_count = encoders.get_counts()
    left_diff = abs(left_count - left_start)
    right_diff = abs(right_count - right_start)
    avg_counts = (left_diff + right_diff) / 2
    count_error = target_counts - avg_counts
    
    # Display final position
    display.fill(0)
    display.text("Turn complete", 0, 0, 1)
    display.text(f"Target: {target_counts}", 0, 10, 1)
    display.text(f"Final: {int(avg_counts)}", 0, 20, 1)
    display.text(f"Error: {int(count_error)}", 0, 30, 1)
    display.show()
    
    return count_error

# Test code
# while True:
#     if robot.ButtonA().is_pressed():
#         time.sleep(0.2)
#         error = turn(90)  # Turn left 90 degrees
#         print(f"Error: {error}")
#     if robot.ButtonB().is_pressed():
#         time.sleep(0.2)
#         error = turn(-90)  # Turn right 90 degrees
#         print(f"Error: {error}")
