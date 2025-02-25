import time
from pololu_3pi_2040_robot import robot
import math

# Initialize hardware
motors = robot.Motors()
encoders = robot.Encoders()
display = robot.Display()
yellow_led = robot.YellowLED()

# Robot Parameters
MAX_MOVE_SPEED = 1500  # Maximum movement speed
MIN_MOVE_SPEED = 400   # Minimum movement speed
WHEEL_DIAMETER = 3.315  # Wheel diameter in cm
WHEEL_CIRCUMFERENCE = WHEEL_DIAMETER * math.pi
COUNTS_PER_ROTATION = 358.2  # Encoder counts per wheel rotation

def move(distance_cm, time_expected):
    """
    Move the robot straight for a given distance in a specified time.
    Positive distance moves forward, negative moves backward.
    
    :param distance_cm: Distance to move in centimeters
    :param time_expected: Expected time to complete movement in seconds
    """
    # Calculate target encoder counts
    target_counts = int((abs(distance_cm) / WHEEL_CIRCUMFERENCE) * COUNTS_PER_ROTATION)
    
    # Get initial encoder values
    left_start, right_start = encoders.get_counts()
    
    # Set movement direction
    moving_forward = distance_cm > 0
    
    # Track timing
    start_time = time.ticks_ms()
    
    while True:
        # Get current encoder counts
        left_count, right_count = encoders.get_counts()
        left_diff = abs(left_count - left_start)
        right_diff = abs(right_count - right_start)
        
        # Use average of both wheels
        avg_counts = (left_diff + right_diff) / 2
        
        # Calculate remaining counts
        remaining_counts = target_counts - avg_counts
        
        # Calculate elapsed time
        elapsed_time = time.ticks_diff(time.ticks_ms(), start_time) / 1000.0
        
        # Check if movement is complete
        if remaining_counts <= 1 or elapsed_time >= time_expected:
            break
            
        # Calculate speed based on timing and remaining distance
        progress = elapsed_time / time_expected
        if progress < 0.2:  # First 20%: Accelerate
            speed_factor = progress / 0.2
        elif progress > 0.8:  # Last 20%: Decelerate
            speed_factor = (1 - progress) / 0.2
        else:  # Middle 60%: Full speed
            speed_factor = 1.0
            
        move_speed = MAX_MOVE_SPEED * speed_factor
        move_speed = max(move_speed, MIN_MOVE_SPEED)
        
        # Calculate correction to keep straight
        error = left_diff - right_diff
        correction = error * 2  # Simple proportional correction
        
        # Set motor speeds based on direction
        if moving_forward:
            motors.set_speeds(move_speed - correction, move_speed + correction)
        else:
            motors.set_speeds(-(move_speed - correction), -(move_speed + correction))
        
        # Update display
        display.fill(0)
        display.text(f"Target: {target_counts}", 0, 0, 1)
        display.text(f"Current: {int(avg_counts)}", 0, 10, 1)
        display.text(f"Time: {elapsed_time:.2f}s", 0, 20, 1)
        display.text(f"Speed: {int(move_speed)}", 0, 30, 1)
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
    display.text("Move complete", 0, 0, 1)
    display.text(f"Target: {target_counts}", 0, 10, 1)
    display.text(f"Final: {int(avg_counts)}", 0, 20, 1)
    display.text(f"Error: {int(count_error)}", 0, 30, 1)
    display.show()
    
    return count_error

# Test code

while True:
    if robot.ButtonA().is_pressed():
        time.sleep(0.2)
        error = move(130, 2.5)  # Move forward 30cm in 1 second
        print(f"Error: {error}")
    if robot.ButtonB().is_pressed():
        time.sleep(0.2)
        error = move(-30, 1.0)  # Move backward 30cm in 1 second
        print(f"Error: {error}")
